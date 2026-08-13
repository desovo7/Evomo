from __future__ import annotations

import json
import importlib.util
from dataclasses import replace
from pathlib import Path

import pytest

from evomo.data import Episode, StepRecord, TaskSpec, TerminationReason
from evomo.evaluation import (
    CANONICAL_TASK_TYPES,
    build_cross_variant_comparison,
    build_paired_success_analysis,
    ensure_run_config,
    load_completed_episode,
    merge_variant_summaries,
    persist_episode_artifacts,
    render_comparison_markdown,
    select_all_tasks_by_type,
    select_tasks_by_type,
    summarize_variant,
)


def make_task(task_type: str, suffix: str) -> TaskSpec:
    return TaskSpec(
        task_id=f"valid_train/{task_type}/{suffix}",
        split="valid_train",
        task_type=task_type,
        goal=f"goal {suffix}",
    )


def make_episode(task: TaskSpec, *, policy_id: str = "policy-b", success: bool = False) -> Episode:
    step = StepRecord(
        step_index=0,
        observation="room",
        admissible_actions=("look", "go north"),
        action="look",
        next_observation="room",
        reward=1.0 if success else 0.0,
        terminated=success,
        info={
            "success": success,
            "policy": {
                "metadata": {
                    "raw_response": "<action>0</action>",
                    "parse_ok": True,
                    "required_format_ok": True,
                    "parse_format": "tagged_index",
                }
            },
        },
    )
    return Episode(
        episode_id=f"episode-{task.task_type}",
        task=task,
        policy_id=policy_id,
        seed=42,
        started_at="2026-01-01T00:00:00+00:00",
        ended_at="2026-01-01T00:00:01+00:00",
        initial_observation="room",
        steps=(step,),
        success=success,
        termination_reason=(TerminationReason.SUCCESS if success else TerminationReason.MAX_STEPS),
        total_reward=step.reward,
    )


def test_select_tasks_by_type_is_stable_and_canonical() -> None:
    tasks = []
    for task_type in reversed(CANONICAL_TASK_TYPES):
        tasks.extend((make_task(task_type, "z"), make_task(task_type, "a")))

    selected = select_tasks_by_type(reversed(tasks), per_type=1)

    assert [task.task_type for task in selected] == list(CANONICAL_TASK_TYPES)
    assert all(task.task_id.endswith("/a") for task in selected)

    held_out = select_tasks_by_type(reversed(tasks), per_type=1, offset=1)
    assert all(task.task_id.endswith("/z") for task in held_out)


def test_select_tasks_by_type_rejects_missing_category() -> None:
    tasks = [make_task(task_type, "a") for task_type in CANONICAL_TASK_TYPES[:-1]]
    with pytest.raises(ValueError, match="has 0 tasks"):
        select_tasks_by_type(tasks)


def test_select_tasks_by_type_validates_offset() -> None:
    tasks = [make_task(task_type, "a") for task_type in CANONICAL_TASK_TYPES]
    with pytest.raises(ValueError, match="offset=1"):
        select_tasks_by_type(tasks, offset=1)


def test_select_all_tasks_by_type_is_complete_stable_and_scoped() -> None:
    tasks = [
        make_task(CANONICAL_TASK_TYPES[0], "z"),
        make_task(CANONICAL_TASK_TYPES[1], "b"),
        make_task(CANONICAL_TASK_TYPES[0], "a"),
        make_task(CANONICAL_TASK_TYPES[1], "a"),
    ]

    selected = select_all_tasks_by_type(
        reversed(tasks), task_types=tuple(CANONICAL_TASK_TYPES[:2])
    )

    assert [task.task_id.rsplit("/", 1)[-1] for task in selected] == ["a", "z", "a", "b"]
    assert [task.task_type for task in selected] == [
        CANONICAL_TASK_TYPES[0],
        CANONICAL_TASK_TYPES[0],
        CANONICAL_TASK_TYPES[1],
        CANONICAL_TASK_TYPES[1],
    ]


def test_select_all_tasks_rejects_empty_or_duplicate_types() -> None:
    task = make_task(CANONICAL_TASK_TYPES[0], "a")
    with pytest.raises(ValueError, match="non-empty and unique"):
        select_all_tasks_by_type([task], task_types=())
    with pytest.raises(ValueError, match="non-empty and unique"):
        select_all_tasks_by_type(
            [task], task_types=(CANONICAL_TASK_TYPES[0], CANONICAL_TASK_TYPES[0])
        )


def test_atomic_persistence_round_trip_and_resume(tmp_path: Path) -> None:
    task = make_task(CANONICAL_TASK_TYPES[0], "a")
    episode = make_episode(task)
    directory = tmp_path / "task"

    persist_episode_artifacts(episode, directory)
    restored = load_completed_episode(
        directory,
        expected_task=task,
        expected_policy_id=episode.policy_id,
    )

    assert restored == episode
    assert sorted(path.name for path in directory.iterdir()) == [
        "episode.jsonl",
        "steps.jsonl",
        "summary.json",
        "trajectory.md",
    ]
    with pytest.raises(FileExistsError):
        persist_episode_artifacts(episode, directory)


