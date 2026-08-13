# Qwen3-1.7B ALFWorld multi-task prompt comparison

- Split: `valid_train`
- Tasks per prompt: 6
- Samples per task type: 1

| Prompt | Success | Parsed actions | Format compliant | Repeats | Unchanged obs |
| --- | ---: | ---: | ---: | ---: | ---: |
| B | 0/6 (0.0%) | 179/180 | 179/180 | 90 | 90 |
| C | 0/6 (0.0%) | 173/180 | 0/180 | 23 | 23 |
| D | 0/6 (0.0%) | 153/180 | 46/180 | 33 | 33 |

## Per-task results

### Prompt B

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | False | 30 | 15 | 7 |
| pick_and_place_simple | False | 30 | 1 | 11 |
| pick_clean_then_place_in_recep | False | 30 | 28 | 2 |
| pick_cool_then_place_in_recep | False | 30 | 18 | 6 |
| pick_heat_then_place_in_recep | False | 30 | 24 | 4 |
| pick_two_obj_and_place | False | 30 | 4 | 19 |

### Prompt C

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | False | 30 | 1 | 14 |
| pick_and_place_simple | False | 30 | 14 | 4 |
| pick_clean_then_place_in_recep | False | 30 | 1 | 17 |
| pick_cool_then_place_in_recep | False | 30 | 3 | 16 |
| pick_heat_then_place_in_recep | False | 30 | 4 | 23 |
| pick_two_obj_and_place | False | 30 | 0 | 6 |

### Prompt D

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | False | 30 | 8 | 14 |
| pick_and_place_simple | False | 30 | 11 | 8 |
| pick_clean_then_place_in_recep | False | 30 | 11 | 11 |
| pick_cool_then_place_in_recep | False | 30 | 1 | 24 |
| pick_heat_then_place_in_recep | False | 30 | 0 | 19 |
| pick_two_obj_and_place | False | 30 | 2 | 11 |
