# Trajectory: qwen3-1.7b-i-experience_guided_action

- Task: `valid_train/pick_clean_then_place_in_recep-Bowl-None-Shelf-7/trial_T20190908_152949_169018`
- Goal: Place a cleaned bowl on a shelf
- Result: success=True, reason=success
- Steps: 16
- Parsed/fallback: 15/0
- Repeated actions: 0
- Unchanged observations: 0

## Step 0

Observation:
```text
-= Welcome to TextWorld, ALFRED! =-

You are in the middle of a room. Looking quickly around you, you see a cabinet 13, a cabinet 12, a cabinet 11, a cabinet 10, a cabinet 9, a cabinet 8, a cabinet 7, a cabinet 6, a cabinet 5, a cabinet 4, a cabinet 3, a cabinet 2, a cabinet 1, a coffeemachine 1, a countertop 2, a countertop 1, a diningtable 1, a drawer 4, a drawer 3, a drawer 2, a drawer 1, a fridge 1, a garbagecan 1, a microwave 1, a shelf 3, a shelf 2, a shelf 1, a sinkbasin 1, a stoveburner 4, a stoveburner 3, a stoveburner 2, a stoveburner 1, and a toaster 1.

Your task is to: clean some bowl and put it in shelf.
```

Model response: `<action>go to cabinet 1</action>`
Parsed: `True` (`tagged_exact_action`)
Action: `go to cabinet 1`
Proposed action: `go to cabinet 1`
Repair reason: `None`
Experience version: `exp-v3-from-h-offset2-failures`
Experience override: `None`
Experience rules: `[]`

Reconstructed state before decision:
```json
{
  "task_recipe": [
    "find and take the goal object",
    "go to a sinkbasin and clean the held object",
    "go to the goal receptacle",
    "place the cleaned object"
  ],
  "target_object_type": "Bowl",
  "target_destination_type": "Shelf",
  "target_toggle_type": null,
  "current_location": null,
  "inventory": null,
  "visited_locations": [],
  "opened_receptacles": [],
  "empty_receptacles": [],
  "known_placements": [],
  "transformed_objects": [],
  "toggled_objects": [],
  "stalled_actions": [],
  "recent_actions": []
}
```

Result:
```text
You arrive at cabinet 1. The cabinet 1 is closed.
```

## Step 1

Observation:
```text
You arrive at cabinet 1. The cabinet 1 is closed.
```

Model response: `<action>open cabinet 1</action>`
Parsed: `True` (`tagged_exact_action`)
Action: `open cabinet 1`
Proposed action: `open cabinet 1`
Repair reason: `None`
Experience version: `exp-v3-from-h-offset2-failures`
Experience override: `open_unsearched_current_receptacle`
Experience rules: `['novelty-before-revisit']`

Reconstructed state before decision:
```json
{
  "task_recipe": [
    "find and take the goal object",
    "go to a sinkbasin and clean the held object",
    "go to the goal receptacle",
    "place the cleaned object"
  ],
  "target_object_type": "Bowl",
  "target_destination_type": "Shelf",
  "target_toggle_type": null,
  "current_location": "cabinet 1",
  "inventory": null,
  "visited_locations": [
    "cabinet 1"
  ],
  "opened_receptacles": [],
  "empty_receptacles": [],
  "known_placements": [],
  "transformed_objects": [],
  "toggled_objects": [],
  "stalled_actions": [],
  "recent_actions": [
    "go to cabinet 1"
  ]
}
```

Result:
```text
You open the cabinet 1. The cabinet 1 is open. In it, you see nothing.
```

## Step 2

Observation:
```text
You open the cabinet 1. The cabinet 1 is open. In it, you see nothing.
```

Model response: `<action>go to shelf 1</action>`
Parsed: `True` (`tagged_exact_action`)
Action: `go to shelf 1`
Proposed action: `go to shelf 1`
Repair reason: `None`
Experience version: `exp-v3-from-h-offset2-failures`
Experience override: `None`
Experience rules: `[]`

