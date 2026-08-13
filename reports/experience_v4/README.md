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

The later `cycle_executor/` directory demonstrates safe adoption and resume
of this pre-executor cycle. Its `events.jsonl` contains two runs and 13
SHA-256-chained events: one sealed-manifest adoption followed by one complete
four-stage recovery. `cycle_executor_audit.json` verifies the immutable config,
stage output hashes, event chain and manifest replay. No model job was launched
during adoption.

`executed_cycle/` is stronger execution evidence: it uses the historical
trajectories only as immutable rollout inputs, then actually launches every
post-rollout project CLI through the executor. The candidate is regenerated
byte-for-byte, the paired validation is reprocessed, the gate and manifest are
rebuilt, and the manifest is independently replayed. Its second invocation
recovers all seven stages without launching another job.
