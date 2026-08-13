from __future__ import annotations

import importlib.util
from pathlib import Path


def load_module():
    spec = importlib.util.spec_from_file_location(
        "analyze_alfworld_failures",
        Path(__file__).parents[1] / "scripts" / "analyze_alfworld_failures.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def step(index: int, action: str, *, inventory: str | None = None) -> dict:
    return {
        "step_index": index,
        "action": action,
        "info": {"policy": {"metadata": {"state_before": {"inventory": inventory}}}},
    }


def episode(task_type: str, steps: list[dict]) -> dict:
    return {
        "task": {
            "task_type": task_type,
            "metadata": {
                "pddl_params": {
                    "object_target": "SoapBar",
                    "parent_target": "GarbageCan",
                    "toggle_target": "",
                }
            },
        },
        "steps": steps,
    }


def test_classifies_retake_only_after_delivery_to_target() -> None:
    module = load_module()
    value = episode(
        "pick_two_obj_and_place",
        [
            step(0, "move soapbar 1 to garbagecan 1", inventory="soapbar 1"),
            step(1, "take soapbar 1 from garbagecan 1"),
        ],
    )

    assert module.classify(value) == ("retake_delivered_target", [1])


def test_classifies_missing_target_from_terminal_state() -> None:
    module = load_module()
    value = episode(
        "pick_clean_then_place_in_recep",
        [step(index, f"go to cabinet {index + 1}") for index in range(8)],
    )

    signature, indices = module.classify(value)

    assert signature == "target_not_acquired"
    assert indices == list(range(8))
