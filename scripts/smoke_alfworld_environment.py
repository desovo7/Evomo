"""Reset one real ALFWorld task and execute one admissible action."""

from __future__ import annotations

import argparse
import json
import os

from evomo.benchmarks.alfworld import discover_tasks
from evomo.envs.alfworld_textworld import AlfworldTextEnvironment


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        default=os.environ.get("ALFWORLD_DATA"),
        help="ALFWORLD_DATA directory or its json_2.1.1 child",
    )
    parser.add_argument("--split", default="valid_train")
    parser.add_argument("--task-index", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not args.data_root:
        parser.error("--data-root is required when ALFWORLD_DATA is unset")
    if args.task_index < 0:
        parser.error("--task-index must be non-negative")
    return args


def main() -> None:
    args = parse_args()
    result = discover_tasks(args.data_root, splits=[args.split])
    if args.task_index >= len(result.tasks):
        raise IndexError(
            f"task index {args.task_index} is out of range for "
            f"{len(result.tasks)} playable tasks"
        )
    task = result.tasks[args.task_index]

    with AlfworldTextEnvironment(args.data_root) as environment:
        reset = environment.reset(task, seed=args.seed)
        if not reset.admissible_actions:
            raise RuntimeError(f"task has no admissible actions after reset: {task.task_id}")
        action = reset.admissible_actions[0]
        transition = environment.step(action)

    output = {
        "task": {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "goal": task.goal,
            "game_file": task.game_file,
        },
        "reset": {
            "observation": reset.observation,
            "admissible_action_count": len(reset.admissible_actions),
            "admissible_action_sample": list(reset.admissible_actions[:5]),
        },
        "action": action,
        "step": {
            "observation": transition.observation,
            "reward": transition.reward,
            "terminated": transition.terminated,
            "success": transition.success,
            "admissible_action_count": len(transition.admissible_actions),
            "action_was_admissible": transition.info["action_was_admissible"],
        },
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
