from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from evomo.data import Episode, StepRecord, TaskSpec, TerminationReason
from evomo.evaluation import (
    CANONICAL_TASK_TYPES,
    build_cross_variant_comparison,
    ensure_run_config,
    load_completed_episode,
    persist_episode_artifacts,
    render_comparison_markdown,
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
