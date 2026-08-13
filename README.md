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
  --source-split valid_train \
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

## Evolve exp-v3 and evaluate on a second disjoint set

The next evolution consumes all 30 H failures from the offset-2 run. The
general evolution now merges new evidence into existing rules, expands rule
scope from observed failures, bounds retained evidence with stable category
coverage, and records the prior version as its parent. Recursive episode
discovery lets it consume the three-GPU shard logs directly.

The failures reveal that exp-v2 never applied to simple pick/place or
two-object tasks, where the policy repeatedly manipulated non-target objects.
Exp-v3 adds direct target-lock and ordered-delivery evidence for both types.
For two-object tasks, an instance already delivered to the destination is
skipped using a placement fact derived from the environment's successful
`move` response.

```bash
PYTHONPATH=src python scripts/evolve_failure_experiences.py \
  --base reports/experience_v1/exp_v2.json \
  --episodes-root \
    reports/generalization_60/qwen3_1.7b_valid_train_offset2_10_per_type/H \
  --source-split valid_train \
  --version exp-v3-from-h-offset2-failures \
  --output reports/experience_v2/exp_v3.json

PYTHONPATH=src python scripts/audit_experience_evolution.py \
  --base reports/experience_v1/exp_v2.json \
  --child reports/experience_v2/exp_v3.json \
  --episodes-root \
    reports/generalization_60/qwen3_1.7b_valid_train_offset2_10_per_type/H \
  --source-split valid_train \
  --output reports/experience_v2/evolution_audit.json
```

The evolution audit resolves each retained new evidence item to a real source
episode and, where present, its exact step and action. It verifies 30 failed
source episodes, source policy and base-version consistency, parent lineage,
and 138 new evidence records across four rules.

Offset 12 with seven tasks per category is the largest balanced contiguous
sample that does not reuse indices 0 through 11 because light tasks have only
19 playable `valid_train` entries. It yields 42 tasks disjoint from the
exp-v3 source set and all retained exp-v2/v3 evidence. H and I use identical
prompts, model, tasks, seeds, greedy decoding, history, and limits; H loads
exp-v2 while I loads exp-v3.

| Task type | H / exp-v2 | I / exp-v3 | Delta |
| --- | ---: | ---: | ---: |
| Look under light | 2/7 | 1/7 | -1 |
| Simple pick/place | 2/7 | 5/7 | +3 |
| Clean then place | 4/7 | 4/7 | 0 |
| Cool then place | 3/7 | 5/7 | +2 |
| Heat then place | 6/7 | 6/7 | 0 |
| Place two objects | 2/7 | 7/7 | +5 |
| **Overall** | **19/42 (45.2%)** | **28/42 (66.7%)** | **+9** |

There are 11 I-only successes and two H-only successes (two-sided exact
McNemar/binomial p=0.02246). Exp-v3 improves both newly covered categories
and preserves heat, but the light regression shows evolution is not assumed
to be monotonic. The next version should diagnose that regression rather than
accept every broader rule unconditionally.

The report audit covers 84 episodes and 1,741 transitions, validates both
experience files independently by version and SHA-256, and confirms zero task
overlap with either version's evidence. Full logs are under
`reports/experience_v2/qwen3_1.7b_valid_train_offset12_7_per_type/`.

## Gate experience promotion on blind unseen scenes

Exp-v3 improved overall on offset 12 but regressed by one light task. The next
increment therefore implements a conservative per-task-type promotion gate:
promote the candidate only when its candidate-only successes exceed the
incumbent-only successes; retain the incumbent on a tie or regression. The
selection comparison promotes exp-v3 for simple, cool, and two-object tasks,
and retains exp-v2 for light, clean, and heat.

The compiler produces an immutable `champion-v1` ExperienceSet plus a
manifest containing every decision, paired counts, comparison SHA-256, input
experience versions and hashes, and output hash. A separate audit reconstructs
the champion byte-for-byte and verifies that each task type renders exactly
the same rule text as its selected source version. It rejects rule merging if
the same rule ID changed its kind or instruction between versions.

```bash
PYTHONPATH=src python scripts/promote_experience_by_task_type.py \
  --comparison \
    reports/experience_v2/qwen3_1.7b_valid_train_offset12_7_per_type/comparison.json \
  --incumbent reports/experience_v1/exp_v2.json \
  --candidate reports/experience_v2/exp_v3.json \
  --version champion-v1-from-offset12-promotion \
  --output reports/experience_v3/champion_v1.json \
  --manifest reports/experience_v3/promotion_manifest.json
```