def test_resume_rejects_incomplete_artifacts(tmp_path: Path) -> None:
    task = make_task(CANONICAL_TASK_TYPES[0], "a")
    directory = tmp_path / "task"
    directory.mkdir()
    (directory / "summary.json").write_text("{}", encoding="utf-8")

    with pytest.raises(RuntimeError, match="incomplete task artifacts"):
        load_completed_episode(
            directory,
            expected_task=task,
            expected_policy_id="policy-b",
        )


def test_run_config_is_immutable(tmp_path: Path) -> None:
    path = tmp_path / "run_config.json"
    config = {"variant": "B", "max_steps": 30, "task_ids": ["task-a"]}

    ensure_run_config(path, config)
    ensure_run_config(path, json.loads(json.dumps(config)))

    with pytest.raises(RuntimeError, match="run config mismatch"):
        ensure_run_config(path, {**config, "max_steps": 50})


def test_merge_accepts_overlapping_types_for_frozen_manifest_shards() -> None:
    task_a = make_task(CANONICAL_TASK_TYPES[0], "a")
    task_b = make_task(CANONICAL_TASK_TYPES[0], "b")
    summaries = []
    for index, task in enumerate((task_a, task_b)):
        summary = summarize_variant(
            variant="I", policy_id="policy-i", episodes=[make_episode(task, policy_id="policy-i")]
        )
        summary["run"] = {
            "model_id": "Qwen3-1.7B",
            "split": "valid_train",
            "selection_mode": "frozen_manifest_shard",
            "per_type": None,
            "task_offset": 0,
            "seed": 42,
            "max_steps": 30,
            "max_new_tokens": 96,
            "max_history_items": 6,
            "experience_version": "exp-v3",
            "experience_sha256": "abc",
            "experience_selection": {},
            "task_manifest": "pool.jsonl",
            "task_manifest_sha256": "def",
            "task_shard_index": index,
            "task_shard_count": 2,
            "task_types": [CANONICAL_TASK_TYPES[0]],
            "task_ids": [task.task_id],
        }
        summaries.append(summary)

    merged = merge_variant_summaries(summaries)

    assert merged["task_count"] == 2
    assert merged["run"]["task_shard_index"] is None
    assert merged["run"]["task_shard_count"] == 2


def test_variant_and_cross_variant_aggregation() -> None:
    tasks = [make_task(task_type, "a") for task_type in CANONICAL_TASK_TYPES]
    episodes = [make_episode(task, success=index == 0) for index, task in enumerate(tasks)]
    summary_b = summarize_variant(variant="B", policy_id="policy-b", episodes=episodes)
    summary_c = json.loads(json.dumps(summary_b))
    summary_c["variant"] = "C"
    summary_c["policy_id"] = "policy-c"

    comparison = build_cross_variant_comparison(
        [summary_b, summary_c], split="valid_train", per_type=1
    )
    markdown = render_comparison_markdown(comparison)

    assert summary_b["success_count"] == 1
    assert summary_b["totals"]["steps"] == 6
    assert comparison["task_count_per_variant"] == 6
    assert "| B | 1/6 (16.7%) |" in markdown


def test_cross_variant_aggregation_requires_same_tasks() -> None:
    task = make_task(CANONICAL_TASK_TYPES[0], "a")
    summary_b = summarize_variant(variant="B", policy_id="policy-b", episodes=[make_episode(task)])
    other = replace(task, task_id=task.task_id + "-other")
    summary_c = summarize_variant(
        variant="C", policy_id="policy-c", episodes=[make_episode(other, policy_id="policy-c")]
    )
    with pytest.raises(ValueError, match="identical task IDs"):
        build_cross_variant_comparison([summary_b, summary_c], split="valid_train", per_type=1)


def test_paired_success_analysis_counts_gains_and_regressions() -> None:
    tasks = [make_task(CANONICAL_TASK_TYPES[0], suffix) for suffix in ("a", "b", "c", "d")]
    baseline = summarize_variant(
        variant="F",
        policy_id="policy-f",
        episodes=[make_episode(task, success=index in (0, 1)) for index, task in enumerate(tasks)],
    )
    candidate = summarize_variant(
        variant="H",
        policy_id="policy-h",
        episodes=[make_episode(task, policy_id="policy-h", success=index in (1, 2, 3)) for index, task in enumerate(tasks)],
    )

    paired = build_paired_success_analysis(baseline, candidate)

    assert paired["overall"] == {
        "task_count": 4,
        "both_success": 1,
        "baseline_only": 1,
        "candidate_only": 2,
        "both_fail": 0,
        "success_delta": 1,
        "exact_p_value": 1.0,
    }


