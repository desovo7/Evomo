from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from evomo.evaluation import (
    CycleExecutor,
    audit_cycle_executor_state,
    write_json,
)


def job(job_id: str, output: Path, value: str, *, returncode: int = 0) -> dict:
    source = (
        "from pathlib import Path; "
        f"Path({str(output)!r}).write_text({value!r}, encoding='utf-8'); "
        f"raise SystemExit({returncode})"
    )
    return {"job_id": job_id, "argv": [sys.executable, "-c", source]}


def config(tmp_path: Path) -> dict:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    third = tmp_path / "third.txt"
    merged = tmp_path / "merged.txt"
    return {
        "schema_version": 1,
        "cycle_id": "synthetic-cycle",
        "workspace": str(tmp_path),
        "max_parallel": 3,
        "stages": [
            {
                "stage_id": "parallel_rollout",
                "depends_on": [],
                "outputs": [str(first), str(second), str(third)],
                "jobs": [
                    job("gpu-0", first, "one"),
                    job("gpu-1", second, "two"),
                    job("gpu-2", third, "three"),
                ],
            },
            {
                "stage_id": "merge",
                "depends_on": ["parallel_rollout"],
                "outputs": [str(merged)],
                "jobs": [job("merge", merged, "complete")],
            },
        ],
    }


def test_executor_runs_parallel_jobs_then_recovers_without_rerunning(
    tmp_path: Path,
) -> None:
    value = config(tmp_path)
    config_path = tmp_path / "config.json"
    state_dir = tmp_path / "state"
    write_json(config_path, value)

    first = CycleExecutor(value, state_dir=state_dir).run()
    first_events = (state_dir / "events.jsonl").read_text(encoding="utf-8")
    second = CycleExecutor(value, state_dir=state_dir).run()
    audit = audit_cycle_executor_state(config_path, state_dir=state_dir)

    assert first["status"] == second["status"] == "complete"
    assert all(
        stage["completion_mode"] == "executed"
        for stage in second["stages"].values()
    )
    assert len(second["stages"]["parallel_rollout"]["jobs"]) == 3
    assert audit["status"] == "passed"
    assert audit["executed_stage_count"] == 2
    assert audit["job_count"] == 4
    later_events = (state_dir / "events.jsonl").read_text(encoding="utf-8")
    assert later_events.startswith(first_events)
    assert later_events.count('"event":"stage_recovered"') == 2


def test_executor_rejects_config_change_after_state_exists(tmp_path: Path) -> None:
    value = config(tmp_path)
    state_dir = tmp_path / "state"
    CycleExecutor(value, state_dir=state_dir).run()
    changed = deepcopy(value)
    changed["max_parallel"] = 1

    with pytest.raises(ValueError, match="differs from immutable saved state"):
        CycleExecutor(changed, state_dir=state_dir).run()


def test_executor_persists_failure_and_does_not_complete_stage(tmp_path: Path) -> None:
    output = tmp_path / "failed.txt"
    value = {
        "schema_version": 1,
        "cycle_id": "failed-cycle",
        "workspace": str(tmp_path),
        "max_parallel": 1,
        "stages": [
            {
                "stage_id": "fails",
                "depends_on": [],
                "outputs": [str(output)],
                "jobs": [job("failure", output, "partial", returncode=7)],
            }
        ],
    }
    state_dir = tmp_path / "state"

    with pytest.raises(RuntimeError, match="jobs failed"):
        CycleExecutor(value, state_dir=state_dir).run()

    state = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
    assert state["status"] == "failed"
    assert state["stages"] == {}
    events = (state_dir / "events.jsonl").read_text(encoding="utf-8")
    assert '"event":"run_failed"' in events


def test_executor_validates_dependency_order_and_gpu_bound() -> None:
    with pytest.raises(ValueError, match="1 to 3"):
        CycleExecutor(
            {
                "schema_version": 1,
                "cycle_id": "bad",
                "max_parallel": 4,
                "stages": [],
            },
            state_dir="unused",
        )


def test_audit_detects_job_log_tampering(tmp_path: Path) -> None:
    value = config(tmp_path)
    config_path = tmp_path / "config.json"
    state_dir = tmp_path / "state"
    write_json(config_path, value)
    state = CycleExecutor(value, state_dir=state_dir).run()
    log_path = Path(state["stages"]["merge"]["jobs"][0]["log_path"])
    log_path.write_text("tampered", encoding="utf-8")

    with pytest.raises(ValueError, match="job log hash mismatch"):
        audit_cycle_executor_state(config_path, state_dir=state_dir)


def test_executor_detects_event_chain_tampering_before_resume(tmp_path: Path) -> None:
    value = config(tmp_path)
    state_dir = tmp_path / "state"
    CycleExecutor(value, state_dir=state_dir).run()
    events_path = state_dir / "events.jsonl"
    events = events_path.read_text(encoding="utf-8").splitlines()
    altered = json.loads(events[1])
    altered["event"] = "tampered"
    events[1] = json.dumps(altered, separators=(",", ":"))
    events_path.write_text("\n".join(events) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="event digest mismatch"):
        CycleExecutor(value, state_dir=state_dir).run()
