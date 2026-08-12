"""Run and persist one complete random-policy ALFWorld episode."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from evomo.benchmarks.alfworld import discover_tasks
from evomo.data import EpisodeStore
from evomo.envs.alfworld_textworld import AlfworldTextEnvironment
from evomo.policies import RandomPolicy
from evomo.rollout import RolloutRunner


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
    parser.add_argument("--max-steps", type=int, default=50)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/episodes/random_baseline.jsonl"),
    )
    args = parser.parse_args()
    if not args.data_root:
        parser.error("--data-root is required when ALFWORLD_DATA is unset")
    if args.task_index < 0:
        parser.error("--task-index must be non-negative")
    if args.max_steps <= 0:
        parser.error("--max-steps must be positive")
    return args


def main() -> None:
    args = parse_args()
    discovered = discover_tasks(args.data_root, splits=[args.split])
    if args.task_index >= len(discovered.tasks):
        raise IndexError(
            f"task index {args.task_index} is out of range for "
            f"{len(discovered.tasks)} playable tasks"
        )
    task = discovered.tasks[args.task_index]
    store = EpisodeStore(args.output)
    episode = RolloutRunner(max_steps=args.max_steps).run_episode(
        task=task,
        environment=AlfworldTextEnvironment(args.data_root),
        policy=RandomPolicy(),
        seed=args.seed,
        store=store,
    )

    restored = list(EpisodeStore(args.output))[-1]
    if restored != episode:
        raise RuntimeError("persisted episode does not match the completed rollout")

    print(
        json.dumps(
            {
                "episode_id": episode.episode_id,
                "task_id": episode.task.task_id,
                "goal": episode.task.goal,
                "policy_id": episode.policy_id,
                "seed": episode.seed,
                "steps": len(episode.steps),
                "success": episode.success,
                "termination_reason": episode.termination_reason.value,
                "total_reward": episode.total_reward,
                "first_action": episode.steps[0].action if episode.steps else None,
                "last_action": episode.steps[-1].action if episode.steps else None,
                "output": str(args.output.resolve()),
                "round_trip_verified": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
