# Experience promotion and blind validation

This stage compiles a per-task-type champion from exp-v2 and exp-v3 using the
offset-12 paired comparison, then evaluates the champion and both fixed
versions on 42 `valid_unseen` tasks.

- [`promotion_manifest.json`](promotion_manifest.json): input hashes,
  criterion, per-type paired counts, decisions, and compiled output hash.
- [`promotion_audit.json`](promotion_audit.json): reproducibility and rule
  render-equivalence audit.
- [`champion_v1.json`](champion_v1.json): compiled experience candidate.
- [`promotion_validation.json`](promotion_validation.json): blind acceptance
  decision; the champion is rejected because it scores below exp-v3.
- [`qwen3_1.7b_valid_unseen_7_per_type/`](qwen3_1.7b_valid_unseen_7_per_type/):
  all H/I/J episodes, step logs, readable trajectories, comparison, and audit.

Blind results are exp-v2 31/42, exp-v3 38/42, and champion 35/42. Exp-v3
remains the current deployment candidate.
