"""Run A/B/C/D Qwen prompt variants sequentially on one ALFWorld task."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from evomo.benchmarks.alfworld import discover_tasks
from evomo.data import EpisodeStore
from evomo.envs.alfworld_textworld import AlfworldTextEnvironment
from evomo.evaluation import write_trajectory_logs
from evomo.policies import HuggingFaceQwenGenerator, PromptVariant, QwenPolicy
from evomo.rollout import RolloutRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("ALFWORLD_DATA"))
    parser.add_argument("--model-path", type=Path, default=Path("../models/Qwen3-1.7B"))
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--split", default="valid_train")
    parser.add_argument("--task-index", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--max-history-items", type=int, default=6)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/prompt_ablation/qwen3_1.7b_task0"),
    )
    args = parser.parse_args()
    if not args.data_root:
        parser.error("--data-root is required when ALFWORLD_DATA is unset")
    if args.task_index < 0 or args.max_steps <= 0 or args.max_new_tokens <= 0:
        parser.error("task-index must be non-negative and token/step limits positive")
    return args


def main() -> None:
    args = parse_args()
    tasks = discover_tasks(args.data_root, splits=[args.split]).tasks
    if args.task_index >= len(tasks):
        raise IndexError(f"task index {args.task_index} out of range for {len(tasks)} tasks")
    task = tasks[args.task_index]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    episode_store = EpisodeStore(args.output_dir / "episodes.jsonl")
    generator = HuggingFaceQwenGenerator(
        args.model_path,
        device=args.device,
        max_new_tokens=args.max_new_tokens,
    )

    variants = (
        ("A", PromptVariant.INDEX_BASELINE),
        ("B", PromptVariant.PLAN_THEN_INDEX),
        ("C", PromptVariant.THINK_THEN_ACTION_TEXT),
        ("D", PromptVariant.ANTI_LOOP_SKILL),
    )
    results = []
    for label, variant in variants:
        policy = QwenPolicy(
            generator,
            policy_id=f"qwen3-1.7b-{label.lower()}-{variant.value}",
            max_history_items=args.max_history_items,
            prompt_variant=variant,
        )
        episode = RolloutRunner(max_steps=args.max_steps).run_episode(
            task=task,
            environment=AlfworldTextEnvironment(args.data_root),
            policy=policy,
            seed=args.seed,
            store=episode_store,
        )
        metrics = write_trajectory_logs(episode, args.output_dir / f"{label}_{variant.value}")
        results.append(
            {
                "label": label,
                "variant": variant.value,
                "policy_id": episode.policy_id,
                "termination_reason": episode.termination_reason.value,
                **metrics.to_dict(),
            }
        )

    restored = episode_store.load_all()
    if len(restored) != len(variants):
        raise RuntimeError("episode JSONL round-trip count mismatch")
    comparison = {
        "task_id": task.task_id,
        "goal": task.goal,
        "model_path": str(args.model_path),
        "seed": args.seed,
        "max_steps": args.max_steps,
        "variants": results,
        "episode_round_trip_verified": True,
    }
    (args.output_dir / "comparison.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(comparison, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