Reconstructed state before decision:
```json
{
  "task_recipe": [
    "find and take the goal object",
    "go to a sinkbasin and clean the held object",
    "go to the goal receptacle",
    "place the cleaned object"
  ],
  "target_object_type": "Bowl",
  "target_destination_type": "Shelf",
  "target_toggle_type": null,
  "current_location": "cabinet 1",
  "inventory": null,
  "visited_locations": [
    "cabinet 1"
  ],
  "opened_receptacles": [
    "cabinet 1"
  ],
  "empty_receptacles": [
    "cabinet 1"
  ],
  "known_placements": [],
  "transformed_objects": [],
  "toggled_objects": [],
  "stalled_actions": [],
  "recent_actions": [
    "go to cabinet 1",
    "open cabinet 1"
  ]
}
```

Result:
```text
You arrive at shelf 1. On the shelf 1, you see nothing.
```

## Step 3

Observation:
```text
You arrive at shelf 1. On the shelf 1, you see nothing.
```

Model response: `<action>look</action>`
Parsed: `True` (`tagged_exact_action`)
Action: `go to coffeemachine 1`
Proposed action: `look`
Repair reason: `None`
Experience version: `exp-v3-from-h-offset2-failures`
Experience override: `explore_unvisited_location_type`
Experience rules: `['novelty-before-revisit', 'diversify-location-types']`

Reconstructed state before decision:
```json
{
  "task_recipe": [
    "find and take the goal object",
    "go to a sinkbasin and clean the held object",
    "go to the goal receptacle",
    "place the cleaned object"
  ],
  "target_object_type": "Bowl",
  "target_destination_type": "Shelf",
  "target_toggle_type": null,
  "current_location": "shelf 1",
  "inventory": null,
  "visited_locations": [
    "cabinet 1",
    "shelf 1"
  ],
  "opened_receptacles": [
    "cabinet 1"
  ],
  "empty_receptacles": [
    "cabinet 1"
  ],
  "known_placements": [],
  "transformed_objects": [],
  "toggled_objects": [],
  "stalled_actions": [],
  "recent_actions": [
    "go to cabinet 1",
    "open cabinet 1",
    "go to shelf 1"
  ]
}
```

Result:
```text
You arrive at coffeemachine 1. On the coffeemachine 1, you see a mug 2.
```

## Step 4

Observation:
```text
You arrive at coffeemachine 1. On the coffeemachine 1, you see a mug 2.
```

Model response: `<action>take mug 2 from coffeemachine 1</action>`
Parsed: `True` (`tagged_exact_action`)
Action: `go to countertop 1`
Proposed action: `take mug 2 from coffeemachine 1`
Repair reason: `None`
Experience version: `exp-v3-from-h-offset2-failures`
Experience override: `explore_unvisited_location_type`
Experience rules: `['novelty-before-revisit', 'diversify-location-types']`

Reconstructed state before decision:
```json
{
  "task_recipe": [
    "find and take the goal object",
    "go to a sinkbasin and clean the held object",
    "go to the goal receptacle",
    "place the cleaned object"
  ],
  "target_object_type": "Bowl",
  "target_destination_type": "Shelf",
  "target_toggle_type": null,
  "current_location": "coffeemachine 1",
  "inventory": null,
  "visited_locations": [
    "cabinet 1",
    "coffeemachine 1",
    "shelf 1"
  ],
  "opened_receptacles": [
    "cabinet 1"
  ],
  "empty_receptacles": [
    "cabinet 1"
  ],
  "known_placements": [],
  "transformed_objects": [],
  "toggled_objects": [],
  "stalled_actions": [],
  "recent_actions": [
    "go to cabinet 1",
    "open cabinet 1",
    "go to shelf 1",
    "go to coffeemachine 1"
  ]
}
```

