# Qwen3-1.7B ALFWorld multi-task prompt comparison

- Split: `valid_seen`
- Tasks per prompt: 140
- Task selection: all playable tasks
- Stable task offset: 0
- Integrity audit: [`audit.json`](audit.json)
- Prompt I experience: `exp-v3-from-h-offset2-failures`
- Prompt K experience: `exp-v4-from-full-valid-train-failures`

| Prompt | Success | Parsed actions | Repaired | Experience overrides | True fallback | Repeats | Unchanged obs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| I | 110/140 (78.6%) | 1951/2165 | 0 | 1900 | 21 | 9 | 9 |
| K | 112/140 (80.0%) | 1892/2109 | 0 | 1853 | 16 | 7 | 7 |

## Paired success analysis

- Baseline: `I`; candidate: `K`
- Candidate-only successes: 2
- Baseline-only successes: 0
- Exact paired p-value: 0.5
- The exact p-value is a two-sided McNemar/binomial test over discordant task pairs.

| Task type | Baseline only | Candidate only | Both succeed | Both fail | Success delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | 0 | 0 | 8 | 5 | +0 |
| pick_and_place_simple | 0 | 0 | 33 | 2 | +0 |
| pick_clean_then_place_in_recep | 0 | 2 | 20 | 5 | +2 |
| pick_cool_then_place_in_recep | 0 | 0 | 18 | 7 | +0 |
| pick_heat_then_place_in_recep | 0 | 0 | 12 | 4 | +0 |
| pick_two_obj_and_place | 0 | 0 | 19 | 5 | +0 |

## Per-task results

### Prompt I by task type

| Task type | Success | Rate | Steps |
| --- | ---: | ---: | ---: |
| look_at_obj_in_light | 8/13 | 61.5% | 311 |
| pick_and_place_simple | 33/35 | 94.3% | 345 |
| pick_clean_then_place_in_recep | 20/27 | 74.1% | 409 |
| pick_cool_then_place_in_recep | 18/25 | 72.0% | 409 |
| pick_heat_then_place_in_recep | 12/16 | 75.0% | 246 |
| pick_two_obj_and_place | 19/24 | 79.2% | 445 |

