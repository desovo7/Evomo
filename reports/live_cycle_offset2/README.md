# Live Qwen3-1.7B three-H800 evolution cycle

This is the first cycle executed from new model rollouts through the final
gate and manifest audit by one recoverable executor configuration.

## Data flow

```text
exp-v3
  -> 6 valid_train episodes on GPUs 0/1/2
  -> 3 failures
  -> exp-v5 candidate with 12 new evidence records
  -> 134 fresh exp-v3 valid_unseen episodes
  -> 134 fresh exp-v5 valid_unseen episodes
  -> paired audit and candidate gate
  -> retain exp-v5 candidate; keep exp-v3 stable
```

## Results

| Measure | exp-v3 incumbent | exp-v5 candidate |
| --- | ---: | ---: |
| valid_unseen successes | 114/134 | 116/134 |
| total steps | 2,351 | 2,333 |
| candidate-only successes | – | 2 |
| incumbent-only successes | 0 | – |

The improvements are one `pick_clean_then_place_in_recep` task and one
`pick_two_obj_and_place` task. The paired exact p-value is 0.5, so the result
is positive and has no observed regression, but it does not meet the fixed
0.05 promotion threshold.

## Execution evidence

- 13 stages, 20 jobs, 9 GPU rollout jobs;
- 274 new episodes with readable Markdown plus JSONL transitions;
- 1,130 content records covered by the cycle manifest;
- 83 SHA-256-chained executor events after one run and one resume;
- second run: 13 recovered stages and zero new jobs;
- manifest replay: passed;
- learning/evaluation task overlap: zero;
- selected stable experience: exp-v3.

`executor/logs/` contains a separate stdout/stderr log for every command.
`executor_audit.json` verifies commands, attempts, log hashes, stage outputs,
event order and the final state anchor. `cycle_manifest_audit.json` reparses
all development and validation trajectories and replays the gate decision.
