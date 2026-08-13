# Experience evolution v3

This stage evolves `exp-v3-from-h-offset2-failures` from the 30 failed H
episodes in the 60-task offset-2 evaluation, then compares exp-v2 and exp-v3
on 42 new offset-12 tasks.

- [`exp_v3.json`](exp_v3.json): versioned experience and trajectory evidence.
- [`evolution_audit.json`](evolution_audit.json): lineage and evidence audit.
- [`qwen3_1.7b_valid_train_offset12_7_per_type/`](qwen3_1.7b_valid_train_offset12_7_per_type/):
  paired summaries, audit, step JSONL, episode JSONL, and readable traces.

The matched result is H/exp-v2 19/42 versus I/exp-v3 28/42, a paired net gain
of nine tasks with exact two-sided p=0.02246. This is a second disjoint
`valid_train` sample, not an official ALFWorld test-set score.
