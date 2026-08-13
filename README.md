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
6. **Persistence and resume (implemented):** atomically publish one complete
   artifact directory per task, validate it on restart, and skip completed
   trajectories.
7. **Configuration and observability (partly implemented):** CLI validation,
   fixed seeds, step JSONL, readable trajectories, and cross-prompt summaries.
8. **Baseline CLI:** execute reproducible random, expert, and later Qwen
   baselines over selected splits.

Parts 1 through 6 now exist. The executable data path is:

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

## Run the fixed six-task prompt baseline on three GPUs

The multi-task runner selects the lexicographically first playable
`valid_train` task from each of ALFWorld's six task types. B, C, and D can run
independently on three GPUs while covering identical task IDs. A task is first
written to a temporary directory and then published atomically with:

- the complete `Episode` in `episode.jsonl`;
- one transition per line in `steps.jsonl`;
- task and trajectory metrics in `summary.json`;
- a readable `trajectory.md`.

Rerunning the same command validates and skips complete tasks. Each variant
also stores an immutable `run_config.json`; changing the model, prompt, task
set, seed, step/token limit, or history budget requires a new output directory.
The runner rejects a partially written task directory so incomplete or mixed
data cannot enter an aggregate.

```bash
export ALFWORLD_DATA=/path/to/alfworld
REPORT=reports/multitask/qwen3_1.7b_valid_train_1_per_type

for spec in "0 B" "1 C" "2 D"; do
  set -- $spec
  CUDA_VISIBLE_DEVICES=$1 PYTHONPATH=src python \
    scripts/run_qwen_multitask_variant.py \
    --model-path ../models/Qwen3-1.7B \
    --device cuda:0 \
    --split valid_train \
    --per-type 1 \
    --variant $2 \
    --seed 42 \
    --max-steps 30 \
    --max-new-tokens 96 \
    --max-history-items 6 \
    --output-dir "$REPORT/$2" &
done
wait

PYTHONPATH=src python scripts/summarize_qwen_multitask.py \
  --input-dir "$REPORT" \
  --split valid_train \
  --per-type 1
```

The checked-in run contains 18 episodes and 540 transitions. All persisted
actions belonged to their step's admissible-action set, every observation
chain was continuous, and step-log counts matched their episodes. Results:

| Prompt | Success | Parsed | Strict format | Repeats | Unchanged observations |
| --- | ---: | ---: | ---: | ---: | ---: |
| B plan + index | 0/6 | 179/180 | 179/180 | 90 | 90 |
| C reasoning + action text | 0/6 | 173/180 | 0/180 | 23 | 23 |
| D anti-loop skill | 0/6 | 153/180 | 46/180 | 33 | 33 |

B follows its output format but loops heavily. C produces the fewest repeats
and parses 96.1% of actions, yet does not emit the requested complete
`<think>...</think>` structure. D explores the most distinct actions overall
but falls back more often. The fixed six-task sample is still a diagnostic,
not a statistically stable benchmark estimate: all three prompts score 0%, so
the next stage should add explicit task-state tracking or learned experience
rather than declare a prompt winner from success rate.

The full per-task table and every raw response are under
`reports/multitask/qwen3_1.7b_valid_train_1_per_type/`.

## Add explicit state and repair future intents

The next increment reconstructs compact ALFWorld state from completed
transitions before every decision. It does not ask another model to summarize
history. The deterministic tracker records:

- the task-type recipe and current location;
- the held object, visited locations, opened and known-empty receptacles;
- known object placements and completed clean/cool/heat transformations;
- actions that returned an unchanged observation and the six recent actions.

Prompt E injects that state and asks Qwen for an exact admissible action. Its
state snapshot is stored as `state_before` on every step. The first E run
exposed a specific interface mismatch: Qwen often proposed a sensible future
action that was not admissible *yet*. Examples included trying to take an
alarm clock from a sidetable while standing at a desk, or trying to put a held
book on a desk while still standing at the bed. Falling back to the first
admissible action discarded that useful intent and created loops.

