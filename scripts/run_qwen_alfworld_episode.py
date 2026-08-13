"""Run and persist one local-Qwen ALFWorld episode."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from evomo.benchmarks.alfworld import discover_tasks
from evomo.data import EpisodeStore
from evomo.envs.alfworld_textworld import AlfworldTextEnvironment
from evomo.evaluation import resolve_experience_selection
from evomo.policies import HuggingFaceQwenGenerator, PromptVariant, QwenPolicy
from evomo.rollout import RolloutRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        default=os.environ.get("ALFWORLD_DATA"),
        help="ALFWORLD_DATA directory or its json_2.1.1 child",
    )
    parser.add_argument("--model-path", type=Path, default=Path("../models/Qwen3-1.7B"))
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--split", default="valid_train")
    parser.add_argument("--task-index", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-steps", type=int, default=50)
    parser.add_argument("--max-new-tokens", type=int, default=16)
    parser.add_argument("--max-history-items", type=int, default=6)
    experience = parser.add_mutually_exclusive_group()
    experience.add_argument("--experience-file", type=Path)
    experience.add_argument("--experience-decision", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/episodes/qwen3_1.7b_baseline.jsonl"),
    )
    args = parser.parse_args()
    if not args.data_root:
        parser.error("--data-root is required when ALFWORLD_DATA is unset")
    if args.task_index < 0:
        parser.error("--task-index must be non-negative")
    if args.max_steps <= 0 or args.max_new_tokens <= 0:
        parser.error("--max-steps and --max-new-tokens must be positive")
    if args.max_history_items < 0:
        parser.error("--max-history-items must be non-negative")
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
    selection = (
        resolve_experience_selection(
            experience_path=args.experience_file,
            decision_path=args.experience_decision,
        )
        if args.experience_file or args.experience_decision
        else None
    )
    generator = HuggingFaceQwenGenerator(
        args.model_path,
        device=args.device,
        max_new_tokens=args.max_new_tokens,
    )
    policy = QwenPolicy(
        generator,
        policy_id=(
            "qwen3-1.7b-decision-selected-experience"
            if selection
            else "qwen3-1.7b-admissible-v1"
        ),
        max_history_items=args.max_history_items,
        prompt_variant=(
            PromptVariant.EXPERIENCE_GUIDED_ACTION
            if selection
            else PromptVariant.INDEX_BASELINE
        ),
        experiences=selection.experiences if selection else None,
        experience_provenance=selection.provenance if selection else None,
    )
    episode = RolloutRunner(max_steps=args.max_steps).run_episode(
        task=task,
        environment=AlfworldTextEnvironment(args.data_root),
        policy=policy,
        seed=args.seed,
        store=EpisodeStore(args.output),
        experience_version=(selection.experiences.version if selection else None),
        episode_metadata={
            "experience_selection": dict(selection.provenance)
        } if selection else None,
    )

    restored = list(EpisodeStore(args.output))[-1]
    if restored != episode:
        raise RuntimeError("persisted episode does not match the completed rollout")
    parse_successes = sum(
        bool(step.info["policy"]["metadata"]["parse_ok"]) for step in episode.steps
    )
    print(
        json.dumps(
            {
                "episode_id": episode.episode_id,
                "task_id": episode.task.task_id,
                "goal": episode.task.goal,
                "policy_id": episode.policy_id,
                "steps": len(episode.steps),
                "success": episode.success,
                "termination_reason": episode.termination_reason.value,
                "total_reward": episode.total_reward,
                "parsed_actions": parse_successes,
                "fallback_actions": len(episode.steps) - parse_successes,
                "output": str(args.output.resolve()),
                "round_trip_verified": True,
                "experience_selection": (
                    dict(selection.provenance) if selection else None
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