Result:
```text
You arrive at countertop 1. On the countertop 1, you see a butterknife 1, a saltshaker 1, and a spoon 1.
```

## Step 5

Observation:
```text
You arrive at countertop 1. On the countertop 1, you see a butterknife 1, a saltshaker 1, and a spoon 1.
```

Model response: `<action>take spoon 1 from countertop 1</action>`
Parsed: `True` (`tagged_exact_action`)
Action: `go to diningtable 1`
Proposed action: `take spoon 1 from countertop 1`
Repair reason: `None`
Experience version: `exp-v3-from-h-offset2-failures`
Experience override: `explore_unvisited_location_type`
Experience rules: `['novelty-before-revisit', 'diversify-location-types']`

Reconstructed state before decision:
```json
{
  "task_recipe": [
    "find and take the goal object",
    "go to a sinkbasin and clean the held object",
    "go to the goal receptacle",
    "place the cleaned object"
  ],
  "target_object_type": "Bowl",
  "target_destination_type": "Shelf",
  "target_toggle_type": null,
  "current_location": "countertop 1",
  "inventory": null,
  "visited_locations": [
    "cabinet 1",
    "coffeemachine 1",
    "countertop 1",
    "shelf 1"
  ],
  "opened_receptacles": [
    "cabinet 1"
  ],
  "empty_receptacles": [
    "cabinet 1"
  ],
  "known_placements": [],
  "transformed_objects": [],
  "toggled_objects": [],
  "stalled_actions": [],
  "recent_actions": [
    "go to cabinet 1",
    "open cabinet 1",
    "go to shelf 1",
    "go to coffeemachine 1",
    "go to countertop 1"
  ]
}
```

Result:
```text
You arrive at diningtable 1. On the diningtable 1, you see a fork 1, a houseplant 1, a kettle 1, a knife 1, a lettuce 2, a lettuce 1, a mug 1, a plate 2, a soapbottle 3, a soapbottle 2, a spatula 1, a tomato 2, and a tomato 1.
```

## Step 6

Observation:
```text
You arrive at diningtable 1. On the diningtable 1, you see a fork 1, a houseplant 1, a kettle 1, a knife 1, a lettuce 2, a lettuce 1, a mug 1, a plate 2, a soapbottle 3, a soapbottle 2, a spatula 1, a tomato 2, and a tomato 1.
```

Model response: `<action>take bowl from diningtable 1</action>`
Parsed: `False` (`None`)
Action: `go to drawer 1`
Proposed action: `take bowl from diningtable 1`
Repair reason: `None`
Experience version: `exp-v3-from-h-offset2-failures`
Experience override: `explore_unvisited_location_type`
Experience rules: `['novelty-before-revisit', 'diversify-location-types']`

Reconstructed state before decision:
```json
{
  "task_recipe": [
    "find and take the goal object",
    "go to a sinkbasin and clean the held object",
    "go to the goal receptacle",
    "place the cleaned object"
  ],
  "target_object_type": "Bowl",
  "target_destination_type": "Shelf",
  "target_toggle_type": null,
  "current_location": "diningtable 1",
  "inventory": null,
  "visited_locations": [
    "cabinet 1",
    "coffeemachine 1",
    "countertop 1",
    "diningtable 1",
    "shelf 1"
  ],
  "opened_receptacles": [
    "cabinet 1"
  ],
  "empty_receptacles": [
    "cabinet 1"
  ],
  "known_placements": [],
  "transformed_objects": [],
  "toggled_objects": [],
  "stalled_actions": [],
  "recent_actions": [
    "go to cabinet 1",
    "open cabinet 1",
    "go to shelf 1",
    "go to coffeemachine 1",
    "go to countertop 1",
    "go to diningtable 1"
  ]
}
```

Result:
```text
You arrive at drawer 1. The drawer 1 is closed.
```

## Step 7

Observation:
```text
You arrive at drawer 1. The drawer 1 is closed.
```