Prompt F keeps the same model prompt and adds a narrow prerequisite repair.
It may only convert an unavailable future intent into one currently
admissible navigation action:

- `take X from Y` can become `go to Y`;
- `move HELD_X to Y` can become `go to Y`;
- `clean/cool/heat HELD_X with Y` can become `go to Y`.

Every repair records the model's proposed action, executed action, and repair
reason. No invented action is sent to ALFWorld.

```bash
export ALFWORLD_DATA=/path/to/alfworld
REPORT=reports/state_tracking/qwen3_1.7b_valid_train_1_per_type

for variant in E F; do
  CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src python \
    scripts/run_qwen_multitask_variant.py \
    --model-path ../models/Qwen3-1.7B \
    --device cuda:0 \
    --split valid_train \
    --per-type 1 \
    --variant "$variant" \
    --seed 42 \
    --max-steps 30 \
    --max-new-tokens 96 \
    --max-history-items 6 \
    --output-dir "$REPORT/$variant"
done

PYTHONPATH=src python scripts/summarize_qwen_multitask.py \
  --input-dir "$REPORT" \
  --split valid_train \
  --per-type 1 \
  --variants C E F \
  --summary C=reports/multitask/qwen3_1.7b_valid_train_1_per_type/C/summary.json
```

Fixed-task results:

| Policy | Success | Steps | Parsed | Repairs | True fallback | Repeats |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C exact action, recent text | 0/6 | 180 | 173 | 0 | 7 | 23 |
| E exact action, explicit state | 0/6 | 180 | 145 | 0 | 35 | 31 |
| F explicit state + prerequisite repair | 2/6 | 153 | 145 | 4 | 4 | 5 |

F solved the simple pick-and-place task in 24 steps and the two-object task in
9 steps. Both ended through ALFWorld's own successful terminal transition and
positive reward. Four prerequisite repairs were used across all six tasks;
all 153 executed F actions were members of their current admissible set. This
six-task result demonstrates the mechanism but remains too small to estimate
a stable benchmark success rate.

The complete C/E/F comparison and step-level state snapshots are under
`reports/state_tracking/qwen3_1.7b_valid_train_1_per_type/`.

## Evolve evidence-backed experiences from failures

The first self-evolving loop now uses persisted trajectories as its only
experience source:

```text
F failures
  -> extract exp-v1 (target lock, novel exploration, ordered subgoals)
  -> evaluate G
  -> inspect G failures
  -> evolve exp-v2 (+ location-type diversity)
  -> evaluate H on source and disjoint held-out tasks
```

An experience JSON contains a schema version, experience version, parent
version, source policy, source episode IDs, and typed rules. Each rule carries
its instruction plus concrete evidence records identifying the source
episode, task, step, action, and observed failure. The rollout run contract
stores both the experience version and SHA-256, so replacing a file under the
same version cannot silently resume old trajectories.

Generate and evolve the checked-in experiences:

```bash
PYTHONPATH=src python scripts/extract_failure_experiences.py \
  --episodes-root reports/state_tracking/qwen3_1.7b_valid_train_1_per_type/F \
  --version exp-v1-from-f-failures \
  --output reports/experience_v1/exp_v1.json

PYTHONPATH=src python scripts/evolve_failure_experiences.py \
  --base reports/experience_v1/exp_v1.json \
  --episodes-root reports/experience_v1/qwen3_1.7b_valid_train_1_per_type/G \
  --version exp-v2-from-g-failures \
  --output reports/experience_v1/exp_v2.json
```

Run H with exp-v2. `--task-offset 0` selects the source-task set and offset 1
selects the lexicographically next task in every ALFWorld category:

```bash
export ALFWORLD_DATA=/path/to/alfworld
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src python \
  scripts/run_qwen_multitask_variant.py \
  --model-path ../models/Qwen3-1.7B \
  --device cuda:0 \
  --split valid_train \
  --per-type 1 \
  --task-offset 1 \
  --variant H \
  --experience-file reports/experience_v1/exp_v2.json \
  --seed 42 \
  --max-steps 30 \
  --max-new-tokens 96 \
  --max-history-items 6 \
  --output-dir reports/experience_v1/qwen3_1.7b_valid_train_heldout_offset1/H
```