### Prompt I

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | False | 30 | 0 | 30 |
| look_at_obj_in_light | False | 30 | 0 | 30 |
| look_at_obj_in_light | True | 13 | 0 | 12 |
| look_at_obj_in_light | True | 21 | 0 | 21 |
| look_at_obj_in_light | True | 19 | 0 | 19 |
| look_at_obj_in_light | False | 30 | 2 | 19 |
| look_at_obj_in_light | True | 25 | 3 | 14 |
| look_at_obj_in_light | False | 30 | 1 | 26 |
| look_at_obj_in_light | True | 13 | 0 | 12 |
| look_at_obj_in_light | True | 19 | 0 | 19 |
| look_at_obj_in_light | False | 30 | 0 | 30 |
| look_at_obj_in_light | True | 21 | 0 | 20 |
| look_at_obj_in_light | True | 30 | 0 | 29 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 19 | 0 | 18 |
| pick_and_place_simple | True | 14 | 0 | 13 |
| pick_and_place_simple | True | 10 | 0 | 9 |
| pick_and_place_simple | True | 10 | 0 | 9 |
| pick_and_place_simple | True | 8 | 0 | 7 |
| pick_and_place_simple | True | 8 | 0 | 7 |
| pick_and_place_simple | True | 13 | 0 | 12 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 8 | 0 | 7 |
| pick_and_place_simple | True | 10 | 0 | 9 |
| pick_and_place_simple | True | 15 | 0 | 14 |
| pick_and_place_simple | True | 10 | 0 | 9 |
| pick_and_place_simple | True | 8 | 0 | 7 |
| pick_and_place_simple | True | 6 | 0 | 5 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | False | 30 | 0 | 30 |
| pick_and_place_simple | True | 9 | 0 | 8 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 5 | 0 | 4 |
| pick_and_place_simple | True | 6 | 0 | 5 |
| pick_and_place_simple | True | 14 | 0 | 13 |
| pick_and_place_simple | False | 30 | 0 | 4 |
| pick_and_place_simple | True | 10 | 0 | 9 |
| pick_and_place_simple | True | 8 | 0 | 7 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 6 | 0 | 5 |
| pick_and_place_simple | True | 7 | 0 | 6 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 7 | 0 | 6 |
| pick_and_place_simple | True | 14 | 0 | 13 |
| pick_and_place_simple | True | 12 | 0 | 11 |
| pick_and_place_simple | True | 9 | 0 | 8 |
| pick_and_place_simple | True | 6 | 0 | 5 |
| pick_and_place_simple | True | 9 | 0 | 8 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | True | 10 | 0 | 9 |
| pick_clean_then_place_in_recep | True | 11 | 0 | 10 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 6 |
| pick_clean_then_place_in_recep | True | 10 | 0 | 8 |
| pick_clean_then_place_in_recep | True | 7 | 0 | 6 |
| pick_clean_then_place_in_recep | True | 7 | 0 | 6 |
| pick_clean_then_place_in_recep | True | 10 | 0 | 9 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | True | 6 | 0 | 5 |
| pick_clean_then_place_in_recep | True | 10 | 0 | 8 |
| pick_clean_then_place_in_recep | True | 11 | 0 | 9 |
| pick_clean_then_place_in_recep | True | 11 | 0 | 9 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 9 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 6 |
| pick_clean_then_place_in_recep | True | 6 | 0 | 5 |
| pick_clean_then_place_in_recep | True | 26 | 0 | 24 |
| pick_clean_then_place_in_recep | True | 11 | 0 | 9 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 6 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 8 |
| pick_clean_then_place_in_recep | True | 6 | 0 | 5 |
| pick_clean_then_place_in_recep | True | 14 | 0 | 12 |
| pick_cool_then_place_in_recep | True | 13 | 0 | 11 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | True | 10 | 0 | 10 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | True | 12 | 0 | 10 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | True | 7 | 0 | 6 |
| pick_cool_then_place_in_recep | True | 10 | 0 | 8 |
| pick_cool_then_place_in_recep | True | 13 | 0 | 12 |
| pick_cool_then_place_in_recep | True | 11 | 0 | 9 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | True | 10 | 0 | 8 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | True | 6 | 0 | 5 |
| pick_cool_then_place_in_recep | True | 8 | 0 | 7 |
| pick_cool_then_place_in_recep | True | 6 | 0 | 6 |
| pick_cool_then_place_in_recep | True | 12 | 0 | 10 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 29 |
| pick_cool_then_place_in_recep | True | 14 | 0 | 12 |
| pick_cool_then_place_in_recep | True | 19 | 0 | 17 |
| pick_cool_then_place_in_recep | True | 14 | 0 | 12 |
| pick_cool_then_place_in_recep | True | 12 | 0 | 10 |
| pick_cool_then_place_in_recep | True | 11 | 0 | 10 |
| pick_cool_then_place_in_recep | True | 11 | 0 | 9 |
| pick_heat_then_place_in_recep | False | 30 | 0 | 30 |
| pick_heat_then_place_in_recep | True | 18 | 0 | 16 |
| pick_heat_then_place_in_recep | False | 30 | 0 | 30 |
| pick_heat_then_place_in_recep | True | 7 | 0 | 6 |
| pick_heat_then_place_in_recep | True | 9 | 0 | 7 |
| pick_heat_then_place_in_recep | True | 10 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 6 | 0 | 5 |
| pick_heat_then_place_in_recep | True | 9 | 0 | 8 |
| pick_heat_then_place_in_recep | False | 30 | 0 | 30 |
| pick_heat_then_place_in_recep | True | 10 | 0 | 10 |
| pick_heat_then_place_in_recep | False | 30 | 0 | 30 |
| pick_heat_then_place_in_recep | True | 12 | 0 | 11 |
| pick_heat_then_place_in_recep | True | 11 | 0 | 10 |
| pick_heat_then_place_in_recep | True | 11 | 0 | 10 |
| pick_heat_then_place_in_recep | True | 11 | 0 | 10 |
| pick_heat_then_place_in_recep | True | 12 | 0 | 11 |
| pick_two_obj_and_place | True | 21 | 0 | 19 |
| pick_two_obj_and_place | True | 14 | 0 | 12 |
| pick_two_obj_and_place | True | 27 | 0 | 24 |
| pick_two_obj_and_place | True | 15 | 0 | 13 |
| pick_two_obj_and_place | True | 5 | 0 | 5 |
| pick_two_obj_and_place | True | 16 | 0 | 14 |
| pick_two_obj_and_place | True | 13 | 0 | 11 |
| pick_two_obj_and_place | True | 18 | 0 | 17 |
| pick_two_obj_and_place | False | 30 | 0 | 8 |
| pick_two_obj_and_place | True | 13 | 0 | 11 |
| pick_two_obj_and_place | False | 30 | 0 | 29 |
| pick_two_obj_and_place | True | 15 | 0 | 13 |
| pick_two_obj_and_place | True | 11 | 0 | 10 |
| pick_two_obj_and_place | True | 11 | 0 | 10 |
| pick_two_obj_and_place | False | 30 | 0 | 6 |
| pick_two_obj_and_place | True | 14 | 0 | 12 |
| pick_two_obj_and_place | False | 30 | 3 | 20 |
| pick_two_obj_and_place | True | 21 | 0 | 19 |
| pick_two_obj_and_place | True | 15 | 0 | 13 |
| pick_two_obj_and_place | True | 22 | 0 | 21 |
| pick_two_obj_and_place | True | 17 | 0 | 15 |
| pick_two_obj_and_place | True | 11 | 0 | 9 |
| pick_two_obj_and_place | True | 16 | 0 | 14 |
| pick_two_obj_and_place | False | 30 | 0 | 25 |

