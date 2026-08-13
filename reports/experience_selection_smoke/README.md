# Decision-selected experience smoke trajectory

- Source command: `--experience-decision reports/experience_v4/decision.json`
- Gate outcome: `retain_candidate`
- Resolved stable experience: `exp-v3-from-h-offset2-failures`
- Task: one `valid_train/pick_and_place_simple` episode
- Result: 1/1 success in 10 steps
- Decision replay SHA-256:
  `d68d769eadcd11b83c3bfdc10654e0fd9244cd54800adbded151ab1479be4712`
- Provenance equality: run config = Episode = all 10 Episode steps = all 10
  flattened step-log records
- Human-readable trajectory contains the same decision digest
- Audit status: passed

This smoke demonstrates the runtime data flow:

```text
decision.json
  -> replay five content-addressed gate inputs
  -> resolve selected_stable (exp-v3, not retained exp-v4)
  -> construct experience-guided policy
  -> execute ALFWorld transitions
  -> persist selection provenance at run, episode, and step levels
  -> independently replay and audit the saved trajectory
```
