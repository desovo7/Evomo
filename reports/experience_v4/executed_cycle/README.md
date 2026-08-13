# Executed exp-v4 post-rollout cycle

This directory was produced by the non-adoption executor configuration
`configs/experience_v4_executed_cycle.json`.

| Stage | Jobs | Output evidence |
| --- | ---: | --- |
| development audit | 1 | 200 episodes, 158 successes, 42 failures |
| experience evolution | 1 | exp-v4 rebuilt byte-for-byte |
| evolution audit | 1 | all 42 failure source IDs resolved |
| validation postprocess | 2 concurrent | 140 paired tasks and evaluation audit |
| candidate gate | 1 | `retain_candidate`, stable exp-v3 |
| cycle manifest | 1 | 12 artifacts, 1,954 content records |
| manifest audit | 1 | `replay_equal: true` |

`executor/` contains eight command logs, the immutable stage state, and 41
SHA-256-chained events. The first invocation executed all seven stages. The
second invocation verified each output hash and emitted seven
`stage_recovered` events without launching any job. `executor_audit.json`
checks the config hash, command hashes, one-to-one job start/finish events,
return codes, log hashes, stage output hashes, event chain and final state
anchor.

No evaluation trajectory is used as learning evidence: only the 42 failed
`valid_train` episodes feed experience evolution; `valid_seen` is consumed
afterward by the paired validation and gate.