Model response: `<action>open drawer 1</action>`
Parsed: `True` (`tagged_exact_action`)
Action: `open drawer 1`
Proposed action: `open drawer 1`
Repair reason: `None`
Experience version: `exp-v3-from-h-offset2-failures`
Experience override: `open_unsearched_current_receptacle`
Experience rules: `['novelty-before-revisit']`

Reconstructed state before decision:
```json
{
  "task_recipe": [
    "find and take the goal object",
    "go to a sinkbasin and clean the held object",
    "go to the goal receptacle",
    "place the cleaned object"
  ],
  "target_object_type": "Bowl",
  "target_destination_type": "Shelf",
  "target_toggle_type": null,
  "current_location": "drawer 1",
  "inventory": null,
  "visited_locations": [
    "cabinet 1",
    "coffeemachine 1",
    "countertop 1",
    "diningtable 1",
    "drawer 1",
    "shelf 1"
  ],
  "opened_receptacles": [
    "cabinet 1"
  ],
  "empty_receptacles": [
    "cabinet 1"
  ],
  "known_placements": [],
  "transformed_objects": [],
  "toggled_objects": [],
  "stalled_actions": [],
  "recent_actions": [
    "open cabinet 1",
    "go to shelf 1",
    "go to coffeemachine 1",
    "go to countertop 1",
    "go to diningtable 1",
    "go to drawer 1"
  ]
}
```

Result:
```text
You open the drawer 1. The drawer 1 is open. In it, you see nothing.
```

## Step 8

Observation:
```text
You open the drawer 1. The drawer 1 is open. In it, you see nothing.
```

Model response: `<action>go to sinkbasin 1</action>`
Parsed: `True` (`tagged_exact_action`)
Action: `go to sinkbasin 1`
Proposed action: `go to sinkbasin 1`
Repair reason: `None`
Experience version: `exp-v3-from-h-offset2-failures`
Experience override: `None`
Experience rules: `[]`

Reconstructed state before decision:
```json
{
  "task_recipe": [
    "find and take the goal object",
    "go to a sinkbasin and clean the held object",
    "go to the goal receptacle",
    "place the cleaned object"
  ],
  "target_object_type": "Bowl",
  "target_destination_type": "Shelf",
  "target_toggle_type": null,
  "current_location": "drawer 1",
  "inventory": null,
  "visited_locations": [
    "cabinet 1",
    "coffeemachine 1",
    "countertop 1",
    "diningtable 1",
    "drawer 1",
    "shelf 1"
  ],
  "opened_receptacles": [
    "cabinet 1",
    "drawer 1"
  ],
  "empty_receptacles": [
    "cabinet 1",
    "drawer 1"
  ],
  "known_placements": [],
  "transformed_objects": [],
  "toggled_objects": [],
  "stalled_actions": [],
  "recent_actions": [
    "go to shelf 1",
    "go to coffeemachine 1",
    "go to countertop 1",
    "go to diningtable 1",
    "go to drawer 1",
    "open drawer 1"
  ]
}
```

Result:
```text
You arrive at sinkbasin 1. On the sinkbasin 1, you see nothing.
```

## Step 9

Observation:
```text
You arrive at sinkbasin 1. On the sinkbasin 1, you see nothing.
```

Model response: `<action>examine sinkbasin 1</action>`
Parsed: `True` (`tagged_exact_action`)
Action: `go to fridge 1`
Proposed action: `examine sinkbasin 1`
Repair reason: `None`
Experience version: `exp-v3-from-h-offset2-failures`
Experience override: `explore_unvisited_location_type`
Experience rules: `['novelty-before-revisit', 'diversify-location-types']`

