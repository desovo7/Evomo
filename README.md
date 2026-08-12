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
3. **Environment adapter:** map ALFWorld `reset/step` results to the data
   contract without involving a language model.
4. **Policy contract:** map an observation to an `ActionDecision`, first with
   random and scripted policies.
5. **Rollout runner:** connect task, environment, policy, and recorder for one
   episode.
6. **Persistence and resume:** manifests, deduplication, interrupted-run
   recovery, and batch output layout.
7. **Configuration and observability:** validated configs, structured logs,
   seeds, and run summaries.
8. **Baseline CLI:** execute reproducible random, expert, and later Qwen
   baselines over selected splits.

Parts 1 and 2 now exist. The executable data path is:

```text
ALFWorld data -> TaskSpec manifest -> EpisodeRecorder -> StepRecord -> Episode JSONL
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
