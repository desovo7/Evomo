from __future__ import annotations

from pathlib import Path

import pytest

from evomo.evaluation import (
    TASK_TYPE_SHARDS,
    CycleExecutor,
    audit_cycle_executor_state,
    build_qwen_evolution_cycle_plan,
)


def build(tmp_path: Path) -> dict:
    return build_qwen_evolution_cycle_plan(
        cycle_id="live-cycle",
        report_root=tmp_path / "report",
        incumbent_experience="incumbent.json",
        candidate_version="candidate-v1",
        data_root="alfworld-data",
        model_path="models/qwen",
        python_executable="python",
        gpus=("0", "1", "2"),
        development_offset=2,
    )


def test_plan_covers_full_cycle_and_three_gpu_shards(tmp_path: Path) -> None:
    plan = build(tmp_path)
    stages = {stage["stage_id"]: stage for stage in plan["stages"]}

    assert len(stages) == 13
    assert TASK_TYPE_SHARDS == (
        ("look_at_obj_in_light", "pick_and_place_simple"),
        ("pick_clean_then_place_in_recep", "pick_cool_then_place_in_recep"),
        ("pick_heat_then_place_in_recep", "pick_two_obj_and_place"),
    )
    for stage_id in (
        "development_rollout",
        "incumbent_validation_rollout",
        "candidate_validation_rollout",
    ):
        jobs = stages[stage_id]["jobs"]
        assert len(jobs) == 3
        assert {job["env"]["CUDA_VISIBLE_DEVICES"] for job in jobs} == {
            "0",
            "1",
            "2",
        }
        assert all("--task-types" in job["argv"] for job in jobs)
    development_argv = stages["development_rollout"]["jobs"][0]["argv"]
    assert development_argv[development_argv.index("--task-offset") + 1] == "2"
    assert "--all-tasks" not in development_argv
    assert all(
        "--all-tasks" in job["argv"]
        for key in ("incumbent_validation_rollout", "candidate_validation_rollout")
        for job in stages[key]["jobs"]
    )
    CycleExecutor(plan, state_dir=tmp_path / "state")


def test_plan_keeps_learning_and_evaluation_splits_separate(tmp_path: Path) -> None:
    stages = {stage["stage_id"]: stage for stage in build(tmp_path)["stages"]}
    development = stages["development_rollout"]["jobs"][0]["argv"]
    validation = stages["candidate_validation_rollout"]["jobs"][0]["argv"]
    audit = stages["validation_postprocess"]["jobs"][1]["argv"]

    assert development[development.index("--split") + 1] == "valid_train"
    assert validation[validation.index("--split") + 1] == "valid_unseen"
    assert "--exclude-episodes-root" in audit
    assert "--protocol-role" in audit
    assert audit[audit.index("--protocol-role") + 1] == "evaluation"


def test_plan_rejects_duplicate_gpu_ids(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="three unique"):
        build_qwen_evolution_cycle_plan(
            cycle_id="bad",
            report_root=tmp_path,
            incumbent_experience="base.json",
            candidate_version="candidate",
            data_root="data",
            model_path="model",
            gpus=("0", "0", "1"),
        )


def test_checked_in_live_cycle_executed_and_resumed() -> None:
    repository = Path(__file__).resolve().parents[1]
    report = repository / "reports/live_cycle_offset2"
    audit = audit_cycle_executor_state(
        repository / "configs/live_cycle_offset2.json",
        state_dir=report / "executor",
    )
    import json

    development = json.loads(
        (report / "development/I/summary.json").read_text(encoding="utf-8")
    )
    incumbent = json.loads(
        (report / "validation/I/summary.json").read_text(encoding="utf-8")
    )
    candidate = json.loads(
        (report / "validation/K/summary.json").read_text(encoding="utf-8")
    )
    decision = json.loads((report / "decision.json").read_text(encoding="utf-8"))

    assert development["task_count"] == 6
    assert development["success_count"] == 3
    assert incumbent["success_count"] == 114
    assert candidate["success_count"] == 116
    assert candidate["totals"]["steps"] < incumbent["totals"]["steps"]
    assert decision["decision"] == "retain_candidate"
    assert decision["paired"]["baseline_only"] == 0
    assert decision["paired"]["candidate_only"] == 2
    assert audit["executed_stage_count"] == 13
    assert audit["job_count"] == 20
    assert audit["resume_run_count"] == 1
    assert audit["stage_recovery_event_count"] == 13