Strict current-code comparisons:

| Task set | F: state + repair | H: exp-v2 | H steps | H repeats |
| --- | ---: | ---: | ---: | ---: |
| Source tasks, offset 0 | 2/6 | 6/6 | 74 | 1 |
| Held-out tasks, offset 1 | 1/6 | 4/6 | 96 | 0 |

The source and held-out task IDs are disjoint. On held-out tasks, H transfers
to clean, cool, and heat tasks that F fails. The held-out clean goal changes
from bowl/shelf to cloth/cart, so the rule follows structured TaskSpec targets
instead of memorizing a source object. H still fails held-out light and simple
pick-and-place, and six tasks per set is a mechanism test rather than a stable
ALFWorld score.

Across the 30 checked-in episodes in this stage, all 580 executed actions were
admissible, all transition chains were continuous, all experience rule IDs
resolved against the recorded experience file, and every one of the 17
successes was an ALFWorld terminal transition with positive reward. Full
reports are under `reports/experience_v1/`.

## Evaluate experience generalization on 60 disjoint tasks

The next evaluation expands the sample from one to ten tasks per ALFWorld
category. It uses stable task offset 2, so all 60 evaluation task IDs are
disjoint from both the offset-0/1 mechanism tests and the four task IDs cited
as exp-v2 evidence. F and H run on exactly the same tasks with identical model,
seed, decoding, history, and 30-step limits; H differs only by loading exp-v2.
Six task types are split into three non-overlapping two-type shards so three
GPUs can run concurrently, then merged only after validating their run
contracts and task IDs.

```bash
REPORT=reports/generalization_60/qwen3_1.7b_valid_train_offset2_10_per_type

PYTHONPATH=src python scripts/merge_qwen_multitask_shards.py \
  --shard-root "$REPORT/H" \
  --output "$REPORT/H/summary.json"

PYTHONPATH=src python scripts/summarize_qwen_multitask.py \
  --input-dir "$REPORT" \
  --split valid_train \
  --per-type 10 \
  --task-offset 2 \
  --variants F H

PYTHONPATH=src python scripts/audit_multitask_report.py \
  --report-dir "$REPORT" \
  --experience-file reports/experience_v1/exp_v2.json \
  --output "$REPORT/audit.json"
```

Results by task type:

| Task type | F | H | Delta |
| --- | ---: | ---: | ---: |
| Look under light | 3/10 | 5/10 | +2 |
| Simple pick/place | 4/10 | 4/10 | 0 |
| Clean then place | 2/10 | 5/10 | +3 |
| Cool then place | 3/10 | 5/10 | +2 |
| Heat then place | 1/10 | 9/10 | +8 |
| Place two objects | 2/10 | 2/10 | 0 |
| **Overall** | **15/60 (25%)** | **30/60 (50%)** | **+15** |

On matched tasks, H gained 18 successes and lost 3 relative to F. The
two-sided exact McNemar/binomial p-value over those 21 discordant pairs is
0.00149. This is evidence that exp-v2 transfers beyond its four evidence task
IDs on this fixed sample, with most of the gain coming from heat tasks; it is
not yet a claim about the official ALFWorld test-set score. Simple pick/place
and two-object tasks receive no exp-v2 rules and show no change.

The checked-in audit covers 120 episodes and 2,912 transitions. It validates
admissible executed actions, continuous observation chains, state snapshots,
native terminal rewards for successes, exact F/H task matching, experience
version and SHA-256, rule IDs and task-type scope, and zero overlap with
experience evidence tasks. The full paired table, raw model responses, state
snapshots, and readable trajectories are under
`reports/generalization_60/qwen3_1.7b_valid_train_offset2_10_per_type/`.
