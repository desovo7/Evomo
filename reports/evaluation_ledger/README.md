# ALFWorld evaluation exposure ledger

This ledger records every auditable full evaluation exposure in chronological
evidence order:

| Order | Cycle | Split | Tasks | Prior overlap |
| ---: | --- | --- | ---: | ---: |
| 1 | full-valid-unseen-exp-v3 | valid_unseen | 134 | 0 |
| 2 | full-valid-seen-exp-v4-gate | valid_seen | 140 | 0 |
| 3 | qwen3-1.7b-live-offset2-full-unseen | valid_unseen | 134 | 134 |

There are 274 unique evaluation tasks. The live cycle generated new model
trajectories but reused all 134 task identities from order 1, so the audit
correctly reports `protocol_clean: false`. This is historical disclosure, not
a claim that the artifacts are invalid: it limits the result to repeated
measurement rather than new blind promotion evidence.

Future cycle plans reserve evaluation task IDs before validation rollout.
`valid_seen` and `valid_unseen` reservations now both fail because every local
task has been exposed. A new promotion requires an unexposed evaluation pool.

Files:

- `ledger.json`: full task identities and content-addressed evidence;
- `audit.json`: independently reconstructed overlap counts;
- `receipts/`: durable receipts for each historical registration.

The audit also re-hashes all eight source files referenced by the three
entries. For the live cycle it replays both the cycle manifest and executor
state, rather than trusting stored summary fields.
