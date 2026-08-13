# Qwen3-1.7B ALFWorld multi-task prompt comparison

- Split: `valid_train`
- Tasks per prompt: 60
- Samples per task type: 10
- Stable task offset: 2
- Integrity audit: [`audit.json`](audit.json)

| Prompt | Success | Parsed actions | Repaired | Experience overrides | True fallback | Repeats | Unchanged obs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| F | 15/60 (25.0%) | 1131/1572 | 22 | 0 | 419 | 315 | 315 |
| H | 30/60 (50.0%) | 1148/1340 | 12 | 727 | 90 | 58 | 58 |

## Paired success analysis

- Baseline: `F`; candidate: `H`
- Candidate-only successes: 18
- Baseline-only successes: 3
- Exact paired p-value: 0.00148964
- The exact p-value is a two-sided McNemar/binomial test over discordant task pairs.

| Task type | Baseline only | Candidate only | Both succeed | Both fail | Success delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | 2 | 4 | 1 | 3 | +2 |
| pick_and_place_simple | 0 | 0 | 4 | 6 | +0 |
| pick_clean_then_place_in_recep | 0 | 3 | 2 | 5 | +3 |
| pick_cool_then_place_in_recep | 1 | 3 | 2 | 4 | +2 |
| pick_heat_then_place_in_recep | 0 | 8 | 1 | 1 | +8 |
| pick_two_obj_and_place | 0 | 0 | 2 | 8 | +0 |

## Per-task results

### Prompt F by task type

| Task type | Success | Rate | Steps |
| --- | ---: | ---: | ---: |
| look_at_obj_in_light | 3/10 | 30.0% | 245 |
| pick_and_place_simple | 4/10 | 40.0% | 217 |
| pick_clean_then_place_in_recep | 2/10 | 20.0% | 266 |
| pick_cool_then_place_in_recep | 3/10 | 30.0% | 286 |
| pick_heat_then_place_in_recep | 1/10 | 10.0% | 277 |
| pick_two_obj_and_place | 2/10 | 20.0% | 281 |

### Prompt F

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | False | 30 | 17 | 5 |
| look_at_obj_in_light | False | 30 | 7 | 9 |
| look_at_obj_in_light | True | 4 | 0 | 4 |
| look_at_obj_in_light | True | 28 | 6 | 15 |
| look_at_obj_in_light | True | 3 | 0 | 3 |
| look_at_obj_in_light | False | 30 | 5 | 15 |
| look_at_obj_in_light | False | 30 | 27 | 3 |
| look_at_obj_in_light | False | 30 | 8 | 13 |
| look_at_obj_in_light | False | 30 | 28 | 2 |
| look_at_obj_in_light | False | 30 | 4 | 18 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 15 | 2 | 11 |
| pick_and_place_simple | False | 30 | 0 | 13 |
| pick_and_place_simple | False | 30 | 1 | 15 |
| pick_and_place_simple | True | 11 | 3 | 7 |
| pick_and_place_simple | False | 30 | 5 | 11 |
| pick_and_place_simple | False | 30 | 9 | 10 |
| pick_and_place_simple | False | 30 | 1 | 11 |
| pick_and_place_simple | True | 7 | 0 | 6 |
| pick_and_place_simple | False | 30 | 0 | 17 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 17 |
| pick_clean_then_place_in_recep | False | 30 | 2 | 15 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 12 |
| pick_clean_then_place_in_recep | False | 30 | 4 | 12 |
| pick_clean_then_place_in_recep | True | 17 | 1 | 14 |
| pick_clean_then_place_in_recep | False | 30 | 8 | 16 |
| pick_clean_then_place_in_recep | False | 30 | 2 | 20 |
| pick_clean_then_place_in_recep | False | 30 | 17 | 4 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 8 |
| pick_clean_then_place_in_recep | False | 30 | 28 | 2 |
| pick_cool_then_place_in_recep | False | 30 | 1 | 15 |
| pick_cool_then_place_in_recep | False | 30 | 2 | 15 |
| pick_cool_then_place_in_recep | False | 30 | 2 | 17 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 13 |
| pick_cool_then_place_in_recep | True | 21 | 0 | 14 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 20 |
| pick_cool_then_place_in_recep | False | 30 | 1 | 18 |
| pick_cool_then_place_in_recep | True | 28 | 1 | 18 |
| pick_cool_then_place_in_recep | True | 27 | 5 | 13 |
| pick_cool_then_place_in_recep | False | 30 | 18 | 10 |
| pick_heat_then_place_in_recep | False | 30 | 1 | 22 |
| pick_heat_then_place_in_recep | False | 30 | 5 | 14 |
| pick_heat_then_place_in_recep | False | 30 | 7 | 11 |
| pick_heat_then_place_in_recep | True | 7 | 0 | 7 |
| pick_heat_then_place_in_recep | False | 30 | 26 | 4 |
| pick_heat_then_place_in_recep | False | 30 | 5 | 18 |
| pick_heat_then_place_in_recep | False | 30 | 1 | 14 |
| pick_heat_then_place_in_recep | False | 30 | 7 | 13 |
| pick_heat_then_place_in_recep | False | 30 | 28 | 2 |
| pick_heat_then_place_in_recep | False | 30 | 6 | 14 |
| pick_two_obj_and_place | False | 30 | 1 | 11 |
| pick_two_obj_and_place | False | 30 | 0 | 15 |
| pick_two_obj_and_place | False | 30 | 5 | 15 |
| pick_two_obj_and_place | False | 30 | 3 | 9 |
| pick_two_obj_and_place | False | 30 | 0 | 11 |
| pick_two_obj_and_place | False | 30 | 2 | 10 |
| pick_two_obj_and_place | True | 21 | 1 | 16 |
| pick_two_obj_and_place | False | 30 | 0 | 15 |
| pick_two_obj_and_place | True | 20 | 1 | 13 |
| pick_two_obj_and_place | False | 30 | 1 | 17 |

