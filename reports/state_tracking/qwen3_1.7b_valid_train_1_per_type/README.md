# Qwen3-1.7B ALFWorld multi-task prompt comparison

- Split: `valid_train`
- Tasks per prompt: 6
- Samples per task type: 1

| Prompt | Success | Parsed actions | Repaired | True fallback | Repeats | Unchanged obs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C | 0/6 (0.0%) | 173/180 | 0 | 7 | 23 | 23 |
| E | 0/6 (0.0%) | 145/180 | 0 | 35 | 31 | 31 |
| F | 2/6 (33.3%) | 145/153 | 4 | 4 | 5 | 5 |

## Per-task results

### Prompt C

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | False | 30 | 1 | 14 |
| pick_and_place_simple | False | 30 | 14 | 4 |
| pick_clean_then_place_in_recep | False | 30 | 1 | 17 |
| pick_cool_then_place_in_recep | False | 30 | 3 | 16 |
| pick_heat_then_place_in_recep | False | 30 | 4 | 23 |
| pick_two_obj_and_place | False | 30 | 0 | 6 |

### Prompt E

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | False | 30 | 1 | 12 |
| pick_and_place_simple | False | 30 | 9 | 12 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 14 |
| pick_cool_then_place_in_recep | False | 30 | 1 | 18 |
| pick_heat_then_place_in_recep | False | 30 | 1 | 19 |
| pick_two_obj_and_place | False | 30 | 19 | 9 |

### Prompt F

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | False | 30 | 1 | 12 |
| pick_and_place_simple | True | 24 | 2 | 12 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 14 |
| pick_cool_then_place_in_recep | False | 30 | 1 | 18 |
| pick_heat_then_place_in_recep | False | 30 | 1 | 19 |
| pick_two_obj_and_place | True | 9 | 0 | 7 |