Reconstructed state before decision:
```json
{
  "task_recipe": [
    "find and take the goal object",
    "go to a sinkbasin and clean the held object",
    "go to the goal receptacle",
    "place the cleaned object"
  ],
  "target_object_type": "Bowl",
  "target_destination_type": "Shelf",
  "target_toggle_type": null,
  "current_location": "sinkbasin 1",
  "inventory": null,
  "visited_locations": [
    "cabinet 1",
    "coffeemachine 1",
    "countertop 1",
    "diningtable 1",
    "drawer 1",
    "shelf 1",
    "sinkbasin 1"
  ],
  "opened_receptacles": [
    "cabinet 1",
    "drawer 1"
  ],
  "empty_receptacles": [
    "cabinet 1",
    "drawer 1"
  ],
  "known_placements": [],
  "transformed_objects": [],
  "toggled_objects": [],
  "stalled_actions": [],
  "recent_actions": [
    "go to coffeemachine 1",
    "go to countertop 1",
    "go to diningtable 1",
    "go to drawer 1",
    "open drawer 1",
    "go to sinkbasin 1"
  ]
}
```

Result:
```text
You arrive at fridge 1. The fridge 1 is closed.
```

## Step 10

Observation:
```text
You arrive at fridge 1. The fridge 1 is closed.
```

Model response: `<action>examine fridge 1</action>`
Parsed: `True` (`tagged_exact_action`)
Action: `open fridge 1`
Proposed action: `examine fridge 1`
Repair reason: `None`
Experience version: `exp-v3-from-h-offset2-failures`
Experience override: `open_unsearched_current_receptacle`
Experience rules: `['novelty-before-revisit']`

Reconstructed state before decision:
```json
{
  "task_recipe": [
    "find and take the goal object",
    "go to a sinkbasin and clean the held object",
    "go to the goal receptacle",
    "place the cleaned object"
  ],
  "target_object_type": "Bowl",
  "target_destination_type": "Shelf",
  "target_toggle_type": null,
  "current_location": "fridge 1",
  "inventory": null,
  "visited_locations": [
    "cabinet 1",
    "coffeemachine 1",
    "countertop 1",
    "diningtable 1",
    "drawer 1",
    "fridge 1",
    "shelf 1",
    "sinkbasin 1"
  ],
  "opened_receptacles": [
    "cabinet 1",
    "drawer 1"
  ],
  "empty_receptacles": [
    "cabinet 1",
    "drawer 1"
  ],
  "known_placements": [],
  "transformed_objects": [],
  "toggled_objects": [],
  "stalled_actions": [],
  "recent_actions": [
    "go to countertop 1",
    "go to diningtable 1",
    "go to drawer 1",
    "open drawer 1",
    "go to sinkbasin 1",
    "go to fridge 1"
  ]
}
```

Result:
```text
You open the fridge 1. The fridge 1 is open. In it, you see a apple 1, a bowl 4, a bread 3, a cup 1, and a egg 1.
```

## Step 11

Observation:
```text
You open the fridge 1. The fridge 1 is open. In it, you see a apple 1, a bowl 4, a bread 3, a cup 1, and a egg 1.
```

Model response: `<action>take bowl 4 from fridge 1</action>`
Parsed: `True` (`tagged_exact_action`)
Action: `take bowl 4 from fridge 1`
Proposed action: `take bowl 4 from fridge 1`
Repair reason: `None`
Experience version: `exp-v3-from-h-offset2-failures`
Experience override: `take_visible_target_object`
Experience rules: `['target-object-lock']`

Reconstructed state before decision:
```json
{
  "task_recipe": [
    "find and take the goal object",
    "go to a sinkbasin and clean the held object",
    "go to the goal receptacle",
    "place the cleaned object"
  ],
  "target_object_type": "Bowl",
  "target_destination_type": "Shelf",
  "target_toggle_type": null,
  "current_location": "fridge 1",
  "inventory": null,
  "visited_locations": [
    "cabinet 1",
    "coffeemachine 1",
    "countertop 1",
    "diningtable 1",
    "drawer 1",
    "fridge 1",
    "shelf 1",
    "sinkbasin 1"
  ],
  "opened_receptacles": [
    "cabinet 1",
    "drawer 1",
    "fridge 1"
  ],
  "empty_receptacles": [
    "cabinet 1",
    "drawer 1"
  ],
  "known_placements": [],
  "transformed_objects": [],
  "toggled_objects": [],
  "stalled_actions": [],
  "recent_actions": [
    "go to diningtable 1",
    "go to drawer 1",
    "open drawer 1",
    "go to sinkbasin 1",
    "go to fridge 1",
    "open fridge 1"
  ]
}
```

