# Qwen3-1.7B ALFWorld multi-task prompt comparison

- Split: `valid_unseen`
- Tasks per prompt: 134
- Task selection: all playable tasks
- Stable task offset: 0
- Integrity audit: [`audit.json`](audit.json)
- Prompt I experience: `exp-v3-from-h-offset2-failures`
- Prompt K experience: `exp-v5-live-offset2-failures`

| Prompt | Success | Parsed actions | Repaired | Experience overrides | True fallback | Repeats | Unchanged obs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| I | 114/134 (85.1%) | 2081/2351 | 1 | 2089 | 24 | 9 | 9 |
| K | 116/134 (86.6%) | 2061/2333 | 0 | 2082 | 22 | 9 | 9 |

## Paired success analysis

- Baseline: `I`; candidate: `K`
- Candidate-only successes: 2
- Baseline-only successes: 0
- Exact paired p-value: 0.5
- The exact p-value is a two-sided McNemar/binomial test over discordant task pairs.

| Task type | Baseline only | Candidate only | Both succeed | Both fail | Success delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | 0 | 0 | 16 | 2 | +0 |
| pick_and_place_simple | 0 | 0 | 21 | 3 | +0 |
| pick_clean_then_place_in_recep | 0 | 1 | 28 | 2 | +1 |
| pick_cool_then_place_in_recep | 0 | 0 | 19 | 2 | +0 |
| pick_heat_then_place_in_recep | 0 | 0 | 23 | 0 | +0 |
| pick_two_obj_and_place | 0 | 1 | 7 | 9 | +1 |

## Per-task results

### Prompt I by task type

| Task type | Success | Rate | Steps |
| --- | ---: | ---: | ---: |
| look_at_obj_in_light | 16/18 | 88.9% | 497 |
| pick_and_place_simple | 21/24 | 87.5% | 381 |
| pick_clean_then_place_in_recep | 28/31 | 90.3% | 472 |
| pick_cool_then_place_in_recep | 19/21 | 90.5% | 300 |
| pick_heat_then_place_in_recep | 23/23 | 100.0% | 281 |
| pick_two_obj_and_place | 7/17 | 41.2% | 420 |

