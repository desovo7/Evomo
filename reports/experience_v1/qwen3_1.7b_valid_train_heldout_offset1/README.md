# Qwen3-1.7B ALFWorld multi-task prompt comparison

- Split: `valid_train`
- Tasks per prompt: 6
- Samples per task type: 1

This held-out task set uses `task_offset=1`; its six task IDs are disjoint from
all tasks used to extract exp-v1 or evolve exp-v2. F and H use the same model,
state fields, greedy decoding, seed policy, history budget, and step limit. H
alone loads exp-v2. For task types without applicable experience, no experience
text is added to the model prompt and no experience override is allowed.

| Prompt | Success | Parsed actions | Repaired | Experience overrides | True fallback | Repeats | Unchanged obs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| F | 1/6 (16.7%) | 120/160 | 4 | 0 | 36 | 31 | 31 |
| H | 4/6 (66.7%) | 77/96 | 3 | 52 | 3 | 0 | 0 |

H transfers successfully to clean, cool, and heat tasks that F fails, plus the
two-object task already solved by F. The clean target changes from the source
task's bowl/shelf to cloth/cart, showing that target locking uses TaskSpec
metadata rather than a memorized object instance. H still fails the held-out
light and simple pick-and-place tasks, so this is evidence of partial transfer,
not a solved benchmark.

## Per-task results

### Prompt F

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | False | 30 | 26 | 4 |
| pick_and_place_simple | False | 30 | 0 | 13 |
| pick_clean_then_place_in_recep | False | 30 | 0 | 14 |
| pick_cool_then_place_in_recep | False | 30 | 3 | 15 |
| pick_heat_then_place_in_recep | False | 30 | 2 | 19 |
| pick_two_obj_and_place | True | 10 | 0 | 8 |

### Prompt H

| Task type | Success | Steps | Repeats | Unique actions |
| --- | ---: | ---: | ---: | ---: |
| look_at_obj_in_light | False | 30 | 0 | 30 |
| pick_and_place_simple | False | 30 | 0 | 13 |
| pick_clean_then_place_in_recep | True | 7 | 0 | 6 |
| pick_cool_then_place_in_recep | True | 9 | 0 | 8 |
| pick_heat_then_place_in_recep | True | 10 | 0 | 9 |
| pick_two_obj_and_place | True | 10 | 0 | 8 |
