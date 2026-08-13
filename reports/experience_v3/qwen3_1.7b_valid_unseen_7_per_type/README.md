# Qwen3-1.7B ALFWorld multi-task prompt comparison

- Split: `valid_unseen`
- Tasks per prompt: 42
- Samples per task type: 7
- Stable task offset: 0
- Integrity audit: [`audit.json`](audit.json)
- Prompt H experience: `exp-v2-from-g-failures`
- Prompt I experience: `exp-v3-from-h-offset2-failures`
- Prompt J experience: `champion-v1-from-offset12-promotion`

| Prompt | Success | Parsed actions | Repaired | Experience overrides | True fallback | Repeats | Unchanged obs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H | 31/42 (73.8%) | 616/757 | 21 | 413 | 46 | 23 | 23 |
| I | 38/42 (90.5%) | 658/756 | 0 | 668 | 11 | 4 | 4 |
| J | 35/42 (83.3%) | 629/730 | 0 | 636 | 12 | 14 | 14 |

## All pairwise success analyses

| Baseline | Candidate | Baseline only | Candidate only | Net delta | Exact p-value |
| --- | --- | ---: | ---: | ---: | ---: |
| H | I | 1 | 8 | +7 | 0.0390625 |
| H | J | 0 | 4 | +4 | 0.125 |
| I | J | 4 | 1 | -3 | 0.375 |

## Per-task results

### Prompt H by task type

| Task type | Success | Rate | Steps |
| --- | ---: | ---: | ---: |
| look_at_obj_in_light | 3/7 | 42.9% | 204 |
| pick_and_place_simple | 6/7 | 85.7% | 81 |
| pick_clean_then_place_in_recep | 7/7 | 100.0% | 76 |
| pick_cool_then_place_in_recep | 7/7 | 100.0% | 125 |
| pick_heat_then_place_in_recep | 7/7 | 100.0% | 78 |
| pick_two_obj_and_place | 1/7 | 14.3% | 193 |

### Prompt H

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | True | 30 | 4 | 25 |
| look_at_obj_in_light | False | 30 | 2 | 25 |
| look_at_obj_in_light | False | 30 | 4 | 24 |
| look_at_obj_in_light | True | 28 | 1 | 26 |
| look_at_obj_in_light | False | 30 | 1 | 28 |
| look_at_obj_in_light | True | 26 | 0 | 25 |
| look_at_obj_in_light | False | 30 | 2 | 26 |
| pick_and_place_simple | True | 10 | 0 | 8 |
| pick_and_place_simple | True | 11 | 0 | 10 |
| pick_and_place_simple | True | 6 | 0 | 5 |
| pick_and_place_simple | True | 16 | 4 | 7 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | False | 30 | 0 | 14 |
| pick_clean_then_place_in_recep | True | 19 | 0 | 17 |
| pick_clean_then_place_in_recep | True | 6 | 0 | 5 |
| pick_clean_then_place_in_recep | True | 11 | 0 | 9 |
| pick_clean_then_place_in_recep | True | 14 | 0 | 12 |
| pick_clean_then_place_in_recep | True | 10 | 0 | 8 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 7 |
| pick_cool_then_place_in_recep | True | 20 | 0 | 18 |
| pick_cool_then_place_in_recep | True | 20 | 0 | 18 |
| pick_cool_then_place_in_recep | True | 20 | 0 | 18 |
| pick_cool_then_place_in_recep | True | 18 | 0 | 17 |
| pick_cool_then_place_in_recep | True | 17 | 0 | 16 |
| pick_cool_then_place_in_recep | True | 18 | 0 | 17 |
| pick_cool_then_place_in_recep | True | 12 | 0 | 10 |
| pick_heat_then_place_in_recep | True | 13 | 0 | 12 |
| pick_heat_then_place_in_recep | True | 10 | 0 | 9 |
| pick_heat_then_place_in_recep | True | 7 | 0 | 6 |
| pick_heat_then_place_in_recep | True | 9 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 9 | 0 | 9 |
| pick_heat_then_place_in_recep | True | 13 | 0 | 12 |
| pick_heat_then_place_in_recep | True | 17 | 0 | 15 |
| pick_two_obj_and_place | False | 30 | 1 | 18 |
| pick_two_obj_and_place | True | 13 | 0 | 11 |
| pick_two_obj_and_place | False | 30 | 1 | 20 |
| pick_two_obj_and_place | False | 30 | 3 | 14 |
| pick_two_obj_and_place | False | 30 | 0 | 14 |
| pick_two_obj_and_place | False | 30 | 0 | 19 |
| pick_two_obj_and_place | False | 30 | 0 | 18 |

### Prompt I by task type