### Prompt I

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | False | 30 | 1 | 24 |
| look_at_obj_in_light | True | 28 | 0 | 26 |
| look_at_obj_in_light | True | 29 | 0 | 25 |
| look_at_obj_in_light | True | 28 | 1 | 26 |
| look_at_obj_in_light | True | 27 | 0 | 26 |
| look_at_obj_in_light | True | 27 | 1 | 25 |
| look_at_obj_in_light | True | 27 | 1 | 25 |
| look_at_obj_in_light | True | 28 | 1 | 26 |
| look_at_obj_in_light | False | 30 | 1 | 25 |
| look_at_obj_in_light | True | 26 | 0 | 25 |
| look_at_obj_in_light | True | 26 | 0 | 25 |
| look_at_obj_in_light | True | 30 | 1 | 26 |
| look_at_obj_in_light | True | 30 | 1 | 26 |
| look_at_obj_in_light | True | 26 | 0 | 25 |
| look_at_obj_in_light | True | 25 | 0 | 24 |
| look_at_obj_in_light | True | 27 | 0 | 26 |
| look_at_obj_in_light | True | 27 | 1 | 25 |
| look_at_obj_in_light | True | 26 | 0 | 25 |
| pick_and_place_simple | True | 21 | 0 | 20 |
| pick_and_place_simple | True | 12 | 0 | 11 |
| pick_and_place_simple | True | 12 | 0 | 11 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 27 | 0 | 26 |
| pick_and_place_simple | False | 30 | 0 | 4 |
| pick_and_place_simple | True | 6 | 0 | 5 |
| pick_and_place_simple | False | 30 | 0 | 30 |
| pick_and_place_simple | True | 14 | 0 | 13 |
| pick_and_place_simple | True | 6 | 0 | 5 |
| pick_and_place_simple | True | 19 | 0 | 18 |
| pick_and_place_simple | False | 30 | 0 | 4 |
| pick_and_place_simple | True | 27 | 0 | 26 |
| pick_and_place_simple | True | 7 | 0 | 7 |
| pick_and_place_simple | True | 7 | 0 | 6 |
| pick_and_place_simple | True | 7 | 0 | 6 |
| pick_and_place_simple | True | 30 | 0 | 29 |
| pick_and_place_simple | True | 11 | 0 | 10 |
| pick_and_place_simple | True | 23 | 0 | 22 |
| pick_and_place_simple | True | 11 | 0 | 10 |
| pick_and_place_simple | True | 10 | 0 | 9 |
| pick_and_place_simple | True | 29 | 0 | 28 |
| pick_clean_then_place_in_recep | True | 29 | 0 | 27 |
| pick_clean_then_place_in_recep | True | 6 | 0 | 5 |
| pick_clean_then_place_in_recep | True | 23 | 0 | 21 |
| pick_clean_then_place_in_recep | True | 20 | 0 | 18 |
| pick_clean_then_place_in_recep | True | 16 | 0 | 14 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 8 |
| pick_clean_then_place_in_recep | True | 29 | 0 | 27 |
| pick_clean_then_place_in_recep | True | 10 | 0 | 9 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 8 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 8 |
| pick_clean_then_place_in_recep | True | 29 | 0 | 27 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 7 | 0 | 6 |
| pick_clean_then_place_in_recep | True | 7 | 0 | 6 |
| pick_clean_then_place_in_recep | True | 13 | 0 | 11 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 12 | 0 | 10 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 29 | 0 | 27 |
| pick_clean_then_place_in_recep | True | 29 | 0 | 27 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 8 |
| pick_cool_then_place_in_recep | True | 29 | 0 | 27 |
| pick_cool_then_place_in_recep | True | 29 | 0 | 27 |
| pick_cool_then_place_in_recep | True | 29 | 0 | 27 |
| pick_cool_then_place_in_recep | True | 10 | 0 | 9 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 8 |
| pick_cool_then_place_in_recep | True | 10 | 0 | 9 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 7 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 7 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 7 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 7 |
| pick_cool_then_place_in_recep | True | 6 | 0 | 5 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 7 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | True | 8 | 0 | 6 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 8 |
| pick_cool_then_place_in_recep | True | 11 | 0 | 10 |
| pick_cool_then_place_in_recep | True | 11 | 0 | 10 |
| pick_cool_then_place_in_recep | True | 14 | 0 | 13 |
| pick_cool_then_place_in_recep | True | 11 | 0 | 10 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 13 | 0 | 12 |
| pick_heat_then_place_in_recep | True | 10 | 0 | 9 |
| pick_heat_then_place_in_recep | True | 7 | 0 | 6 |
| pick_heat_then_place_in_recep | True | 9 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 9 | 0 | 9 |
| pick_heat_then_place_in_recep | True | 13 | 0 | 12 |
| pick_heat_then_place_in_recep | True | 17 | 0 | 15 |
| pick_heat_then_place_in_recep | True | 17 | 0 | 15 |
| pick_heat_then_place_in_recep | True | 12 | 0 | 11 |
| pick_heat_then_place_in_recep | True | 29 | 0 | 27 |
| pick_heat_then_place_in_recep | True | 15 | 0 | 13 |
| pick_heat_then_place_in_recep | True | 8 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 7 | 0 | 6 |
| pick_heat_then_place_in_recep | True | 23 | 0 | 21 |
| pick_heat_then_place_in_recep | True | 6 | 0 | 6 |
| pick_heat_then_place_in_recep | True | 6 | 0 | 5 |
| pick_heat_then_place_in_recep | True | 6 | 0 | 5 |
| pick_heat_then_place_in_recep | True | 12 | 0 | 11 |
| pick_heat_then_place_in_recep | True | 8 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 8 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 8 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 29 | 0 | 27 |
| pick_heat_then_place_in_recep | True | 9 | 0 | 9 |
| pick_two_obj_and_place | True | 21 | 0 | 19 |
| pick_two_obj_and_place | True | 16 | 0 | 15 |
| pick_two_obj_and_place | False | 30 | 0 | 27 |
| pick_two_obj_and_place | True | 18 | 0 | 16 |
| pick_two_obj_and_place | True | 18 | 0 | 16 |
| pick_two_obj_and_place | False | 30 | 0 | 4 |
| pick_two_obj_and_place | False | 30 | 0 | 6 |
| pick_two_obj_and_place | False | 30 | 0 | 4 |
| pick_two_obj_and_place | False | 30 | 0 | 29 |
| pick_two_obj_and_place | False | 30 | 0 | 29 |
| pick_two_obj_and_place | False | 30 | 0 | 29 |
| pick_two_obj_and_place | True | 13 | 0 | 11 |
| pick_two_obj_and_place | False | 30 | 0 | 25 |
| pick_two_obj_and_place | False | 30 | 0 | 22 |
| pick_two_obj_and_place | True | 20 | 0 | 19 |
| pick_two_obj_and_place | False | 30 | 0 | 24 |
| pick_two_obj_and_place | True | 14 | 0 | 12 |

