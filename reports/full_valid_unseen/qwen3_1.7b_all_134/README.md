# Qwen3-1.7B ALFWorld multi-task prompt comparison

- Split: `valid_unseen`
- Tasks per prompt: 134
- Task selection: all playable tasks
- Stable task offset: 0
- Integrity audit: [`audit.json`](audit.json)
- Prompt I experience: `exp-v3-from-h-offset2-failures`

| Prompt | Success | Parsed actions | Repaired | Experience overrides | True fallback | Repeats | Unchanged obs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| F | 32/134 (23.9%) | 2671/3489 | 87 | 0 | 731 | 491 | 491 |
| I | 114/134 (85.1%) | 2081/2351 | 1 | 2089 | 24 | 9 | 9 |

## Paired success analysis

- Baseline: `F`; candidate: `I`
- Candidate-only successes: 86
- Baseline-only successes: 4
- Exact paired p-value: 4.32455e-21
- The exact p-value is a two-sided McNemar/binomial test over discordant task pairs.

| Task type | Baseline only | Candidate only | Both succeed | Both fail | Success delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | 0 | 13 | 3 | 2 | +13 |
| pick_and_place_simple | 2 | 11 | 10 | 1 | +9 |
| pick_clean_then_place_in_recep | 0 | 21 | 7 | 3 | +21 |
| pick_cool_then_place_in_recep | 0 | 18 | 1 | 2 | +18 |
| pick_heat_then_place_in_recep | 0 | 18 | 5 | 0 | +18 |
| pick_two_obj_and_place | 2 | 5 | 2 | 8 | +3 |

## Per-task results

### Prompt F by task type

| Task type | Success | Rate | Steps |
| --- | ---: | ---: | ---: |
| look_at_obj_in_light | 3/18 | 16.7% | 460 |
| pick_and_place_simple | 12/24 | 50.0% | 471 |
| pick_clean_then_place_in_recep | 7/31 | 22.6% | 849 |
| pick_cool_then_place_in_recep | 1/21 | 4.8% | 621 |
| pick_heat_then_place_in_recep | 5/23 | 21.7% | 629 |
| pick_two_obj_and_place | 4/17 | 23.5% | 459 |