The fixed H/exp-v2, I/exp-v3, and J/champion policies were then evaluated on
the same 42 `valid_unseen` tasks, seven per category. No `valid_unseen` task
was used to extract experiences or make promotion decisions.

| Task type | H / exp-v2 | I / exp-v3 | J / champion |
| --- | ---: | ---: | ---: |
| Look under light | 3/7 | 6/7 | 3/7 |
| Simple pick/place | 6/7 | 7/7 | 7/7 |
| Clean then place | 7/7 | 7/7 | 7/7 |
| Cool then place | 7/7 | 7/7 | 7/7 |
| Heat then place | 7/7 | 7/7 | 7/7 |
| Place two objects | 1/7 | 4/7 | 4/7 |
| **Overall** | **31/42 (73.8%)** | **38/42 (90.5%)** | **35/42 (83.3%)** |

Exp-v3 beats exp-v2 by seven paired successes (eight gains, one regression;
exact p=0.0391). Champion improves over exp-v2 by four, but loses three net
successes relative to exp-v3 because the offset-12 light rollback does not
generalize to unseen scenes. The blind validation gate therefore records
`reject_champion`; exp-v3 remains the deployment candidate. This negative
result demonstrates why an evolving agent must validate and reject proposed
memory changes instead of assuming every local rollback is beneficial.

The unseen audit covers 126 episodes and 2,243 transitions. It validates all
three experience hashes and scopes, exact task matching, admissible actions,
continuous transition chains, native success rewards, and zero overlap with
experience evidence or source tasks. Full artifacts are under
`reports/experience_v3/`.

## Run the complete playable valid-unseen benchmark

Balanced samples are useful for diagnosis but omit tasks when ALFWorld
categories have different sizes. The runner now supports `--all-tasks`, which
selects every playable task in stable task-type and task-ID order. The
selection mode is part of the immutable run contract and shard merge
invariants. A discovery-backed audit independently re-enumerates the dataset
and requires exact task-ID equality, so a runner and summary cannot silently
agree on the same incomplete subset.

The complete local `valid_unseen` split contains 134 playable tasks:

- 18 light, 24 simple pick/place, 31 clean, 21 cool, 23 heat, and 17
  two-object tasks.

F and I were each split across three GPUs by disjoint task types and run on
the same 134 IDs, seeds, model, greedy decoding, history, token limit, and
30-step budget. F uses state tracking and prerequisite repair without learned
experience; I loads exp-v3.

```bash
REPORT=reports/full_valid_unseen/qwen3_1.7b_all_134

PYTHONPATH=src python scripts/summarize_qwen_multitask.py \
  --input-dir "$REPORT" \
  --split valid_unseen \
  --all-tasks \
  --variants F I

PYTHONPATH=src python scripts/audit_multitask_report.py \
  --report-dir "$REPORT" \
  --variants F I \
  --variant-experience I=reports/experience_v2/exp_v3.json \
  --exclude-episodes-root \
    reports/generalization_60/qwen3_1.7b_valid_train_offset2_10_per_type/H \
  --data-root /path/to/alfworld \
  --output "$REPORT/audit.json"
```

| Task type | F | I / exp-v3 | Delta |
| --- | ---: | ---: | ---: |
| Look under light | 3/18 | 16/18 | +13 |
| Simple pick/place | 12/24 | 21/24 | +9 |
| Clean then place | 7/31 | 28/31 | +21 |
| Cool then place | 1/21 | 19/21 | +18 |
| Heat then place | 5/23 | 23/23 | +18 |
| Place two objects | 4/17 | 7/17 | +3 |
| **Overall** | **32/134 (23.9%)** | **114/134 (85.1%)** | **+82** |

The paired comparison contains 86 I-only successes and four F-only successes
(two-sided exact McNemar/binomial p=4.32e-21). Exp-v3 also reduces total
environment steps from 3,489 to 2,351. This is the first result here covering
every playable local `valid_unseen` task rather than a balanced subset.

The audit validates 268 episodes and 5,840 transitions, exact discovery
coverage of all 134 tasks, admissible actions, continuous chains, native
success rewards, state snapshots, experience scope and hash, and source-task
separation. The deterministic failure manifest classifies all 20 I failures:
eight target-not-acquired, six destination-navigation loops, four retakes of
an already delivered target, and two incomplete light interactions. These are
the evidence candidates for exp-v4; no experience is learned from the same
split during this benchmark run.

Full trajectories and reports are under
`reports/full_valid_unseen/qwen3_1.7b_all_134/`.

## Evolve exp-v4 only from development data