### Prompt K by task type

| Task type | Success | Rate | Steps |
| --- | ---: | ---: | ---: |
| look_at_obj_in_light | 8/13 | 61.5% | 311 |
| pick_and_place_simple | 33/35 | 94.3% | 345 |
| pick_clean_then_place_in_recep | 22/27 | 81.5% | 365 |
| pick_cool_then_place_in_recep | 18/25 | 72.0% | 409 |
| pick_heat_then_place_in_recep | 12/16 | 75.0% | 246 |
| pick_two_obj_and_place | 19/24 | 79.2% | 433 |

### Prompt K

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | False | 30 | 0 | 30 |
| look_at_obj_in_light | False | 30 | 0 | 30 |
| look_at_obj_in_light | True | 13 | 0 | 12 |
| look_at_obj_in_light | True | 21 | 0 | 21 |
| look_at_obj_in_light | True | 19 | 0 | 19 |
| look_at_obj_in_light | False | 30 | 2 | 19 |
| look_at_obj_in_light | True | 25 | 3 | 14 |
| look_at_obj_in_light | False | 30 | 1 | 26 |
| look_at_obj_in_light | True | 13 | 0 | 12 |
| look_at_obj_in_light | True | 19 | 0 | 19 |
| look_at_obj_in_light | False | 30 | 0 | 30 |
| look_at_obj_in_light | True | 21 | 0 | 20 |
| look_at_obj_in_light | True | 30 | 0 | 29 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 19 | 0 | 18 |
| pick_and_place_simple | True | 14 | 0 | 13 |
| pick_and_place_simple | True | 10 | 0 | 9 |
| pick_and_place_simple | True | 10 | 0 | 9 |
| pick_and_place_simple | True | 8 | 0 | 7 |
| pick_and_place_simple | True | 8 | 0 | 7 |
| pick_and_place_simple | True | 13 | 0 | 12 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 8 | 0 | 7 |
| pick_and_place_simple | True | 10 | 0 | 9 |
| pick_and_place_simple | True | 15 | 0 | 14 |
| pick_and_place_simple | True | 10 | 0 | 9 |
| pick_and_place_simple | True | 8 | 0 | 7 |
| pick_and_place_simple | True | 6 | 0 | 5 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | False | 30 | 0 | 30 |
| pick_and_place_simple | True | 9 | 0 | 8 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 5 | 0 | 4 |
| pick_and_place_simple | True | 6 | 0 | 5 |
| pick_and_place_simple | True | 14 | 0 | 13 |
| pick_and_place_simple | False | 30 | 0 | 4 |
| pick_and_place_simple | True | 10 | 0 | 9 |
| pick_and_place_simple | True | 8 | 0 | 7 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 6 | 0 | 5 |
| pick_and_place_simple | True | 7 | 0 | 6 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 7 | 0 | 6 |
| pick_and_place_simple | True | 14 | 0 | 13 |
| pick_and_place_simple | True | 12 | 0 | 11 |
| pick_and_place_simple | True | 9 | 0 | 8 |
| pick_and_place_simple | True | 6 | 0 | 5 |
| pick_and_place_simple | True | 9 | 0 | 8 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | True | 10 | 0 | 9 |
| pick_clean_then_place_in_recep | True | 11 | 0 | 10 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 10 | 0 | 8 |
| pick_clean_then_place_in_recep | True | 7 | 0 | 6 |
| pick_clean_then_place_in_recep | True | 7 | 0 | 6 |
| pick_clean_then_place_in_recep | True | 10 | 0 | 9 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | True | 6 | 0 | 5 |
| pick_clean_then_place_in_recep | True | 10 | 0 | 8 |
| pick_clean_then_place_in_recep | True | 11 | 0 | 9 |
| pick_clean_then_place_in_recep | True | 11 | 0 | 9 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 9 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 6 |
| pick_clean_then_place_in_recep | True | 6 | 0 | 5 |
| pick_clean_then_place_in_recep | True | 26 | 0 | 24 |
| pick_clean_then_place_in_recep | True | 11 | 0 | 9 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 8 |
| pick_clean_then_place_in_recep | True | 6 | 0 | 5 |
| pick_clean_then_place_in_recep | True | 14 | 0 | 12 |
| pick_cool_then_place_in_recep | True | 13 | 0 | 11 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | True | 10 | 0 | 10 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | True | 12 | 0 | 10 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | True | 7 | 0 | 6 |
| pick_cool_then_place_in_recep | True | 10 | 0 | 8 |
| pick_cool_then_place_in_recep | True | 13 | 0 | 12 |
| pick_cool_then_place_in_recep | True | 11 | 0 | 9 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | True | 10 | 0 | 8 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | True | 6 | 0 | 5 |
| pick_cool_then_place_in_recep | True | 8 | 0 | 7 |
| pick_cool_then_place_in_recep | True | 6 | 0 | 6 |
| pick_cool_then_place_in_recep | True | 12 | 0 | 10 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 29 |
| pick_cool_then_place_in_recep | True | 14 | 0 | 12 |
| pick_cool_then_place_in_recep | True | 19 | 0 | 17 |
| pick_cool_then_place_in_recep | True | 14 | 0 | 12 |
| pick_cool_then_place_in_recep | True | 12 | 0 | 10 |
| pick_cool_then_place_in_recep | True | 11 | 0 | 10 |
| pick_cool_then_place_in_recep | True | 11 | 0 | 9 |
| pick_heat_then_place_in_recep | False | 30 | 0 | 30 |
| pick_heat_then_place_in_recep | True | 18 | 0 | 16 |
| pick_heat_then_place_in_recep | False | 30 | 0 | 30 |
| pick_heat_then_place_in_recep | True | 7 | 0 | 6 |
| pick_heat_then_place_in_recep | True | 9 | 0 | 7 |
| pick_heat_then_place_in_recep | True | 10 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 6 | 0 | 5 |
| pick_heat_then_place_in_recep | True | 9 | 0 | 8 |
| pick_heat_then_place_in_recep | False | 30 | 0 | 30 |
| pick_heat_then_place_in_recep | True | 10 | 0 | 10 |
| pick_heat_then_place_in_recep | False | 30 | 0 | 30 |
| pick_heat_then_place_in_recep | True | 12 | 0 | 11 |
| pick_heat_then_place_in_recep | True | 11 | 0 | 10 |
| pick_heat_then_place_in_recep | True | 11 | 0 | 10 |
| pick_heat_then_place_in_recep | True | 11 | 0 | 10 |
| pick_heat_then_place_in_recep | True | 12 | 0 | 11 |
| pick_two_obj_and_place | True | 21 | 0 | 19 |
| pick_two_obj_and_place | True | 14 | 0 | 12 |
| pick_two_obj_and_place | True | 14 | 0 | 11 |
| pick_two_obj_and_place | True | 15 | 0 | 13 |
| pick_two_obj_and_place | True | 5 | 0 | 5 |
| pick_two_obj_and_place | True | 16 | 0 | 14 |
| pick_two_obj_and_place | True | 13 | 0 | 11 |
| pick_two_obj_and_place | True | 18 | 0 | 17 |
| pick_two_obj_and_place | False | 30 | 0 | 30 |
| pick_two_obj_and_place | True | 13 | 0 | 11 |
| pick_two_obj_and_place | False | 30 | 0 | 29 |
| pick_two_obj_and_place | True | 16 | 0 | 13 |
| pick_two_obj_and_place | True | 11 | 0 | 10 |
| pick_two_obj_and_place | True | 11 | 0 | 10 |
| pick_two_obj_and_place | False | 30 | 0 | 28 |
| pick_two_obj_and_place | True | 14 | 0 | 12 |
| pick_two_obj_and_place | False | 30 | 0 | 18 |
| pick_two_obj_and_place | True | 21 | 0 | 19 |
| pick_two_obj_and_place | True | 15 | 0 | 13 |
| pick_two_obj_and_place | True | 22 | 0 | 21 |
| pick_two_obj_and_place | True | 17 | 0 | 15 |
| pick_two_obj_and_place | True | 11 | 0 | 9 |
| pick_two_obj_and_place | True | 16 | 0 | 14 |
| pick_two_obj_and_place | False | 30 | 1 | 26 |
