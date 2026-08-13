from __future__ import annotations

import json
from pathlib import Path

import pytest

from evomo.evaluation import (
    audit_evaluation_ledger,
    task_ids_sha256,
)
from evomo.evaluation.evaluation_ledger import _commit_entry


def entry(cycle: str, tasks: list[str], *, status: str = "reserved") -> dict:
    return {
        "cycle_id": cycle,
        "exposure_order": 0,
        "status": status,
        "benchmark": "alfworld",
        "split": "valid_unseen",
        "task_types": ["pick_and_place_simple"],
        "task_count": len(tasks),
        "task_ids_sha256": task_ids_sha256(tasks),
        "task_ids": sorted(tasks),
        "prior_overlaps": [],
        "source": {"kind": "dataset_discovery_reservation"},
    }


def test_ledger_commit_is_idempotent_and_rejects_cross_cycle_overlap(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "ledger.json"
    first = entry("cycle-a", ["task-a", "task-b"])
    first["exposure_order"] = 1

    receipt = _commit_entry(first, ledger_path=ledger, receipt_path=tmp_path / "a.json")
    replay = _commit_entry(first, ledger_path=ledger, receipt_path=tmp_path / "a2.json")

    assert not receipt["idempotent_replay"]
    assert replay["idempotent_replay"]
    with pytest.raises(ValueError, match="overlap prior cycle"):
        _commit_entry(
            {**entry("cycle-b", ["task-b", "task-c"]), "exposure_order": 2},
            ledger_path=ledger,
            receipt_path=tmp_path / "b.json",
        )


def test_reservation_can_advance_to_completed_with_identical_scope(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "ledger.json"
    reserved = entry("cycle-a", ["task-a"])
    completed = entry("cycle-a", ["task-a"], status="completed")
    reserved["exposure_order"] = completed["exposure_order"] = 1
    completed["source"] = {"kind": "dataset_discovery_reservation"}
    _commit_entry(reserved, ledger_path=ledger, receipt_path=tmp_path / "reserve.json")

    receipt = _commit_entry(
        completed, ledger_path=ledger, receipt_path=tmp_path / "complete.json"
    )
    saved = json.loads(ledger.read_text(encoding="utf-8"))["entries"][0]

    assert receipt["commit_result"] == "reservation_completed"
    assert saved["status"] == "completed"
    assert saved["source"] == {"kind": "dataset_discovery_reservation"}


def test_completion_inherits_reservation_exposure_order(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    reserved = entry("cycle-a", ["task-a"])
    completed = entry("cycle-a", ["task-a"], status="completed")
    completed["source"] = {"kind": "dataset_discovery_reservation"}
    _commit_entry(reserved, ledger_path=ledger, receipt_path=tmp_path / "reserve.json")

    receipt = _commit_entry(
        completed, ledger_path=ledger, receipt_path=tmp_path / "complete.json"
    )

    assert receipt["exposure_order"] == 1
    assert receipt["commit_result"] == "reservation_completed"


def test_historical_overlap_requires_opt_in_and_is_audited(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    _commit_entry(
        {**entry("first", ["task-a", "task-b"]), "exposure_order": 1},
        ledger_path=ledger,
        receipt_path=tmp_path / "first.json",
    )
    repeated = entry("historical-repeat", ["task-a", "task-b"])
    repeated["exposure_order"] = 2
    _commit_entry(
        repeated,
        ledger_path=ledger,
        receipt_path=tmp_path / "repeat.json",
        allow_historical_overlap=True,
    )
    value = json.loads(ledger.read_text(encoding="utf-8"))
    audit = audit_evaluation_ledger(value, ledger_path=ledger)

    assert value["entries"][1]["prior_overlaps"] == [
        {
            "cycle_id": "first",
            "task_count": 2,
            "task_ids_sha256": task_ids_sha256(["task-a", "task-b"]),
        }
    ]
    assert audit["cycle_count"] == 2
    assert audit["exposed_task_count"] == 2
    assert audit["historical_overlap_task_count"] == 2
    assert audit["historical_overlap_event_count"] == 1
    assert audit["protocol_clean"] is False


def test_ledger_audit_rejects_forged_overlap_metadata(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    _commit_entry(
        {**entry("first", ["task-a"]), "exposure_order": 1},
        ledger_path=ledger,
        receipt_path=tmp_path / "first.json",
    )
    repeated = entry("second", ["task-a"])
    repeated["exposure_order"] = 2
    _commit_entry(
        repeated,
        ledger_path=ledger,
        receipt_path=tmp_path / "second.json",
        allow_historical_overlap=True,
    )
    value = json.loads(ledger.read_text(encoding="utf-8"))
    value["entries"][1]["prior_overlaps"][0]["task_count"] = 99
    ledger.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(ValueError, match="not reproducible"):
        audit_evaluation_ledger(value, ledger_path=ledger)


def test_legacy_audit_requires_full_coverage_evaluation_evidence(
    tmp_path: Path,
) -> None:
    from evomo.evaluation import register_audited_evaluation_report

    summary = {
        "variant": "I",
        "task_count": 1,
        "success_count": 1,
        "run": {
            "split": "valid_unseen",
            "selection_mode": "all_tasks",
            "task_types": ["pick_and_place_simple"],
            "task_ids": ["valid_unseen/task-a"],
        },
    }
    audit = {
        "status": "passed",
        "same_task_ids": True,
        "experience_evidence_task_overlap": 0,
        "excluded_source_task_overlap": 0,
        "discovery_task_count": 1,
        "variants": [{"variant": "I", "episode_count": 1, "success_count": 1}],
    }
    summary_path = tmp_path / "summary.json"
    audit_path = tmp_path / "audit.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    audit_path.write_text(json.dumps(audit), encoding="utf-8")

    register_audited_evaluation_report(
        ledger_path=tmp_path / "ledger.json",
        receipt_path=tmp_path / "receipt.json",
        cycle_id="legacy",
        validation_audit_path=audit_path,
        validation_summary_path=summary_path,
    )
    ledger = json.loads((tmp_path / "ledger.json").read_text())
    assert ledger["entries"][0]["source"]["audit_protocol"] == (
        "legacy_full_coverage_evaluation"
    )

    audit["discovery_task_count"] = 2
    audit_path.write_text(json.dumps(audit), encoding="utf-8")
    with pytest.raises(ValueError, match="lacks full-coverage"):
        register_audited_evaluation_report(
            ledger_path=tmp_path / "other-ledger.json",
            receipt_path=tmp_path / "other-receipt.json",
            cycle_id="bad-legacy",
            validation_audit_path=audit_path,
            validation_summary_path=summary_path,
        )


def test_checked_in_ledger_discloses_historical_unseen_reuse() -> None:
    repository = Path(__file__).resolve().parents[1]
    ledger_path = repository / "reports/evaluation_ledger/ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    audit = audit_evaluation_ledger(ledger, ledger_path=ledger_path)

    assert audit["cycle_count"] == 3
    assert audit["exposed_task_count"] == 274
    assert audit["historical_overlap_event_count"] == 1
    assert audit["historical_overlap_task_count"] == 134
    assert audit["verified_source_file_count"] == 8
    assert audit["replayed_completed_cycle_count"] == 1
    assert audit["protocol_clean"] is False