### Prompt F

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | False | 30 | 27 | 3 |
| look_at_obj_in_light | False | 30 | 13 | 5 |
| look_at_obj_in_light | False | 30 | 26 | 3 |
| look_at_obj_in_light | False | 30 | 10 | 6 |
| look_at_obj_in_light | False | 30 | 14 | 5 |
| look_at_obj_in_light | False | 30 | 17 | 4 |
| look_at_obj_in_light | False | 30 | 5 | 6 |
| look_at_obj_in_light | False | 30 | 4 | 6 |
| look_at_obj_in_light | False | 30 | 8 | 6 |
| look_at_obj_in_light | False | 30 | 16 | 5 |
| look_at_obj_in_light | False | 30 | 10 | 5 |
| look_at_obj_in_light | True | 3 | 0 | 3 |
| look_at_obj_in_light | False | 30 | 5 | 8 |
| look_at_obj_in_light | True | 4 | 0 | 4 |
| look_at_obj_in_light | False | 30 | 16 | 5 |
| look_at_obj_in_light | False | 30 | 7 | 8 |
| look_at_obj_in_light | True | 3 | 0 | 3 |
| look_at_obj_in_light | False | 30 | 11 | 7 |
| pick_and_place_simple | True | 10 | 0 | 8 |
| pick_and_place_simple | True | 11 | 0 | 10 |
| pick_and_place_simple | True | 6 | 0 | 5 |
| pick_and_place_simple | True | 16 | 4 | 7 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | True | 4 | 0 | 4 |
| pick_and_place_simple | False | 30 | 0 | 14 |
| pick_and_place_simple | True | 14 | 0 | 12 |
| pick_and_place_simple | False | 30 | 1 | 12 |
| pick_and_place_simple | False | 30 | 6 | 9 |
| pick_and_place_simple | False | 30 | 1 | 15 |
| pick_and_place_simple | False | 30 | 28 | 2 |
| pick_and_place_simple | True | 8 | 0 | 8 |
| pick_and_place_simple | True | 5 | 0 | 5 |
| pick_and_place_simple | False | 30 | 5 | 16 |
| pick_and_place_simple | True | 6 | 0 | 6 |
| pick_and_place_simple | True | 16 | 0 | 10 |
| pick_and_place_simple | True | 11 | 1 | 7 |
| pick_and_place_simple | False | 30 | 1 | 16 |
| pick_and_place_simple | False | 30 | 2 | 16 |
| pick_and_place_simple | False | 30 | 1 | 19 |
| pick_and_place_simple | False | 30 | 1 | 14 |
| pick_and_place_simple | False | 30 | 3 | 14 |
| pick_and_place_simple | False | 30 | 1 | 19 |
| pick_clean_then_place_in_recep | False | 30 | 4 | 16 |
| pick_clean_then_place_in_recep | True | 18 | 0 | 13 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 16 |
| pick_clean_then_place_in_recep | False | 30 | 2 | 17 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 15 |
| pick_clean_then_place_in_recep | True | 25 | 0 | 15 |
| pick_clean_then_place_in_recep | False | 30 | 1 | 13 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 16 |
| pick_clean_then_place_in_recep | False | 30 | 7 | 16 |
| pick_clean_then_place_in_recep | True | 22 | 1 | 15 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 14 |
| pick_clean_then_place_in_recep | False | 30 | 2 | 13 |
| pick_clean_then_place_in_recep | False | 30 | 28 | 2 |
| pick_clean_then_place_in_recep | True | 13 | 1 | 10 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 17 |
| pick_clean_then_place_in_recep | False | 30 | 5 | 14 |
| pick_clean_then_place_in_recep | False | 30 | 3 | 13 |
| pick_clean_then_place_in_recep | False | 30 | 1 | 15 |
| pick_clean_then_place_in_recep | False | 30 | 2 | 17 |
| pick_clean_then_place_in_recep | False | 30 | 1 | 16 |
| pick_clean_then_place_in_recep | True | 11 | 0 | 9 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 17 |
| pick_clean_then_place_in_recep | True | 15 | 1 | 12 |
| pick_clean_then_place_in_recep | False | 30 | 1 | 16 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 15 |
| pick_clean_then_place_in_recep | True | 25 | 1 | 17 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 14 |
| pick_clean_then_place_in_recep | False | 30 | 1 | 17 |
| pick_clean_then_place_in_recep | False | 30 | 28 | 2 |
| pick_clean_then_place_in_recep | False | 30 | 3 | 16 |
| pick_clean_then_place_in_recep | False | 30 | 28 | 2 |
| pick_cool_then_place_in_recep | False | 30 | 4 | 19 |
| pick_cool_then_place_in_recep | False | 30 | 2 | 14 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 21 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 11 |
| pick_cool_then_place_in_recep | False | 30 | 1 | 19 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 15 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 18 |
| pick_cool_then_place_in_recep | False | 30 | 1 | 15 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 9 |
| pick_cool_then_place_in_recep | False | 30 | 1 | 17 |
| pick_cool_then_place_in_recep | False | 30 | 2 | 20 |
| pick_cool_then_place_in_recep | False | 30 | 1 | 14 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 15 |
| pick_cool_then_place_in_recep | True | 21 | 2 | 12 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 22 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 18 |
| pick_cool_then_place_in_recep | False | 30 | 0 | 15 |
| pick_cool_then_place_in_recep | False | 30 | 1 | 16 |
| pick_cool_then_place_in_recep | False | 30 | 2 | 18 |
| pick_cool_then_place_in_recep | False | 30 | 1 | 23 |
| pick_cool_then_place_in_recep | False | 30 | 1 | 14 |
| pick_heat_then_place_in_recep | False | 30 | 0 | 16 |
| pick_heat_then_place_in_recep | False | 30 | 2 | 16 |
| pick_heat_then_place_in_recep | False | 30 | 3 | 11 |
| pick_heat_then_place_in_recep | False | 30 | 2 | 17 |
| pick_heat_then_place_in_recep | True | 10 | 0 | 10 |
| pick_heat_then_place_in_recep | True | 16 | 1 | 12 |
| pick_heat_then_place_in_recep | False | 30 | 1 | 14 |
| pick_heat_then_place_in_recep | False | 30 | 2 | 15 |
| pick_heat_then_place_in_recep | False | 30 | 2 | 20 |
| pick_heat_then_place_in_recep | False | 30 | 2 | 15 |
| pick_heat_then_place_in_recep | True | 11 | 0 | 9 |
| pick_heat_then_place_in_recep | False | 30 | 8 | 12 |
| pick_heat_then_place_in_recep | False | 30 | 3 | 15 |
| pick_heat_then_place_in_recep | False | 30 | 3 | 14 |
| pick_heat_then_place_in_recep | True | 27 | 7 | 15 |
| pick_heat_then_place_in_recep | False | 30 | 11 | 12 |
| pick_heat_then_place_in_recep | False | 30 | 3 | 14 |
| pick_heat_then_place_in_recep | False | 30 | 28 | 2 |
| pick_heat_then_place_in_recep | False | 30 | 1 | 13 |
| pick_heat_then_place_in_recep | False | 30 | 3 | 20 |
| pick_heat_then_place_in_recep | False | 30 | 4 | 17 |
| pick_heat_then_place_in_recep | False | 30 | 4 | 11 |
| pick_heat_then_place_in_recep | True | 25 | 4 | 15 |
| pick_two_obj_and_place | False | 30 | 1 | 18 |
| pick_two_obj_and_place | True | 13 | 0 | 11 |
| pick_two_obj_and_place | False | 30 | 1 | 20 |
| pick_two_obj_and_place | False | 30 | 3 | 14 |
| pick_two_obj_and_place | False | 30 | 0 | 14 |
| pick_two_obj_and_place | False | 30 | 0 | 19 |
| pick_two_obj_and_place | False | 30 | 0 | 18 |
| pick_two_obj_and_place | False | 30 | 1 | 24 |
| pick_two_obj_and_place | False | 30 | 2 | 16 |
| pick_two_obj_and_place | True | 15 | 2 | 10 |
| pick_two_obj_and_place | False | 30 | 1 | 16 |
| pick_two_obj_and_place | False | 30 | 0 | 13 |
| pick_two_obj_and_place | False | 30 | 1 | 14 |
| pick_two_obj_and_place | True | 23 | 0 | 19 |
| pick_two_obj_and_place | True | 18 | 0 | 13 |
| pick_two_obj_and_place | False | 30 | 1 | 14 |
| pick_two_obj_and_place | False | 30 | 0 | 14 |

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