Result:
```text
You pick up the bowl 4 from the fridge 1.
```

## Step 12

Observation:
```text
You pick up the bowl 4 from the fridge 1.
```

Model response: `<action>go to shelf 1</action>`
Parsed: `True` (`tagged_exact_action`)
Action: `go to sinkbasin 1`
Proposed action: `go to shelf 1`
Repair reason: `None`
Experience version: `exp-v3-from-h-offset2-failures`
Experience override: `navigate_to_clean_appliance`
Experience rules: `['ordered-task-recipe']`

Reconstructed state before decision:
```json
{
  "task_recipe": [
    "find and take the goal object",
    "go to a sinkbasin and clean the held object",
    "go to the goal receptacle",
    "place the cleaned object"
  ],
  "target_object_type": "Bowl",
  "target_destination_type": "Shelf",
  "target_toggle_type": null,
  "current_location": "fridge 1",
  "inventory": "bowl 4",
  "visited_locations": [
    "cabinet 1",
    "coffeemachine 1",
    "countertop 1",
    "diningtable 1",
    "drawer 1",
    "fridge 1",
    "shelf 1",
    "sinkbasin 1"
  ],
  "opened_receptacles": [
    "cabinet 1",
    "drawer 1",
    "fridge 1"
  ],
  "empty_receptacles": [
    "cabinet 1",
    "drawer 1"
  ],
  "known_placements": [],
  "transformed_objects": [],
  "toggled_objects": [],
  "stalled_actions": [],
  "recent_actions": [
    "go to drawer 1",
    "open drawer 1",
    "go to sinkbasin 1",
    "go to fridge 1",
    "open fridge 1",
    "take bowl 4 from fridge 1"
  ]
}
```

Result:
```text
You arrive at sinkbasin 1. On the sinkbasin 1, you see nothing.
```

## Step 13

Observation:
```text
You arrive at sinkbasin 1. On the sinkbasin 1, you see nothing.
```

Model response: `<action>clean bowl 4 with sinkbasin 1</action>`
Parsed: `True` (`tagged_exact_action`)
Action: `clean bowl 4 with sinkbasin 1`
Proposed action: `clean bowl 4 with sinkbasin 1`
Repair reason: `None`
Experience version: `exp-v3-from-h-offset2-failures`
Experience override: `execute_required_clean`
Experience rules: `['ordered-task-recipe']`

Reconstructed state before decision:
```json
{
  "task_recipe": [
    "find and take the goal object",
    "go to a sinkbasin and clean the held object",
    "go to the goal receptacle",
    "place the cleaned object"
  ],
  "target_object_type": "Bowl",
  "target_destination_type": "Shelf",
  "target_toggle_type": null,
  "current_location": "sinkbasin 1",
  "inventory": "bowl 4",
  "visited_locations": [
    "cabinet 1",
    "coffeemachine 1",
    "countertop 1",
    "diningtable 1",
    "drawer 1",
    "fridge 1",
    "shelf 1",
    "sinkbasin 1"
  ],
  "opened_receptacles": [
    "cabinet 1",
    "drawer 1",
    "fridge 1"
  ],
  "empty_receptacles": [
    "cabinet 1",
    "drawer 1"
  ],
  "known_placements": [],
  "transformed_objects": [],
  "toggled_objects": [],
  "stalled_actions": [],
  "recent_actions": [
    "open drawer 1",
    "go to sinkbasin 1",
    "go to fridge 1",
    "open fridge 1",
    "take bowl 4 from fridge 1",
    "go to sinkbasin 1"
  ]
}
```

