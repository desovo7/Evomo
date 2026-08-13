# Complete valid-unseen benchmark

This report covers every playable local ALFWorld `valid_unseen` task rather
than a balanced prefix sample.

- Task count: 134 per policy.
- F baseline: 32/134 (23.9%).
- I with exp-v3: 114/134 (85.1%).
- Paired net gain: 82 tasks.
- Total trajectories: 268 episodes and 5,840 steps.

Artifacts:

- [`qwen3_1.7b_all_134/README.md`](qwen3_1.7b_all_134/README.md): aggregate
  and per-task comparison.
- [`qwen3_1.7b_all_134/audit.json`](qwen3_1.7b_all_134/audit.json): trajectory,
  experience, source-separation, and exact dataset-coverage audit.
- [`qwen3_1.7b_all_134/failure_analysis.json`](qwen3_1.7b_all_134/failure_analysis.json):
  deterministic signatures for all 20 remaining exp-v3 failures.