| Task type | Success | Rate | Steps |
| --- | ---: | ---: | ---: |
| look_at_obj_in_light | 6/7 | 85.7% | 196 |
| pick_and_place_simple | 7/7 | 100.0% | 84 |
| pick_clean_then_place_in_recep | 7/7 | 100.0% | 110 |
| pick_cool_then_place_in_recep | 7/7 | 100.0% | 125 |
| pick_heat_then_place_in_recep | 7/7 | 100.0% | 78 |
| pick_two_obj_and_place | 4/7 | 57.1% | 163 |

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
| pick_and_place_simple | True | 21 | 0 | 20 |
| pick_and_place_simple | True | 12 | 0 | 11 |
| pick_and_place_simple | True | 12 | 0 | 11 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 27 | 0 | 26 |
| pick_clean_then_place_in_recep | True | 29 | 0 | 27 |
| pick_clean_then_place_in_recep | True | 6 | 0 | 5 |
| pick_clean_then_place_in_recep | True | 23 | 0 | 21 |
| pick_clean_then_place_in_recep | True | 20 | 0 | 18 |
| pick_clean_then_place_in_recep | True | 16 | 0 | 14 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 7 |
| pick_cool_then_place_in_recep | True | 29 | 0 | 27 |
| pick_cool_then_place_in_recep | True | 29 | 0 | 27 |
| pick_cool_then_place_in_recep | True | 29 | 0 | 27 |
| pick_cool_then_place_in_recep | True | 10 | 0 | 9 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 8 |
| pick_cool_then_place_in_recep | True | 10 | 0 | 9 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 7 |
| pick_heat_then_place_in_recep | True | 13 | 0 | 12 |
| pick_heat_then_place_in_recep | True | 10 | 0 | 9 |
| pick_heat_then_place_in_recep | True | 7 | 0 | 6 |
| pick_heat_then_place_in_recep | True | 9 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 9 | 0 | 9 |
| pick_heat_then_place_in_recep | True | 13 | 0 | 12 |
| pick_heat_then_place_in_recep | True | 17 | 0 | 15 |
| pick_two_obj_and_place | True | 21 | 0 | 19 |
| pick_two_obj_and_place | True | 16 | 0 | 15 |
| pick_two_obj_and_place | False | 30 | 0 | 27 |
| pick_two_obj_and_place | True | 18 | 0 | 16 |
| pick_two_obj_and_place | True | 18 | 0 | 16 |
| pick_two_obj_and_place | False | 30 | 0 | 4 |
| pick_two_obj_and_place | False | 30 | 0 | 6 |

### Prompt J by task type

| Task type | Success | Rate | Steps |
| --- | ---: | ---: | ---: |
| look_at_obj_in_light | 3/7 | 42.9% | 204 |
| pick_and_place_simple | 7/7 | 100.0% | 84 |
| pick_clean_then_place_in_recep | 7/7 | 100.0% | 76 |
| pick_cool_then_place_in_recep | 7/7 | 100.0% | 125 |
| pick_heat_then_place_in_recep | 7/7 | 100.0% | 78 |
| pick_two_obj_and_place | 4/7 | 57.1% | 163 |

### Prompt J

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | True | 30 | 4 | 25 |
| look_at_obj_in_light | False | 30 | 2 | 25 |
| look_at_obj_in_light | False | 30 | 4 | 24 |
| look_at_obj_in_light | True | 28 | 1 | 26 |
| look_at_obj_in_light | False | 30 | 1 | 28 |
| look_at_obj_in_light | True | 26 | 0 | 25 |
| look_at_obj_in_light | False | 30 | 2 | 26 |
| pick_and_place_simple | True | 21 | 0 | 20 |
| pick_and_place_simple | True | 12 | 0 | 11 |
| pick_and_place_simple | True | 12 | 0 | 11 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 27 | 0 | 26 |
| pick_clean_then_place_in_recep | True | 19 | 0 | 17 |
| pick_clean_then_place_in_recep | True | 6 | 0 | 5 |
| pick_clean_then_place_in_recep | True | 11 | 0 | 9 |
| pick_clean_then_place_in_recep | True | 14 | 0 | 12 |
| pick_clean_then_place_in_recep | True | 10 | 0 | 8 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 7 |
| pick_clean_then_place_in_recep | True | 8 | 0 | 7 |
| pick_cool_then_place_in_recep | True | 29 | 0 | 27 |
| pick_cool_then_place_in_recep | True | 29 | 0 | 27 |
| pick_cool_then_place_in_recep | True | 29 | 0 | 27 |
| pick_cool_then_place_in_recep | True | 10 | 0 | 9 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 8 |
| pick_cool_then_place_in_recep | True | 10 | 0 | 9 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 7 |
| pick_heat_then_place_in_recep | True | 13 | 0 | 12 |
| pick_heat_then_place_in_recep | True | 10 | 0 | 9 |
| pick_heat_then_place_in_recep | True | 7 | 0 | 6 |
| pick_heat_then_place_in_recep | True | 9 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 9 | 0 | 9 |
| pick_heat_then_place_in_recep | True | 13 | 0 | 12 |
| pick_heat_then_place_in_recep | True | 17 | 0 | 15 |
| pick_two_obj_and_place | True | 21 | 0 | 19 |
| pick_two_obj_and_place | True | 16 | 0 | 15 |
| pick_two_obj_and_place | False | 30 | 0 | 27 |
| pick_two_obj_and_place | True | 18 | 0 | 16 |
| pick_two_obj_and_place | True | 18 | 0 | 16 |
| pick_two_obj_and_place | False | 30 | 0 | 4 |
| pick_two_obj_and_place | False | 30 | 0 | 6 |
