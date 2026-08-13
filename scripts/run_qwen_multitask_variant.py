"""Run one Qwen prompt variant over stable samples from all ALFWorld task types."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from evomo.benchmarks.alfworld import discover_tasks
from evomo.envs.alfworld_textworld import AlfworldTextEnvironment
from evomo.evaluation import (
    ensure_run_config,
    load_completed_episode,
    persist_episode_artifacts,
    select_tasks_by_type,
    summarize_variant,
    write_json,
)
from evomo.policies import HuggingFaceQwenGenerator, PromptVariant, QwenPolicy
from evomo.rollout import RolloutRunner

VARIANTS = {
    "B": PromptVariant.PLAN_THEN_INDEX,
    "C": PromptVariant.THINK_THEN_ACTION_TEXT,
    "D": PromptVariant.ANTI_LOOP_SKILL,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("ALFWORLD_DATA"))
    parser.add_argument("--model-path", type=Path, default=Path("../models/Qwen3-1.7B"))
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--split", default="valid_train")
    parser.add_argument("--per-type", type=int, default=1)
    parser.add_argument("--variant", choices=tuple(VARIANTS), required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--max-history-items", type=int, default=6)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.data_root:
        parser.error("--data-root is required when ALFWORLD_DATA is unset")
    if args.per_type <= 0 or args.max_steps <= 0 or args.max_new_tokens <= 0:
        parser.error("per-type, max-steps, and max-new-tokens must be positive")
    if args.max_history_items < 0:
        parser.error("max-history-items must be non-negative")
    return args


def main() -> None:
    args = parse_args()
    prompt_variant = VARIANTS[args.variant]
    policy_id = f"qwen3-1.7b-{args.variant.lower()}-{prompt_variant.value}"
    selected = select_tasks_by_type(
        discover_tasks(args.data_root, splits=[args.split]).tasks,
        per_type=args.per_type,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run_config = {
        "variant": args.variant,
        "prompt_variant": prompt_variant.value,
        "policy_id": policy_id,
        "model_id": args.model_path.name,
        "split": args.split,
        "per_type": args.per_type,
        "seed": args.seed,
        "max_steps": args.max_steps,
        "max_new_tokens": args.max_new_tokens,
        "max_history_items": args.max_history_items,
        "task_ids": [task.task_id for task in selected],
    }
    ensure_run_config(args.output_dir / "run_config.json", run_config)

    completed = []
    pending = []
    type_ordinals: dict[str, int] = {}
    for task_index, task in enumerate(selected):
        ordinal = type_ordinals.get(task.task_type, 0)
        type_ordinals[task.task_type] = ordinal + 1
        task_directory = args.output_dir / f"{task.task_type}_{ordinal:02d}"
        restored = load_completed_episode(
            task_directory,
            expected_task=task,
            expected_policy_id=policy_id,
        )
        if restored is None:
            pending.append((task_index, task, task_directory))
        else:
            completed.append((task_index, restored))
            print(f"[resume] {args.variant} {task.task_type} {task.task_id}", flush=True)

    generator = None
    if pending:
        generator = HuggingFaceQwenGenerator(
            args.model_path,
            device=args.device,
            max_new_tokens=args.max_new_tokens,
        )
    for task_index, task, task_directory in pending:
        assert generator is not None
        policy = QwenPolicy(
            generator,
            policy_id=policy_id,
            max_history_items=args.max_history_items,
            prompt_variant=prompt_variant,
        )
        print(f"[run] {args.variant} {task.task_type} {task.task_id}", flush=True)
        episode = RolloutRunner(max_steps=args.max_steps).run_episode(
            task=task,
            environment=AlfworldTextEnvironment(args.data_root),
            policy=policy,
            seed=args.seed + task_index,
        )
        persist_episode_artifacts(episode, task_directory)
        completed.append((task_index, episode))
        print(
            f"[done] {args.variant} {task.task_type} success={episode.success} "
            f"steps={len(episode.steps)}",
            flush=True,
        )

    episodes = [episode for _, episode in sorted(completed)]
    summary = summarize_variant(variant=args.variant, policy_id=policy_id, episodes=episodes)
    summary["run"] = run_config
    write_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
