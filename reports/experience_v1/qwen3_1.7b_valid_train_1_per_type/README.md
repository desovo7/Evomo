# Qwen3-1.7B ALFWorld multi-task prompt comparison

- Split: `valid_train`
- Tasks per prompt: 6
- Samples per task type: 1

This is the experience-source task set (`task_offset=0`). F is the strict
current-code state baseline without an experience file. G is the preserved
exp-v1 experiment: it exposed excessive same-type exploration and an
unscoped-prompt bug. H fixes prompt scoping and loads exp-v2, which adds the
evidence-backed `diversify-location-types` rule. These results measure
iteration on tasks used to create the experiences; use the held-out report for
transfer evidence.

| Prompt | Success | Parsed actions | Repaired | Experience overrides | True fallback | Repeats | Unchanged obs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| F | 2/6 (33.3%) | 119/144 | 4 | 0 | 21 | 7 | 7 |
| G | 4/6 (66.7%) | 91/106 | 2 | 61 | 7 | 3 | 3 |
| H | 6/6 (100.0%) | 61/74 | 4 | 44 | 3 | 1 | 1 |

All six H successes are native ALFWorld terminal successes with reward 1.0.
Exp-v1 was extracted only from F failures. Exp-v2 has exp-v1 as its parent and
adds one rule from G's heat failure; it does not store object locations or
task-specific action sequences.

## Per-task results

### Prompt F

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | False | 30 | 4 | 12 |
| pick_and_place_simple | True | 15 | 1 | 10 |
| pick_clean_then_place_in_recep | False | 30 | 1 | 21 |
| pick_cool_then_place_in_recep | False | 30 | 1 | 15 |
| pick_heat_then_place_in_recep | False | 30 | 0 | 22 |
| pick_two_obj_and_place | True | 9 | 0 | 7 |

### Prompt G

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | True | 19 | 0 | 19 |
| pick_and_place_simple | False | 30 | 3 | 5 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 9 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 8 |
| pick_heat_then_place_in_recep | False | 30 | 0 | 30 |
| pick_two_obj_and_place | True | 9 | 0 | 7 |

### Prompt H

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | True | 19 | 0 | 19 |
| pick_and_place_simple | True | 15 | 1 | 10 |
| pick_clean_then_place_in_recep | True | 9 | 0 | 9 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 13 | 0 | 12 |
| pick_two_obj_and_place | True | 9 | 0 | 7 |