Result:
```text
You clean the bowl 4 using the sinkbasin 1.
```

## Step 14

Observation:
```text
You clean the bowl 4 using the sinkbasin 1.
```

Model response: `<action>go to shelf 1</action>`
Parsed: `True` (`tagged_exact_action`)
Action: `go to shelf 1`
Proposed action: `go to shelf 1`
Repair reason: `None`
Experience version: `exp-v3-from-h-offset2-failures`
Experience override: `navigate_to_target_destination`
Experience rules: `['ordered-task-recipe']`

Reconstructed state before decision:
```json
{
  "task_recipe": [
    "find and take the goal object",
    "go to a sinkbasin and clean the held object",
    "go to the goal receptacle",
    "place the cleaned object"
  ],
  "target_object_type": "Bowl",
  "target_destination_type": "Shelf",
  "target_toggle_type": null,
  "current_location": "sinkbasin 1",
  "inventory": "bowl 4",
  "visited_locations": [
    "cabinet 1",
    "coffeemachine 1",
    "countertop 1",
    "diningtable 1",
    "drawer 1",
    "fridge 1",
    "shelf 1",
    "sinkbasin 1"
  ],
  "opened_receptacles": [
    "cabinet 1",
    "drawer 1",
    "fridge 1"
  ],
  "empty_receptacles": [
    "cabinet 1",
    "drawer 1"
  ],
  "known_placements": [],
  "transformed_objects": [
    "bowl 4: clean"
  ],
  "toggled_objects": [],
  "stalled_actions": [],
  "recent_actions": [
    "go to sinkbasin 1",
    "go to fridge 1",
    "open fridge 1",
    "take bowl 4 from fridge 1",
    "go to sinkbasin 1",
    "clean bowl 4 with sinkbasin 1"
  ]
}
```

Result:
```text
You arrive at shelf 1. On the shelf 1, you see nothing.
```

## Step 15

Observation:
```text
You arrive at shelf 1. On the shelf 1, you see nothing.
```

Model response: `<action>move bowl 4 to shelf 1</action>`
Parsed: `True` (`tagged_exact_action`)
Action: `move bowl 4 to shelf 1`
Proposed action: `move bowl 4 to shelf 1`
Repair reason: `None`
Experience version: `exp-v3-from-h-offset2-failures`
Experience override: `deliver_completed_target`
Experience rules: `['ordered-task-recipe']`

Reconstructed state before decision:
```json
{
  "task_recipe": [
    "find and take the goal object",
    "go to a sinkbasin and clean the held object",
    "go to the goal receptacle",
    "place the cleaned object"
  ],
  "target_object_type": "Bowl",
  "target_destination_type": "Shelf",
  "target_toggle_type": null,
  "current_location": "shelf 1",
  "inventory": "bowl 4",
  "visited_locations": [
    "cabinet 1",
    "coffeemachine 1",
    "countertop 1",
    "diningtable 1",
    "drawer 1",
    "fridge 1",
    "shelf 1",
    "sinkbasin 1"
  ],
  "opened_receptacles": [
    "cabinet 1",
    "drawer 1",
    "fridge 1"
  ],
  "empty_receptacles": [
    "cabinet 1",
    "drawer 1"
  ],
  "known_placements": [],
  "transformed_objects": [
    "bowl 4: clean"
  ],
  "toggled_objects": [],
  "stalled_actions": [],
  "recent_actions": [
    "go to fridge 1",
    "open fridge 1",
    "take bowl 4 from fridge 1",
    "go to sinkbasin 1",
    "clean bowl 4 with sinkbasin 1",
    "go to shelf 1"
  ]
}
```

Result:
```text
You move the bowl 4 to the shelf 1.
```
