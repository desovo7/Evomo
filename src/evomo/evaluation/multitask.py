"""Deterministic task sampling, resume checks, and multi-task aggregation."""

from __future__ import annotations

import json
import math
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
    offset: int = 0,
    task_types: tuple[str, ...] = CANONICAL_TASK_TYPES,
) -> tuple[TaskSpec, ...]:
    """Select the first stable task IDs for every requested task type."""

    if not isinstance(per_type, int) or isinstance(per_type, bool) or per_type <= 0:
        raise ValueError("per_type must be a positive integer")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise ValueError("offset must be a non-negative integer")
    grouped: dict[str, list[TaskSpec]] = {task_type: [] for task_type in task_types}
    for task in tasks:
        if task.task_type in grouped:
            grouped[task.task_type].append(task)

    selected: list[TaskSpec] = []
    for task_type in task_types:
        candidates = sorted(grouped[task_type], key=lambda task: task.task_id)
        if len(candidates) < offset + per_type:
            raise ValueError(
                f"task type {task_type!r} has {len(candidates)} tasks; "
                f"need {offset + per_type} for offset={offset}, per_type={per_type}"
            )
        selected.extend(candidates[offset : offset + per_type])
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
            "experience_overrides",
            "repeated_actions",
            "unchanged_observations",
            "unique_actions",
        )
    }
    task_types = sorted({row["task_type"] for row in rows})
    by_task_type = {}
    for task_type in task_types:
        type_rows = [row for row in rows if row["task_type"] == task_type]
        success_count = sum(int(row["success"]) for row in type_rows)
        by_task_type[task_type] = {
            "task_count": len(type_rows),
            "success_count": success_count,
            "success_rate": success_count / len(type_rows),
            "steps": sum(int(row["steps"]) for row in type_rows),
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
        "by_task_type": by_task_type,
        "tasks": rows,
    }