def test_three_variant_comparison_contains_every_pair() -> None:
    tasks = [make_task(CANONICAL_TASK_TYPES[0], suffix) for suffix in ("a", "b")]
    summaries = []
    for variant, successes in (("H", (0,)), ("I", (1,)), ("J", (0, 1))):
        summaries.append(
            summarize_variant(
                variant=variant,
                policy_id=f"policy-{variant.lower()}",
                episodes=[
                    make_episode(
                        task,
                        policy_id=f"policy-{variant.lower()}",
                        success=index in successes,
                    )
                    for index, task in enumerate(tasks)
                ],
            )
        )

    comparison = build_cross_variant_comparison(
        summaries, split="valid_unseen", per_type=2
    )

    assert [
        (item["baseline"], item["candidate"])
        for item in comparison["pairwise_success"]
    ] == [("H", "I"), ("H", "J"), ("I", "J")]


def make_shard_summary(task_types: tuple[str, ...], shard_index: int) -> dict:
    episodes = [
        make_episode(
            make_task(task_type, f"{shard_index}-{ordinal}"),
            policy_id="policy-h",
            success=ordinal == 0,
        )
        for task_type in task_types
        for ordinal in range(2)
    ]
    summary = summarize_variant(variant="H", policy_id="policy-h", episodes=episodes)
    summary["run"] = {
        "model_id": "Qwen3-1.7B",
        "split": "valid_train",
        "per_type": 2,
        "task_offset": 2,
        "seed": 42,
        "max_steps": 30,
        "max_new_tokens": 96,
        "max_history_items": 6,
        "experience_version": "exp-v2",
        "experience_sha256": "abc",
        "task_types": list(task_types),
        "task_ids": [episode.task.task_id for episode in episodes],
    }
    return summary


def test_merge_variant_summaries_combines_disjoint_shards() -> None:
    shards = [
        make_shard_summary(tuple(CANONICAL_TASK_TYPES[index : index + 2]), index // 2)
        for index in range(0, 6, 2)
    ]

    merged = merge_variant_summaries(shards)

    assert merged["task_count"] == 12
    assert merged["success_count"] == 6
    assert merged["run"]["shard_count"] == 3
    assert merged["run"]["task_types"] == sorted(CANONICAL_TASK_TYPES)
    assert len(merged["run"]["task_ids"]) == 12
    assert all(item["task_count"] == 2 for item in merged["by_task_type"].values())


def test_merge_variant_summaries_rejects_contract_mismatch() -> None:
    first = make_shard_summary(tuple(CANONICAL_TASK_TYPES[:2]), 0)
    second = make_shard_summary(tuple(CANONICAL_TASK_TYPES[2:4]), 1)
    second["run"]["max_steps"] = 50

    with pytest.raises(ValueError, match="max_steps"):
        merge_variant_summaries([first, second])


def test_merge_variant_summaries_rejects_overlapping_types_and_bad_rows() -> None:
    first = make_shard_summary(tuple(CANONICAL_TASK_TYPES[:2]), 0)
    overlap = make_shard_summary(tuple(CANONICAL_TASK_TYPES[1:3]), 1)
    with pytest.raises(ValueError, match="overlap"):
        merge_variant_summaries([first, overlap])

    second = make_shard_summary(tuple(CANONICAL_TASK_TYPES[2:4]), 1)
    second["run"]["task_ids"].pop()
    with pytest.raises(ValueError, match="task rows"):
        merge_variant_summaries([first, second])


def test_audit_episode_discovery_supports_direct_and_sharded_layouts(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "audit_multitask_report",
        Path(__file__).parents[1] / "scripts" / "audit_multitask_report.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    direct = tmp_path / "direct" / "task_00"
    direct.mkdir(parents=True)
    (direct / "episode.jsonl").write_text("{}\n", encoding="utf-8")
    assert module.find_episode_paths(tmp_path / "direct") == [direct / "episode.jsonl"]

    sharded = tmp_path / "sharded" / "shard_0" / "task_00"
    sharded.mkdir(parents=True)
    (sharded / "episode.jsonl").write_text("{}\n", encoding="utf-8")
    assert module.find_episode_paths(tmp_path / "sharded") == [sharded / "episode.jsonl"]

    mixed = tmp_path / "mixed"
    (mixed / "task_00").mkdir(parents=True)
    (mixed / "task_00" / "episode.jsonl").write_text("{}\n", encoding="utf-8")
    (mixed / "shard_0" / "task_01").mkdir(parents=True)
    (mixed / "shard_0" / "task_01" / "episode.jsonl").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mixed direct and sharded"):
        module.find_episode_paths(mixed)
