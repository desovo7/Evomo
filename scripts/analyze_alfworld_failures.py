"""Classify persisted ALFWorld failures into deterministic trajectory signatures."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


TAKE_RE = re.compile(r"^take (.+) from (.+)$", re.IGNORECASE)
MOVE_RE = re.compile(r"^move (.+) to (.+)$", re.IGNORECASE)
GO_RE = re.compile(r"^go to (.+)$", re.IGNORECASE)


def normalized_type(value: str) -> str:
    return re.sub(r"[^a-z]", "", re.sub(r"\s+\d+$", "", value).casefold())


def classify(episode: dict) -> tuple[str, list[int]]:
    steps = episode["steps"]
    task = episode["task"]
    params = task["metadata"]["pddl_params"]
    target = normalized_type(str(params.get("object_target", "")))
    destination = normalized_type(str(params.get("parent_target", "")))
    final_state = steps[-1]["info"]["policy"]["metadata"]["state_before"]
    inventory = final_state.get("inventory")

    if task["task_type"] == "pick_two_obj_and_place":
        move_by_object: dict[str, list[int]] = {}
        retakes: list[int] = []
        for step in steps:
            move = MOVE_RE.fullmatch(step["action"])
            if move and normalized_type(move.group(1)) == target and normalized_type(move.group(2)) == destination:
                move_by_object.setdefault(move.group(1).casefold(), []).append(step["step_index"])
            take = TAKE_RE.fullmatch(step["action"])
            if take and take.group(1).casefold() in move_by_object and normalized_type(take.group(2)) == destination:
                retakes.append(step["step_index"])
        if retakes:
            return "retake_delivered_target", retakes

    recent = steps[-8:]
    go_indices = [step["step_index"] for step in recent if GO_RE.fullmatch(step["action"])]
    go_places = [
        GO_RE.fullmatch(step["action"]).group(1)
        for step in recent
        if GO_RE.fullmatch(step["action"])
    ]
    if inventory and normalized_type(inventory) == target:
        if destination and sum(normalized_type(place) == destination for place in go_places) >= 3:
            return "destination_navigation_loop", go_indices
        if task["task_type"] == "look_at_obj_in_light":
            return "held_target_light_incomplete", [step["step_index"] for step in recent]
        return "held_target_task_incomplete", [step["step_index"] for step in recent]
    if inventory is None:
        return "target_not_acquired", [step["step_index"] for step in recent]
    return "other_inventory_state", [step["step_index"] for step in recent]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    failures = []
    episode_paths = sorted(args.episodes_root.glob("*/*/episode.jsonl"))
    if not episode_paths:
        episode_paths = sorted(args.episodes_root.glob("*/episode.jsonl"))
    for path in episode_paths:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        if len(rows) != 1:
            raise ValueError(f"{path}: expected one episode")
        episode = rows[0]
        if episode["success"]:
            continue
        signature, evidence_steps = classify(episode)
        final_state = episode["steps"][-1]["info"]["policy"]["metadata"]["state_before"]
        failures.append(
            {
                "episode_id": episode["episode_id"],
                "task_id": episode["task"]["task_id"],
                "task_type": episode["task"]["task_type"],
                "signature": signature,
                "evidence_step_indices": evidence_steps,
                "terminal_inventory": final_state.get("inventory"),
                "last_actions": [step["action"] for step in episode["steps"][-5:]],
            }
        )
    counts = Counter(item["signature"] for item in failures)
    by_task_type = Counter(item["task_type"] for item in failures)
    report = {
        "schema_version": 1,
        "source_root": args.episodes_root.as_posix(),
        "failure_count": len(failures),
        "signature_counts": dict(sorted(counts.items())),
        "failure_counts_by_task_type": dict(sorted(by_task_type.items())),
        "failures": failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