def merge_variant_summaries(shard_summaries: Iterable[dict]) -> dict:
    """Merge disjoint shards from one policy under an identical run contract."""

    shards = tuple(shard_summaries)
    if not shards:
        raise ValueError("at least one shard summary is required")
    variant = shards[0].get("variant")
    policy_id = shards[0].get("policy_id")
    invariant_keys = (
        "model_id",
        "split",
        "per_type",
        "task_offset",
        "seed",
        "max_steps",
        "max_new_tokens",
        "max_history_items",
        "experience_version",
        "experience_sha256",
    )
    reference_run = shards[0].get("run", {})
    task_ids: set[str] = set()
    task_types: set[str] = set()
    rows: list[dict] = []
    shard_descriptors = []
    for shard_index, shard in enumerate(shards):
        if shard.get("variant") != variant or shard.get("policy_id") != policy_id:
            raise ValueError("shards must use one variant and policy_id")
        run = shard.get("run", {})
        mismatched = [key for key in invariant_keys if run.get(key) != reference_run.get(key)]
        if mismatched:
            raise ValueError(f"shard run contracts differ for: {mismatched}")
        shard_types = tuple(run.get("task_types", ()))
        if not shard_types:
            raise ValueError("each shard run must declare task_types")
        overlap_types = task_types.intersection(shard_types)
        if overlap_types:
            raise ValueError(f"shard task types overlap: {sorted(overlap_types)}")
        task_types.update(shard_types)
        shard_rows = list(shard.get("tasks", ()))
        declared_ids = set(run.get("task_ids", ()))
        row_ids = {row["task_id"] for row in shard_rows}
        if declared_ids != row_ids:
            raise ValueError(f"shard {shard_index} task rows do not match run task_ids")
        overlap_ids = task_ids.intersection(row_ids)
        if overlap_ids:
            raise ValueError(f"duplicate task IDs across shards: {sorted(overlap_ids)}")
        task_ids.update(row_ids)
        rows.extend(shard_rows)
        shard_descriptors.append(
            {
                "shard_index": shard_index,
                "task_types": list(shard_types),
                "task_count": len(shard_rows),
            }
        )

    # Reconstruct lightweight EpisodeMetrics-compatible aggregation from task rows.
    task_count = len(rows)
    metric_keys = (
        "steps",
        "parsed_actions",
        "format_compliant_actions",
        "fallback_actions",
        "repaired_actions",
        "experience_overrides",
        "repeated_actions",
        "unchanged_observations",
        "unique_actions",
    )
    totals = {key: sum(int(row[key]) for row in rows) for key in metric_keys}
    by_task_type = {}
    for task_type in sorted(task_types):
        type_rows = [row for row in rows if row["task_type"] == task_type]
        success_count = sum(int(row["success"]) for row in type_rows)
        by_task_type[task_type] = {
            "task_count": len(type_rows),
            "success_count": success_count,
            "success_rate": success_count / len(type_rows),
            "steps": sum(int(row["steps"]) for row in type_rows),
        }
    success_count = sum(int(row["success"]) for row in rows)
    merged_run = {key: reference_run.get(key) for key in invariant_keys}
    merged_run.update(
        {
            "task_types": sorted(task_types),
            "task_ids": sorted(task_ids),
            "shard_count": len(shards),
            "shards": shard_descriptors,
        }
    )
    return {
        "variant": variant,
        "policy_id": policy_id,
        "task_count": task_count,
        "success_count": success_count,
        "success_rate": success_count / task_count,
        "totals": totals,
        "means": {
            "steps": totals["steps"] / task_count,
            "repeated_actions": totals["repeated_actions"] / task_count,
            "unchanged_observations": totals["unchanged_observations"] / task_count,
            "unique_actions": totals["unique_actions"] / task_count,
        },
        "by_task_type": by_task_type,
        "tasks": sorted(rows, key=lambda row: row["task_id"]),
        "run": merged_run,
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
        f"- Stable task offset: {comparison.get('task_offset', 0)}",
        "- Integrity audit: [`audit.json`](audit.json)",
    ]
    for summary in comparison["variants"]:
        version = summary.get("run", {}).get("experience_version")
        if version:
            lines.append(f"- Prompt {summary['variant']} experience: `{version}`")
    lines.extend(
        [
            "",
            "| Prompt | Success | Parsed actions | Repaired | Experience overrides | True fallback | Repeats | Unchanged obs |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for summary in comparison["variants"]:
        totals = summary["totals"]
        lines.append(
            f"| {summary['variant']} | {summary['success_count']}/{summary['task_count']} "
            f"({summary['success_rate']:.1%}) | {totals['parsed_actions']}/{totals['steps']} | "
            f"{totals.get('repaired_actions', 0)} | "
            f"{totals.get('experience_overrides', 0)} | {totals['fallback_actions']} | "
            f"{totals['repeated_actions']} | {totals['unchanged_observations']} |"
        )
    paired = comparison.get("paired_success")
    if paired:
        lines.extend(
            [
                "",
                "## Paired success analysis",
                "",
                f"- Baseline: `{paired['baseline']}`; candidate: `{paired['candidate']}`",
                f"- Candidate-only successes: {paired['overall']['candidate_only']}",
                f"- Baseline-only successes: {paired['overall']['baseline_only']}",
                f"- Exact paired p-value: {paired['overall']['exact_p_value']:.6g}",
                "- The exact p-value is a two-sided McNemar/binomial test over discordant task pairs.",
                "",
                "| Task type | Baseline only | Candidate only | Both succeed | Both fail | Success delta |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for task_type, item in paired["by_task_type"].items():
            lines.append(
                f"| {task_type} | {item['baseline_only']} | {item['candidate_only']} | "
                f"{item['both_success']} | {item['both_fail']} | {item['success_delta']:+d} |"
            )
    lines.extend(["", "## Per-task results", ""])
    for summary in comparison["variants"]:
        if summary.get("by_task_type"):
            lines.extend(
                [
                    f"### Prompt {summary['variant']} by task type",
                    "",
                    "| Task type | Success | Rate | Steps |",
                    "| --- | ---: | ---: | ---: |",
                ]
            )
            for task_type, item in summary["by_task_type"].items():
                lines.append(
                    f"| {task_type} | {item['success_count']}/{item['task_count']} | "
                    f"{item['success_rate']:.1%} | {item['steps']} |"
                )
            lines.append("")
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
    comparison = {
        "split": split,
        "per_type": per_type,
        "task_types": list(CANONICAL_TASK_TYPES),
        "task_count_per_variant": len(expected_task_ids),
        "variants": list(summaries),
    }
    if len(summaries) == 2:
        comparison["paired_success"] = build_paired_success_analysis(
            summaries[0], summaries[1]
        )
    return comparison


def _exact_paired_p_value(baseline_only: int, candidate_only: int) -> float:
    """Two-sided exact McNemar/binomial p-value for discordant pairs."""

    discordant = baseline_only + candidate_only
    if discordant == 0:
        return 1.0
    tail = sum(
        math.comb(discordant, k) for k in range(min(baseline_only, candidate_only) + 1)
    ) / (2**discordant)
    return min(1.0, 2 * tail)


def build_paired_success_analysis(baseline: dict, candidate: dict) -> dict:
    """Compare success on matching task IDs, overall and by task type."""

    baseline_rows = {row["task_id"]: row for row in baseline["tasks"]}
    candidate_rows = {row["task_id"]: row for row in candidate["tasks"]}
    if baseline_rows.keys() != candidate_rows.keys():
        raise ValueError("paired summaries do not cover identical task IDs")

    def aggregate(task_ids: Iterable[str]) -> dict:
        counts = {
            "task_count": 0,
            "both_success": 0,
            "baseline_only": 0,
            "candidate_only": 0,
            "both_fail": 0,
        }
        for task_id in task_ids:
            first = bool(baseline_rows[task_id]["success"])
            second = bool(candidate_rows[task_id]["success"])
            counts["task_count"] += 1
            if first and second:
                counts["both_success"] += 1
            elif first:
                counts["baseline_only"] += 1
            elif second:
                counts["candidate_only"] += 1
            else:
                counts["both_fail"] += 1
        counts["success_delta"] = counts["candidate_only"] - counts["baseline_only"]
        counts["exact_p_value"] = _exact_paired_p_value(
            counts["baseline_only"], counts["candidate_only"]
        )
        return counts

    by_task_type = {}
    for task_type in sorted({row["task_type"] for row in baseline_rows.values()}):
        type_ids = [
            task_id
            for task_id, row in baseline_rows.items()
            if row["task_type"] == task_type
        ]
        if any(candidate_rows[task_id]["task_type"] != task_type for task_id in type_ids):
            raise ValueError("paired task types differ")
        by_task_type[task_type] = aggregate(type_ids)
    return {
        "baseline": baseline["variant"],
        "candidate": candidate["variant"],
        "overall": aggregate(baseline_rows),
        "by_task_type": by_task_type,
    }