The complete `valid_unseen` result above remains frozen and is not an exp-v4
training source. A protocol gate now permits experience extraction only from
`train` or `valid_train`; it rejects `valid_seen`, `valid_unseen`, mixed, or
mislabeled trajectory collections. Evaluation audits still require zero
overlap with both experience evidence and development source tasks.

Exp-v3 was run over all 200 playable `valid_train` tasks on three GPUs. It
solved 158/200 (79.0%); the 42 failures were classified before changing the
policy. Two deterministic progress failures had direct action evidence:

- nine episodes took a target instance back after delivering it in a
  two-object task;
- six episodes repeatedly switched between destination instances while
  holding a ready target instead of opening the current closed destination.

Exp-v4 adds one scoped executable rule for each failure. It does not add a
new light-search rule because those failures did not expose one sufficiently
specific causal action pattern.

```bash
PYTHONPATH=src python scripts/evolve_failure_experiences.py \
  --base reports/experience_v2/exp_v3.json \
  --episodes-root reports/experience_v4/qwen3_1.7b_valid_train_all_200/I \
  --source-split valid_train \
  --enable-progress-rules \
  --version exp-v4-from-full-valid-train-failures \
  --output reports/experience_v4/exp_v4.json

PYTHONPATH=src python scripts/audit_experience_evolution.py \
  --base reports/experience_v2/exp_v3.json \
  --child reports/experience_v4/exp_v4.json \
  --episodes-root reports/experience_v4/qwen3_1.7b_valid_train_all_200/I \
  --source-split valid_train \
  --output reports/experience_v4/evolution_audit.json
```

The evolution audit resolves all 88 newly retained evidence records to the
42 failed source episodes. Regeneration from the same trajectories is byte
identical; exp-v4 SHA-256 is
`f7f6d2692daf069dbf141b6ec35505af6c303eb54d2376592618dee5730283a8`.

Exp-v3 (I) and exp-v4 (K) were then evaluated on every playable `valid_seen`
task without using validation feedback to edit the candidate:

| Task type | I / exp-v3 | K / exp-v4 | Delta |
| --- | ---: | ---: | ---: |
| Look under light | 8/13 | 8/13 | 0 |
| Simple pick/place | 33/35 | 33/35 | 0 |
| Clean then place | 20/27 | 22/27 | +2 |
| Cool then place | 18/25 | 18/25 | 0 |
| Heat then place | 12/16 | 12/16 | 0 |
| Place two objects | 19/24 | 19/24 | 0 |
| **Overall** | **110/140 (78.6%)** | **112/140 (80.0%)** | **+2** |

K has two candidate-only successes, no regressions, and reduces total steps
from 2,165 to 2,109. The paired exact p-value is 0.5, so this is a positive
but statistically weak validation result rather than evidence of a large
general improvement. Exp-v4 is retained as a no-regression candidate;
exp-v3 remains the stable version backed by the frozen full `valid_unseen`
benchmark. The validation audit covers 280 episodes and 4,274 transitions,
all 140 discovered tasks, zero evidence/source overlap, and both immutable
experience hashes. Full artifacts are under `reports/experience_v4/`.

The retention decision is generated rather than handwritten. The candidate
gate consumes the paired comparison, validation audit, evolution audit, and
both experience JSON files. It verifies their SHA-256 values, parent lineage,
development/evaluation roles, exact discovery coverage, zero source/evidence
overlap, and paired-count consistency before applying this fixed rule:

- reject if any incumbent-only success is observed;
- promote only for at least one candidate-only success, no regressions, and
  an exact paired p-value at or below 0.05;
- otherwise retain a positive no-regression candidate for more evidence while
  leaving the incumbent stable.

```bash
PYTHONPATH=src python scripts/gate_experience_candidate.py \
  --comparison \
    reports/experience_v4/qwen3_1.7b_valid_seen_all_140/comparison.json \
  --validation-audit \
    reports/experience_v4/qwen3_1.7b_valid_seen_all_140/audit.json \
  --evolution-audit reports/experience_v4/evolution_audit.json \
  --incumbent reports/experience_v2/exp_v3.json \
  --candidate reports/experience_v4/exp_v4.json \
  --output reports/experience_v4/decision.json

PYTHONPATH=src python scripts/audit_experience_candidate_gate.py \
  --decision reports/experience_v4/decision.json \
  --output reports/experience_v4/decision_audit.json
```

The replay audit reconstructs the complete schema-v2 decision byte-for-byte
from five content-addressed inputs. For this run it returns
`retain_candidate`; `selected_stable.version` remains exp-v3.
