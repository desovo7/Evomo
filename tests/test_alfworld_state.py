from __future__ import annotations

from evomo.data import TaskSpec
from evomo.policies import (
    HistoryItem,
    reconstruct_alfworld_state,
    repair_unavailable_action,
    task_recipe,
)


def make_task(task_type: str = "pick_two_obj_and_place") -> TaskSpec:
    return TaskSpec(
        task_id="valid_train/problem/trial",
        split="valid_train",
        task_type=task_type,
        goal="Move two books from the bed to the desk.",
    )


def test_reconstructs_inventory_placement_and_location() -> None:
    history = (
        HistoryItem("start", "go to bed 1", "You arrive at bed 1. You see a book 1.", 0),
        HistoryItem(
            "You arrive at bed 1. You see a book 1.",
            "take book 1 from bed 1",
            "You pick up the book 1 from the bed 1.",
            0,
        ),
        HistoryItem(
            "You pick up the book 1 from the bed 1.",
            "go to desk 1",
            "You arrive at desk 1. On it, you see nothing.",
            0,
        ),
        HistoryItem(
            "You arrive at desk 1. On it, you see nothing.",
            "move book 1 to desk 1",
            "You move the book 1 to the desk 1.",
            0,
        ),
    )

    state = reconstruct_alfworld_state(make_task(), history, history[-1].next_observation)

    assert state.current_location == "desk 1"
    assert state.inventory is None
    assert state.visited_locations == ("bed 1", "desk 1")
    assert state.known_placements == ("book 1 in/on desk 1",)
    assert "return for a different instance" in state.task_recipe


def test_tracks_open_empty_transform_and_stall_without_inventing_success() -> None:
    history = (
        HistoryItem(
            "The cabinet 1 is closed.",
            "open cabinet 1",
            "You open the cabinet 1. The cabinet 1 is open. In it, you see nothing.",
            0,
        ),
        HistoryItem("same", "look", "same", 0),
        HistoryItem(
            "holding apple",
            "heat apple 1 with microwave 1",
            "The apple 1 is now hot.",
            0,
        ),
    )

    state = reconstruct_alfworld_state(
        make_task("pick_heat_then_place_in_recep"), history, history[-1].next_observation
    )

    assert state.opened_receptacles == ("cabinet 1",)
    assert state.empty_receptacles == ("cabinet 1",)
    assert state.transformed_objects == ("apple 1: heat",)
    assert state.stalled_actions == ("look (1x)",)
    assert task_recipe(make_task("pick_heat_then_place_in_recep"))[1].startswith(
        "go to a microwave"
    )


def test_repairs_future_take_and_move_intents_with_navigation_only() -> None:
    empty_state = reconstruct_alfworld_state(make_task(), (), "start")
    holding_state = reconstruct_alfworld_state(
        make_task(),
        (
            HistoryItem(
                "book visible",
                "take book 2 from bed 1",
                "You pick up the book 2 from the bed 1.",
                0,
            ),
        ),
        "You pick up the book 2 from the bed 1.",
    )

    assert repair_unavailable_action(
        "take alarmclock 2 from sidetable 1",
        ("look", "go to sidetable 1"),
        empty_state,
    ) == (1, "navigate_to_proposed_take_source")
    assert repair_unavailable_action(
        "move book 2 to desk 1",
        ("examine bed 1", "go to desk 1"),
        holding_state,
    ) == (1, "navigate_held_object_to_proposed_destination")
    assert (
        repair_unavailable_action(
            "move book 3 to desk 1",
            ("go to desk 1",),
            holding_state,
        )
        is None
    )
