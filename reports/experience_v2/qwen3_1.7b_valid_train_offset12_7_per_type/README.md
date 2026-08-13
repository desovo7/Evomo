# Qwen3-1.7B ALFWorld multi-task prompt comparison

- Split: `valid_train`
- Tasks per prompt: 42
- Samples per task type: 7
- Stable task offset: 12
- Integrity audit: [`audit.json`](audit.json)
- Prompt H experience: `exp-v2-from-g-failures`
- Prompt I experience: `exp-v3-from-h-offset2-failures`

| Prompt | Success | Parsed actions | Repaired | Experience overrides | True fallback | Repeats | Unchanged obs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H | 19/42 (45.2%) | 830/981 | 21 | 548 | 58 | 36 | 36 |
| I | 28/42 (66.7%) | 658/760 | 0 | 664 | 21 | 11 | 11 |

## Paired success analysis

- Baseline: `H`; candidate: `I`
- Candidate-only successes: 11
- Baseline-only successes: 2
- Exact paired p-value: 0.0224609
- The exact p-value is a two-sided McNemar/binomial test over discordant task pairs.

| Task type | Baseline only | Candidate only | Both succeed | Both fail | Success delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | 1 | 0 | 1 | 5 | -1 |
| pick_and_place_simple | 0 | 3 | 2 | 2 | +3 |
| pick_clean_then_place_in_recep | 1 | 1 | 3 | 2 | +0 |
| pick_cool_then_place_in_recep | 0 | 2 | 3 | 2 | +2 |
| pick_heat_then_place_in_recep | 0 | 0 | 6 | 1 | +0 |
| pick_two_obj_and_place | 0 | 5 | 2 | 0 | +5 |

## Per-task results

### Prompt H by task type

| Task type | Success | Rate | Steps |
| --- | ---: | ---: | ---: |
| look_at_obj_in_light | 2/7 | 28.6% | 186 |
| pick_and_place_simple | 2/7 | 28.6% | 171 |
| pick_clean_then_place_in_recep | 4/7 | 57.1% | 176 |
| pick_cool_then_place_in_recep | 3/7 | 42.9% | 171 |
| pick_heat_then_place_in_recep | 6/7 | 85.7% | 90 |
| pick_two_obj_and_place | 2/7 | 28.6% | 187 |

### Prompt H

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | False | 30 | 0 | 30 |
| look_at_obj_in_light | False | 30 | 0 | 30 |
| look_at_obj_in_light | False | 30 | 2 | 20 |
| look_at_obj_in_light | True | 14 | 2 | 11 |
| look_at_obj_in_light | False | 30 | 2 | 25 |
| look_at_obj_in_light | False | 30 | 0 | 30 |
| look_at_obj_in_light | True | 22 | 0 | 21 |
| pick_and_place_simple | False | 30 | 3 | 23 |
| pick_and_place_simple | False | 30 | 6 | 6 |
| pick_and_place_simple | True | 7 | 0 | 7 |
| pick_and_place_simple | False | 30 | 6 | 13 |
| pick_and_place_simple | True | 14 | 0 | 8 |
| pick_and_place_simple | False | 30 | 5 | 15 |
| pick_and_place_simple | False | 30 | 1 | 11 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | True | 28 | 0 | 27 |
| pick_clean_then_place_in_recep | True | 23 | 0 | 22 |
| pick_clean_then_place_in_recep | True | 6 | 0 | 5 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 12 |
| pick_clean_then_place_in_recep | True | 29 | 0 | 27 |
| pick_cool_then_place_in_recep | True | 27 | 0 | 26 |
| pick_cool_then_place_in_recep | True | 8 | 0 | 6 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | True | 16 | 0 | 15 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_heat_then_place_in_recep | True | 14 | 0 | 13 |
| pick_heat_then_place_in_recep | False | 30 | 0 | 29 |
| pick_heat_then_place_in_recep | True | 7 | 0 | 7 |
| pick_heat_then_place_in_recep | True | 11 | 0 | 10 |
| pick_heat_then_place_in_recep | True | 7 | 0 | 6 |
| pick_heat_then_place_in_recep | True | 7 | 0 | 6 |
| pick_heat_then_place_in_recep | True | 14 | 0 | 13 |
| pick_two_obj_and_place | False | 30 | 1 | 12 |
| pick_two_obj_and_place | False | 30 | 0 | 16 |
| pick_two_obj_and_place | False | 30 | 2 | 16 |
| pick_two_obj_and_place | True | 18 | 3 | 10 |
| pick_two_obj_and_place | False | 30 | 0 | 17 |
| pick_two_obj_and_place | False | 30 | 1 | 16 |
| pick_two_obj_and_place | True | 19 | 2 | 11 |

