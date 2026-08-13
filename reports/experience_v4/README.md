# Exp-v4 evolution cycle

This directory contains the first complete content-addressed evolution cycle:

- incumbent: `exp-v3-from-h-offset2-failures`;
- development: 200 `valid_train` episodes, 158 successes and 42 failures;
- candidate: `exp-v4-from-full-valid-train-failures`, grounded in exactly
  those 42 failures;
- paired validation: 140 `valid_seen` tasks per version;
- outcome: `retain_candidate`, leaving exp-v3 stable.

`cycle_manifest.json` binds the two experience files, both full trajectory
trees, their summaries and audits, the paired comparison, and the gate
decision to 12 content-addressed artifact records. `cycle_manifest_audit.json`
independently replays the semantic chain and the gate decision. It covers 480
episodes and 1,954 files without reading any evaluation episode as learning
evidence.
