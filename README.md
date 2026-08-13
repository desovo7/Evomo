# Evomo

Evomo is a learning-first implementation of a self-evolving agent for
ALFWorld using the local Qwen3-1.7B model.

## M0 decomposition by data flow

M0 is deliberately split into small, independently testable parts:

1. **Data contract (implemented):** convert a task into an immutable
   `TaskSpec`, record environment transitions, finish an `Episode`, and store
   it as JSONL.
2. **Task discovery (implemented):** enumerate ALFWorld splits, report
   incomplete trials, convert raw metadata into `TaskSpec` objects, and write
   a portable JSONL manifest.
3. **Environment adapter (implemented):** map one `TaskSpec` through real
   ALFWorld/TextWorld `reset/step` calls without involving a language model.
4. **Policy contract (implemented):** map observations and history to an
   auditable `ActionDecision`; the first baseline samples admissible actions
   reproducibly.
5. **Rollout runner (implemented):** connect task, environment, policy,
   recorder, and JSONL storage for one complete episode.
6. **Persistence and resume:** manifests, deduplication, interrupted-run
   recovery, and batch output layout.
7. **Configuration and observability:** validated configs, structured logs,
   seeds, and run summaries.
8. **Baseline CLI:** execute reproducible random, expert, and later Qwen
   baselines over selected splits.

Parts 1 through 5 now exist. The executable data path is:

```text
ALFWorld data -> TaskSpec -> TextWorld reset/step -> environment transition
              -> EpisodeRecorder -> StepRecord -> Episode JSONL
```

Run the example without installing the package:

```bash
PYTHONPATH=src python scripts/record_example.py
```

Run the standard-library tests:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Discover ALFWorld tasks

The discovery layer reads files only; it does not import or launch ALFWorld.
Pass either the directory stored in `ALFWORLD_DATA` or its `json_2.1.1`
subdirectory:

```bash
export ALFWORLD_DATA=/path/to/alfworld
PYTHONPATH=src python scripts/discover_alfworld_tasks.py \
  --output outputs/manifests/alfworld_tasks.jsonl
```

By default, only trials containing `game.tw-pddl` are written because those
are runnable by the next TextWorld adapter. The printed report still counts
all `traj_data.json` files and missing games. Use `--include-incomplete` only
for data inspection. Paths inside the manifest are relative to
`json_2.1.1`, so the manifest does not depend on one machine's absolute path.

## Run one ALFWorld environment transition

The environment adapter consumes one discovered `TaskSpec`, resolves its
relative `game.tw-pddl` path, and returns model-independent reset/step data.
ALFWorld is an optional dependency because task discovery and trajectory data
tests do not require it:

```bash
python -m pip install -e '.[alfworld]'

export ALFWORLD_DATA=/path/to/alfworld
PYTHONPATH=src python scripts/smoke_alfworld_environment.py \
  --split valid_train \
  --task-index 0
```

This smoke command deliberately executes the first admissible action. It
checks data plumbing rather than attempting to solve the task. The returned
observation and action set will become inputs to the policy layer in part 4.
The adapter disables ALFWorld name shuffling; `requested_seed` is recorded for
the future rollout layer but TextWorld 1.7's single-game start API does not
accept a reset seed.

## Run one complete random-policy episode

The random baseline validates the full loop without a model or GPU. It
samples only from the current admissible actions, records every decision and
transition, stops at environment termination or `max_steps`, appends one
`Episode` to JSONL, and reads it back before reporting success:

```bash
export ALFWORLD_DATA=/path/to/alfworld
PYTHONPATH=src python scripts/run_random_alfworld_episode.py \
  --split valid_train \
  --task-index 0 \
  --seed 42 \
  --max-steps 50 \
  --output outputs/episodes/random_baseline.jsonl
```

A random policy is expected to fail many tasks. A result such as
`termination_reason=max_steps` is a valid completed rollout, not an
infrastructure error. The next model-policy stage will replace only the
action selection component while keeping the same runner and episode schema.

## Run the local Qwen3-1.7B baseline

`QwenPolicy` renders the task goal, current observation, up to six recent
transitions, and the exact admissible action list. Qwen3 runs in non-thinking,
deterministic mode and selects an action by index. The parser accepts a tagged
index, a bare index, or an index followed by the exact action text. Any other
response falls back to the first admissible action and records the raw output
and parse failure in the episode rather than interrupting the environment.

```bash
python -m pip install -e '.[alfworld,qwen]'

export ALFWORLD_DATA=/path/to/alfworld
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src python \
  scripts/run_qwen_alfworld_episode.py \
  --model-path ../models/Qwen3-1.7B \
  --device cuda:0 \
  --split valid_train \
  --task-index 0 \
  --seed 42 \
  --max-steps 50 \
  --output outputs/episodes/qwen3_1.7b_baseline.jsonl
```

On the development machine, the first real baseline completed 50 steps in
about 21 seconds. All 50 outputs parsed to admissible actions and the JSONL
round trip passed, but the untrained policy did not solve the task and ended
at `max_steps`. This is a valid base-model measurement: infrastructure
success and benchmark success are reported separately.

## Compare four prompt variants with trajectory logs

The controlled A/B/C/D runner loads Qwen once and executes the variants in
order on the same task, environment, seed, history budget, and greedy decoding
configuration:

- A: action index only;
- B: one short plan followed by an action index;
- C: explicit reasoning followed by exact admissible action text;
- D: action index with an independently written anti-loop skill.

```bash
export ALFWORLD_DATA=/path/to/alfworld
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src python \
  scripts/run_qwen_prompt_ablation.py \
  --model-path ../models/Qwen3-1.7B \
  --split valid_train \
  --task-index 0 \
  --seed 42 \
  --max-steps 30 \
  --output-dir reports/prompt_ablation/qwen3_1.7b_valid_train_task0
```

Each variant writes a summary JSON, step-level JSONL, and readable Markdown
trace. A combined Episode JSONL and comparison JSON are also written. The
checked-in first-task result is a prompt diagnostic, not a benchmark score:

| Variant | Success | Parsed | Strict format | Repeats | Unchanged | Unique actions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A index | 0 | 30/30 | 0/30 | 29 | 29 | 1 |
| B plan + index | 0 | 30/30 | 30/30 | 15 | 15 | 7 |
| C reasoning + action text | 0 | 30/30 | 0/30 | 1 | 1 | 14 |
| D anti-loop skill | 0 | 29/30 | 2/30 | 8 | 8 | 14 |

C shows that exact action-text selection greatly reduced looping on this task,
although Qwen3-1.7B omitted the requested `<think>` block. D also reduced
looping substantially. None solved the task, so these observations must be
validated on a fixed multi-task baseline before selecting a default prompt.