### Prompt K by task type

| Task type | Success | Rate | Steps |
| --- | ---: | ---: | ---: |
| look_at_obj_in_light | 16/18 | 88.9% | 497 |
| pick_and_place_simple | 21/24 | 87.5% | 381 |
| pick_clean_then_place_in_recep | 29/31 | 93.5% | 452 |
| pick_cool_then_place_in_recep | 19/21 | 90.5% | 300 |
| pick_heat_then_place_in_recep | 23/23 | 100.0% | 281 |
| pick_two_obj_and_place | 8/17 | 47.1% | 422 |

### Prompt K

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | False | 30 | 1 | 24 |
| look_at_obj_in_light | True | 28 | 0 | 26 |
| look_at_obj_in_light | True | 29 | 0 | 25 |
| look_at_obj_in_light | True | 28 | 1 | 26 |
| look_at_obj_in_light | True | 27 | 0 | 26 |
| look_at_obj_in_light | True | 27 | 1 | 25 |
| look_at_obj_in_light | True | 27 | 1 | 25 |
| look_at_obj_in_light | True | 28 | 1 | 26 |
| look_at_obj_in_light | False | 30 | 1 | 25 |
| look_at_obj_in_light | True | 26 | 0 | 25 |
| look_at_obj_in_light | True | 26 | 0 | 25 |
| look_at_obj_in_light | True | 30 | 1 | 26 |
| look_at_obj_in_light | True | 30 | 1 | 26 |
| look_at_obj_in_light | True | 26 | 0 | 25 |
| look_at_obj_in_light | True | 25 | 0 | 24 |
| look_at_obj_in_light | True | 27 | 0 | 26 |
| look_at_obj_in_light | True | 27 | 1 | 25 |
| look_at_obj_in_light | True | 26 | 0 | 25 |
| pick_and_place_simple | True | 21 | 0 | 20 |
| pick_and_place_simple | True | 12 | 0 | 11 |
| pick_and_place_simple | True | 12 | 0 | 11 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 27 | 0 | 26 |
| pick_and_place_simple | False | 30 | 0 | 4 |
| pick_and_place_simple | True | 6 | 0 | 5 |
| pick_and_place_simple | False | 30 | 0 | 30 |
| pick_and_place_simple | True | 14 | 0 | 13 |
| pick_and_place_simple | True | 6 | 0 | 5 |
| pick_and_place_simple | True | 19 | 0 | 18 |
| pick_and_place_simple | False | 30 | 0 | 4 |
| pick_and_place_simple | True | 27 | 0 | 26 |
| pick_and_place_simple | True | 7 | 0 | 7 |
| pick_and_place_simple | True | 7 | 0 | 6 |
| pick_and_place_simple | True | 7 | 0 | 6 |
| pick_and_place_simple | True | 30 | 0 | 29 |
| pick_and_place_simple | True | 11 | 0 | 10 |
| pick_and_place_simple | True | 23 | 0 | 22 |
| pick_and_place_simple | True | 11 | 0 | 10 |
| pick_and_place_simple | True | 10 | 0 | 9 |
| pick_and_place_simple | True | 29 | 0 | 28 |
| pick_clean_then_place_in_recep | True | 29 | 0 | 27 |
| pick_clean_then_place_in_recep | True | 6 | 0 | 5 |
| pick_clean_then_place_in_recep | True | 23 | 0 | 21 |
| pick_clean_then_place_in_recep | True | 20 | 0 | 18 |
| pick_clean_then_place_in_recep | True | 16 | 0 | 14 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 8 |
| pick_clean_then_place_in_recep | True | 29 | 0 | 27 |
| pick_clean_then_place_in_recep | True | 10 | 0 | 9 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 8 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 8 |
| pick_clean_then_place_in_recep | True | 29 | 0 | 27 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 7 | 0 | 6 |
| pick_clean_then_place_in_recep | True | 7 | 0 | 6 |
| pick_clean_then_place_in_recep | True | 13 | 0 | 11 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 12 | 0 | 10 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 29 | 0 | 27 |
| pick_clean_then_place_in_recep | True | 29 | 0 | 27 |
| pick_clean_then_place_in_recep | True | 10 | 0 | 9 |
| pick_cool_then_place_in_recep | True | 29 | 0 | 27 |
| pick_cool_then_place_in_recep | True | 29 | 0 | 27 |
| pick_cool_then_place_in_recep | True | 29 | 0 | 27 |
| pick_cool_then_place_in_recep | True | 10 | 0 | 9 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 8 |
| pick_cool_then_place_in_recep | True | 10 | 0 | 9 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 7 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 7 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 7 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 7 |
| pick_cool_then_place_in_recep | True | 6 | 0 | 5 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 7 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | True | 8 | 0 | 6 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 8 |
| pick_cool_then_place_in_recep | True | 11 | 0 | 10 |
| pick_cool_then_place_in_recep | True | 11 | 0 | 10 |
| pick_cool_then_place_in_recep | True | 14 | 0 | 13 |
| pick_cool_then_place_in_recep | True | 11 | 0 | 10 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 13 | 0 | 12 |
| pick_heat_then_place_in_recep | True | 10 | 0 | 9 |
| pick_heat_then_place_in_recep | True | 7 | 0 | 6 |
| pick_heat_then_place_in_recep | True | 9 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 9 | 0 | 9 |
| pick_heat_then_place_in_recep | True | 13 | 0 | 12 |
| pick_heat_then_place_in_recep | True | 17 | 0 | 15 |
| pick_heat_then_place_in_recep | True | 17 | 0 | 15 |
| pick_heat_then_place_in_recep | True | 12 | 0 | 11 |
| pick_heat_then_place_in_recep | True | 29 | 0 | 27 |
| pick_heat_then_place_in_recep | True | 15 | 0 | 13 |
| pick_heat_then_place_in_recep | True | 8 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 7 | 0 | 6 |
| pick_heat_then_place_in_recep | True | 23 | 0 | 21 |
| pick_heat_then_place_in_recep | True | 6 | 0 | 6 |
| pick_heat_then_place_in_recep | True | 6 | 0 | 5 |
| pick_heat_then_place_in_recep | True | 6 | 0 | 5 |
| pick_heat_then_place_in_recep | True | 12 | 0 | 11 |
| pick_heat_then_place_in_recep | True | 8 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 8 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 8 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 29 | 0 | 27 |
| pick_heat_then_place_in_recep | True | 9 | 0 | 9 |
| pick_two_obj_and_place | True | 21 | 0 | 19 |
| pick_two_obj_and_place | True | 17 | 0 | 15 |
| pick_two_obj_and_place | False | 30 | 0 | 26 |
| pick_two_obj_and_place | True | 18 | 0 | 16 |
| pick_two_obj_and_place | True | 18 | 0 | 16 |
| pick_two_obj_and_place | False | 30 | 0 | 4 |
| pick_two_obj_and_place | True | 30 | 0 | 28 |
| pick_two_obj_and_place | False | 30 | 0 | 4 |
| pick_two_obj_and_place | False | 30 | 0 | 29 |
| pick_two_obj_and_place | False | 30 | 0 | 29 |
| pick_two_obj_and_place | False | 30 | 0 | 29 |
| pick_two_obj_and_place | True | 13 | 0 | 11 |
| pick_two_obj_and_place | False | 30 | 0 | 20 |
| pick_two_obj_and_place | False | 30 | 0 | 22 |
| pick_two_obj_and_place | True | 21 | 0 | 19 |
| pick_two_obj_and_place | False | 30 | 0 | 24 |
| pick_two_obj_and_place | True | 14 | 0 | 12 |
