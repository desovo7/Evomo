# Evomo

Evomo is a learning-first implementation of a self-evolving agent for
ALFWorld using the local Qwen3-1.7B model.

## M0 decomposition by data flow

M0 is deliberately split into small, independently testable parts:

1. **Data contract (implemented now):** convert a task into an immutable
   `TaskSpec`, record environment transitions, finish an `Episode`, and store
   it as JSONL.
2. **Task discovery:** enumerate ALFWorld splits and convert raw game metadata
   into `TaskSpec` objects.
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

Only part 1 exists at this point. This keeps the first executable path small:

```text
raw task -> TaskSpec -> EpisodeRecorder -> StepRecord -> Episode -> JSONL
```

Run the example without installing the package:

```bash
PYTHONPATH=src python scripts/record_example.py
```

Run the standard-library tests:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```