### Prompt I by task type

| Task type | Success | Rate | Steps |
| --- | ---: | ---: | ---: |
| look_at_obj_in_light | 1/7 | 14.3% | 198 |
| pick_and_place_simple | 5/7 | 71.4% | 98 |
| pick_clean_then_place_in_recep | 4/7 | 57.1% | 135 |
| pick_cool_then_place_in_recep | 5/7 | 71.4% | 126 |
| pick_heat_then_place_in_recep | 6/7 | 85.7% | 90 |
| pick_two_obj_and_place | 7/7 | 100.0% | 113 |

### Prompt I

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | False | 30 | 0 | 30 |
| look_at_obj_in_light | False | 30 | 0 | 30 |
| look_at_obj_in_light | False | 30 | 0 | 22 |
| look_at_obj_in_light | True | 18 | 4 | 13 |
| look_at_obj_in_light | False | 30 | 1 | 26 |
| look_at_obj_in_light | False | 30 | 0 | 30 |
| look_at_obj_in_light | False | 30 | 6 | 22 |
| pick_and_place_simple | False | 30 | 0 | 30 |
| pick_and_place_simple | True | 10 | 0 | 9 |
| pick_and_place_simple | True | 7 | 0 | 6 |
| pick_and_place_simple | False | 30 | 0 | 30 |
| pick_and_place_simple | True | 5 | 0 | 4 |
| pick_and_place_simple | True | 5 | 0 | 4 |
| pick_and_place_simple | True | 11 | 0 | 10 |
| pick_clean_then_place_in_recep | True | 20 | 0 | 18 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 8 |
| pick_clean_then_place_in_recep | True | 6 | 0 | 5 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 9 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 10 |
| pick_clean_then_place_in_recep | True | 10 | 0 | 9 |
| pick_cool_then_place_in_recep | True | 8 | 0 | 7 |
| pick_cool_then_place_in_recep | True | 8 | 0 | 6 |
| pick_cool_then_place_in_recep | True | 20 | 0 | 18 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | True | 11 | 0 | 9 |
| pick_cool_then_place_in_recep | True | 19 | 0 | 17 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_heat_then_place_in_recep | True | 14 | 0 | 13 |
| pick_heat_then_place_in_recep | False | 30 | 0 | 29 |
| pick_heat_then_place_in_recep | True | 7 | 0 | 7 |
| pick_heat_then_place_in_recep | True | 11 | 0 | 10 |
| pick_heat_then_place_in_recep | True | 7 | 0 | 6 |
| pick_heat_then_place_in_recep | True | 7 | 0 | 6 |
| pick_heat_then_place_in_recep | True | 14 | 0 | 13 |
| pick_two_obj_and_place | True | 13 | 0 | 11 |
| pick_two_obj_and_place | True | 16 | 0 | 14 |
| pick_two_obj_and_place | True | 18 | 0 | 16 |
| pick_two_obj_and_place | True | 10 | 0 | 8 |
| pick_two_obj_and_place | True | 23 | 0 | 21 |
| pick_two_obj_and_place | True | 17 | 0 | 15 |
| pick_two_obj_and_place | True | 16 | 0 | 14 |
