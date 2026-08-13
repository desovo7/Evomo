"""Deterministic task sampling, resume checks, and multi-task aggregation."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Iterable

from evomo.data import Episode, EpisodeStore, TaskSpec
from evomo.evaluation.trajectory_log import compute_episode_metrics, write_trajectory_logs

CANONICAL_TASK_TYPES = (
    "look_at_obj_in_light",
    "pick_and_place_simple",
    "pick_clean_then_place_in_recep",
    "pick_cool_then_place_in_recep",
    "pick_heat_then_place_in_recep",
    "pick_two_obj_and_place",
)


def select_tasks_by_type(
    tasks: Iterable[TaskSpec],
    *,
    per_type: int = 1,
    task_types: tuple[str, ...] = CANONICAL_TASK_TYPES,
) -> tuple[TaskSpec, ...]:
    """Select the first stable task IDs for every requested task type."""

    if not isinstance(per_type, int) or isinstance(per_type, bool) or per_type <= 0:
        raise ValueError("per_type must be a positive integer")
    grouped: dict[str, list[TaskSpec]] = {task_type: [] for task_type in task_types}
    for task in tasks:
        if task.task_type in grouped:
            grouped[task.task_type].append(task)

    selected: list[TaskSpec] = []
    for task_type in task_types:
        candidates = sorted(grouped[task_type], key=lambda task: task.task_id)
        if len(candidates) < per_type:
            raise ValueError(
                f"task type {task_type!r} has {len(candidates)} tasks; need {per_type}"
            )
        selected.extend(candidates[:per_type])
    return tuple(selected)


def load_completed_episode(
    task_directory: str | Path,
    *,
    expected_task: TaskSpec,
    expected_policy_id: str,
) -> Episode | None:
    """Return a fully logged episode, or None when no artifacts exist."""

    task_directory = Path(task_directory)
    required_paths = (
        task_directory / "episode.jsonl",
        task_directory / "summary.json",
        task_directory / "steps.jsonl",
        task_directory / "trajectory.md",
    )
    existing = [path.exists() for path in required_paths]
    if not any(existing):
        return None
    if not all(existing):
        missing = [str(path) for path, present in zip(required_paths, existing) if not present]
        raise RuntimeError(
            f"incomplete task artifacts under {task_directory}; missing: {missing}"
        )

    episodes = EpisodeStore(required_paths[0]).load_all()
    if len(episodes) != 1:
        raise RuntimeError(f"expected one episode in {required_paths[0]}, got {len(episodes)}")
    episode = episodes[0]
    if episode.task.task_id != expected_task.task_id:
        raise RuntimeError("completed episode task does not match requested task")
    if episode.policy_id != expected_policy_id:
        raise RuntimeError("completed episode policy does not match requested policy")
    step_lines = sum(1 for line in required_paths[2].open(encoding="utf-8") if line.strip())
    if step_lines != len(episode.steps):
        raise RuntimeError("step log count does not match persisted episode")
    return episode


def summarize_variant(
    *,
    variant: str,
    policy_id: str,
    episodes: Iterable[Episode],
) -> dict:
    episodes = tuple(episodes)
    if not episodes:
        raise ValueError("cannot summarize an empty episode collection")
    task_ids = [episode.task.task_id for episode in episodes]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("variant summary contains duplicate task IDs")

    rows = []
    for episode in episodes:
        metrics = compute_episode_metrics(episode)
        rows.append(
            {
                "task_id": episode.task.task_id,
                "task_type": episode.task.task_type,
                "goal": episode.task.goal,
                "termination_reason": episode.termination_reason.value,
                **metrics.to_dict(),
            }
        )
    task_count = len(rows)
    totals = {
        key: sum(int(row[key]) for row in rows)
        for key in (
            "steps",
            "parsed_actions",
            "format_compliant_actions",
            "fallback_actions",
            "repaired_actions",
            "repeated_actions",
            "unchanged_observations",
            "unique_actions",
        )
    }
    return {
        "variant": variant,
        "policy_id": policy_id,
        "task_count": task_count,
        "success_count": sum(int(row["success"]) for row in rows),
        "success_rate": sum(int(row["success"]) for row in rows) / task_count,
        "totals": totals,
        "means": {
            "steps": totals["steps"] / task_count,
            "repeated_actions": totals["repeated_actions"] / task_count,
            "unchanged_observations": totals["unchanged_observations"] / task_count,
            "unique_actions": totals["unique_actions"] / task_count,
        },
        "tasks": rows,
    }


def write_json(path: str | Path, value: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def ensure_run_config(path: str | Path, expected: dict) -> None:
    """Create an immutable run contract or verify an existing one exactly."""

    path = Path(path)
    if path.exists():
        try:
            actual = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"cannot read run config {path}: {exc}") from exc
        if actual != expected:
            raise RuntimeError(
                f"run config mismatch for {path}; use a new output directory"
            )
        return
    write_json(path, expected)


def persist_episode_artifacts(episode: Episode, task_directory: str | Path) -> None:
    """Publish a complete task artifact directory with one atomic rename."""

    task_directory = Path(task_directory)
    task_directory.parent.mkdir(parents=True, exist_ok=True)
    if task_directory.exists():
        raise FileExistsError(f"task artifact directory already exists: {task_directory}")
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{task_directory.name}.", dir=task_directory.parent)
    )
    try:
        EpisodeStore(temporary / "episode.jsonl").append(episode, durable=True)
        write_trajectory_logs(episode, temporary)
        temporary.replace(task_directory)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def render_comparison_markdown(comparison: dict) -> str:
    """Render the compact cross-prompt table kept next to machine-readable logs."""

    lines = [
        "# Qwen3-1.7B ALFWorld multi-task prompt comparison",
        "",
        f"- Split: `{comparison['split']}`",
        f"- Tasks per prompt: {comparison['task_count_per_variant']}",
        f"- Samples per task type: {comparison['per_type']}",
        "",
        "| Prompt | Success | Parsed actions | Repaired | True fallback | Repeats | Unchanged obs |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for summary in comparison["variants"]:
        totals = summary["totals"]
        lines.append(
            f"| {summary['variant']} | {summary['success_count']}/{summary['task_count']} "
            f"({summary['success_rate']:.1%}) | {totals['parsed_actions']}/{totals['steps']} | "
            f"{totals.get('repaired_actions', 0)} | {totals['fallback_actions']} | "
            f"{totals['repeated_actions']} | {totals['unchanged_observations']} |"
        )
    lines.extend(["", "## Per-task results", ""])
    for summary in comparison["variants"]:
        lines.extend(
            [
                f"### Prompt {summary['variant']}",
                "",
                "| Task type | Success | Steps | Repeats | Unique actions |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in summary["tasks"]:
            lines.append(
                f"| {row['task_type']} | {row['success']} | {row['steps']} | "
                f"{row['repeated_actions']} | {row['unique_actions']} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_cross_variant_comparison(
    variant_summaries: Iterable[dict],
    *,
    split: str,
    per_type: int,
) -> dict:
    summaries = tuple(variant_summaries)
    if not summaries:
        raise ValueError("at least one variant summary is required")
    expected_task_ids = {row["task_id"] for row in summaries[0]["tasks"]}
    for summary in summaries[1:]:
        if {row["task_id"] for row in summary["tasks"]} != expected_task_ids:
            raise ValueError("variant summaries do not cover identical task IDs")
    return {
        "split": split,
        "per_type": per_type,
        "task_types": list(CANONICAL_TASK_TYPES),
        "task_count_per_variant": len(expected_task_ids),
        "variants": list(summaries),
    }