### Prompt H by task type

| Task type | Success | Rate | Steps |
| --- | ---: | ---: | ---: |
| look_at_obj_in_light | 5/10 | 50.0% | 250 |
| pick_and_place_simple | 4/10 | 40.0% | 217 |
| pick_clean_then_place_in_recep | 5/10 | 50.0% | 228 |
| pick_cool_then_place_in_recep | 5/10 | 50.0% | 223 |
| pick_heat_then_place_in_recep | 9/10 | 90.0% | 141 |
| pick_two_obj_and_place | 2/10 | 20.0% | 281 |

### Prompt H

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | True | 12 | 0 | 12 |
| look_at_obj_in_light | True | 19 | 0 | 18 |
| look_at_obj_in_light | False | 30 | 10 | 14 |
| look_at_obj_in_light | True | 25 | 6 | 18 |
| look_at_obj_in_light | False | 30 | 0 | 30 |
| look_at_obj_in_light | False | 30 | 0 | 29 |
| look_at_obj_in_light | True | 19 | 1 | 17 |
| look_at_obj_in_light | False | 30 | 1 | 27 |
| look_at_obj_in_light | True | 25 | 1 | 23 |
| look_at_obj_in_light | False | 30 | 0 | 30 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 15 | 2 | 11 |
| pick_and_place_simple | False | 30 | 0 | 13 |
| pick_and_place_simple | False | 30 | 1 | 15 |
| pick_and_place_simple | True | 11 | 3 | 7 |
| pick_and_place_simple | False | 30 | 5 | 11 |
| pick_and_place_simple | False | 30 | 9 | 10 |
| pick_and_place_simple | False | 30 | 1 | 11 |
| pick_and_place_simple | True | 7 | 0 | 6 |
| pick_and_place_simple | False | 30 | 0 | 17 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 6 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 8 |
| pick_clean_then_place_in_recep | True | 11 | 0 | 10 |
| pick_clean_then_place_in_recep | True | 6 | 0 | 6 |
| pick_clean_then_place_in_recep | True | 20 | 0 | 18 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 30 |
| pick_clean_then_place_in_recep | True | 16 | 0 | 15 |
| pick_clean_then_place_in_recep | True | 25 | 0 | 24 |
| pick_clean_then_place_in_recep | False | 30 | 4 | 26 |
| pick_cool_then_place_in_recep | True | 7 | 0 | 7 |
| pick_cool_then_place_in_recep | True | 19 | 0 | 17 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 28 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_cool_then_place_in_recep | True | 17 | 0 | 16 |
| pick_cool_then_place_in_recep | True | 20 | 0 | 18 |
| pick_cool_then_place_in_recep | True | 10 | 0 | 8 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 30 |
| pick_heat_then_place_in_recep | True | 14 | 0 | 13 |
| pick_heat_then_place_in_recep | True | 15 | 0 | 14 |
| pick_heat_then_place_in_recep | True | 13 | 0 | 12 |
| pick_heat_then_place_in_recep | True | 7 | 0 | 7 |
| pick_heat_then_place_in_recep | True | 13 | 0 | 12 |
| pick_heat_then_place_in_recep | True | 8 | 0 | 7 |
| pick_heat_then_place_in_recep | False | 30 | 0 | 30 |
| pick_heat_then_place_in_recep | True | 17 | 0 | 15 |
| pick_heat_then_place_in_recep | True | 10 | 0 | 9 |
| pick_heat_then_place_in_recep | True | 14 | 0 | 13 |
| pick_two_obj_and_place | False | 30 | 1 | 11 |
| pick_two_obj_and_place | False | 30 | 0 | 15 |
| pick_two_obj_and_place | False | 30 | 5 | 15 |
| pick_two_obj_and_place | False | 30 | 3 | 9 |
| pick_two_obj_and_place | False | 30 | 0 | 11 |
| pick_two_obj_and_place | False | 30 | 2 | 10 |
| pick_two_obj_and_place | True | 21 | 1 | 16 |
| pick_two_obj_and_place | False | 30 | 0 | 15 |
| pick_two_obj_and_place | True | 20 | 1 | 13 |
| pick_two_obj_and_place | False | 30 | 1 | 17 |
