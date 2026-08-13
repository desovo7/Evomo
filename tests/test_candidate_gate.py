from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from evomo.evaluation import (
    audit_experience_candidate_decision,
    decide_experience_candidate,
    file_sha256,
)
from evomo.experience import ExperienceSet, save_experience_set


def gate_inputs(tmp_path: Path, *, baseline_only: int, candidate_only: int, p: float):
    incumbent = ExperienceSet("exp-v3", "policy-h", (), ())
    candidate = ExperienceSet(
        "exp-v4", "policy-i", (), (), parent_version=incumbent.version
    )
    incumbent_path = tmp_path / "incumbent.json"
    candidate_path = tmp_path / "candidate.json"
    save_experience_set(incumbent, incumbent_path)
    save_experience_set(candidate, candidate_path)
    task_count = 20
    delta = candidate_only - baseline_only
    comparison = {
        "split": "valid_seen",
        "task_count_per_variant": task_count,
        "variants": [
            {
                "variant": "I",
                "success_count": 10,
                "totals": {"steps": 200},
                "run": {
                    "experience_version": incumbent.version,
                    "experience_sha256": file_sha256(incumbent_path),
                },
            },
            {
                "variant": "K",
                "success_count": 10 + delta,
                "totals": {"steps": 180},
                "run": {
                    "experience_version": candidate.version,
                    "experience_sha256": file_sha256(candidate_path),
                },
            },
        ],
        "paired_success": {
            "baseline": "I",
            "candidate": "K",
            "overall": {
                "task_count": task_count,
                "both_success": 10 - baseline_only,
                "baseline_only": baseline_only,
                "candidate_only": candidate_only,
                "both_fail": task_count - 10 - candidate_only,
                "success_delta": delta,
                "exact_p_value": p,
            },
            "by_task_type": {},
        },
    }
    validation_audit = {
        "status": "passed",
        "protocol_role": "evaluation",
        "experience_evidence_task_overlap": 0,
        "excluded_source_task_overlap": 0,
        "discovery_task_count": task_count,
        "variants": [
            {"variant": "I", "episode_count": task_count, "success_count": 10},
            {
                "variant": "K",
                "episode_count": task_count,
                "success_count": 10 + delta,
            },
        ],
    }
    evolution_audit = {
        "status": "passed",
        "base_version": incumbent.version,
        "child_version": candidate.version,
        "parent_version": incumbent.version,
        "source_split": "valid_train",
        "source_role": "development",
        "source_episode_count": 8,
    }
    paths = {}
    for name, value in (
        ("comparison", comparison),
        ("validation", validation_audit),
        ("evolution", evolution_audit),
    ):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        paths[name] = path
    return (
        incumbent,
        candidate,
        incumbent_path,
        candidate_path,
        comparison,
        validation_audit,
        evolution_audit,
        paths,
    )


def decide(tmp_path: Path, **counts):
    values = gate_inputs(tmp_path, **counts)
    incumbent, candidate, incumbent_path, candidate_path = values[:4]
    comparison, validation, evolution, paths = values[4:]
    report = decide_experience_candidate(
        comparison=comparison,
        validation_audit=validation,
        evolution_audit=evolution,
        incumbent=incumbent,
        candidate=candidate,
        incumbent_path=incumbent_path,
        candidate_path=candidate_path,
        comparison_path=paths["comparison"],
        validation_audit_path=paths["validation"],
        evolution_audit_path=paths["evolution"],
    )
    return report, values


def test_gate_promotes_significant_gain_without_regression(tmp_path: Path) -> None:
    report, _ = decide(
        tmp_path, baseline_only=0, candidate_only=6, p=0.03125
    )

    assert report["decision"] == "promote_candidate"
    assert report["selected_stable"]["version"] == "exp-v4"
    assert not report["candidate_retained_for_future_evidence"]


def test_gate_retains_weak_positive_candidate_but_keeps_incumbent_stable(
    tmp_path: Path,
) -> None:
    report, _ = decide(tmp_path, baseline_only=0, candidate_only=2, p=0.5)

    assert report["decision"] == "retain_candidate"
    assert report["reason_code"] == "positive_no_regression_but_weak_evidence"
    assert report["selected_stable"]["version"] == "exp-v3"
    assert report["candidate_retained_for_future_evidence"]


def test_gate_rejects_any_paired_regression(tmp_path: Path) -> None:
    report, _ = decide(tmp_path, baseline_only=1, candidate_only=8, p=0.04)

    assert report["decision"] == "reject_candidate"
    assert report["reason_code"] == "paired_regression_detected"
    assert report["selected_stable"]["version"] == "exp-v3"


def test_gate_rejects_no_gain(tmp_path: Path) -> None:
    report, _ = decide(tmp_path, baseline_only=0, candidate_only=0, p=1.0)

    assert report["decision"] == "reject_candidate"
    assert report["reason_code"] == "no_minimum_gain"


def test_gate_rejects_non_evaluation_validation_audit(tmp_path: Path) -> None:
    values = gate_inputs(tmp_path, baseline_only=0, candidate_only=2, p=0.5)
    incumbent, candidate, incumbent_path, candidate_path = values[:4]
    comparison, validation, evolution, paths = values[4:]
    validation = deepcopy(validation)
    validation["protocol_role"] = "development"

    with pytest.raises(ValueError, match="evaluation role"):
        decide_experience_candidate(
            comparison=comparison,
            validation_audit=validation,
            evolution_audit=evolution,
            incumbent=incumbent,
            candidate=candidate,
            incumbent_path=incumbent_path,
            candidate_path=candidate_path,
            comparison_path=paths["comparison"],
            validation_audit_path=paths["validation"],
            evolution_audit_path=paths["evolution"],
        )


def test_gate_rejects_evaluation_split_mislabeled_as_development(
    tmp_path: Path,
) -> None:
    values = gate_inputs(tmp_path, baseline_only=0, candidate_only=2, p=0.5)
    incumbent, candidate, incumbent_path, candidate_path = values[:4]
    comparison, validation, evolution, paths = values[4:]
    evolution = deepcopy(evolution)
    evolution["source_split"] = "valid_unseen"

    with pytest.raises(ValueError, match="not a development split"):
        decide_experience_candidate(
            comparison=comparison,
            validation_audit=validation,
            evolution_audit=evolution,
            incumbent=incumbent,
            candidate=candidate,
            incumbent_path=incumbent_path,
            candidate_path=candidate_path,
            comparison_path=paths["comparison"],
            validation_audit_path=paths["validation"],
            evolution_audit_path=paths["evolution"],
        )


def test_gate_rejects_experience_hash_mismatch(tmp_path: Path) -> None:
    values = gate_inputs(tmp_path, baseline_only=0, candidate_only=2, p=0.5)
    incumbent, candidate, incumbent_path, candidate_path = values[:4]
    comparison, validation, evolution, paths = values[4:]
    comparison = deepcopy(comparison)
    comparison["variants"][1]["run"]["experience_sha256"] = "wrong"

    with pytest.raises(ValueError, match="candidate experience SHA-256 mismatch"):
        decide_experience_candidate(
            comparison=comparison,
            validation_audit=validation,
            evolution_audit=evolution,
            incumbent=incumbent,
            candidate=candidate,
            incumbent_path=incumbent_path,
            candidate_path=candidate_path,
            comparison_path=paths["comparison"],
            validation_audit_path=paths["validation"],
            evolution_audit_path=paths["evolution"],
        )


def test_gate_rejects_inconsistent_paired_cells(tmp_path: Path) -> None:
    values = gate_inputs(tmp_path, baseline_only=0, candidate_only=2, p=0.5)
    incumbent, candidate, incumbent_path, candidate_path = values[:4]
    comparison, validation, evolution, paths = values[4:]
    comparison = deepcopy(comparison)
    comparison["paired_success"]["overall"]["both_fail"] += 1

    with pytest.raises(ValueError, match="do not sum"):
        decide_experience_candidate(
            comparison=comparison,
            validation_audit=validation,
            evolution_audit=evolution,
            incumbent=incumbent,
            candidate=candidate,
            incumbent_path=incumbent_path,
            candidate_path=candidate_path,
            comparison_path=paths["comparison"],
            validation_audit_path=paths["validation"],
            evolution_audit_path=paths["evolution"],
        )


def test_gate_decision_replays_exactly(tmp_path: Path) -> None:
    report, _ = decide(tmp_path, baseline_only=0, candidate_only=2, p=0.5)
    decision_path = tmp_path / "decision.json"

    decision_path.write_text(json.dumps(report), encoding="utf-8")
    audit = audit_experience_candidate_decision(
        report, decision_path=decision_path
    )

    assert audit["status"] == "passed"
    assert audit["replay_equal"]
    assert audit["input_hash_count"] == 5


def test_gate_decision_replay_detects_tampering(tmp_path: Path) -> None:
    report, _ = decide(tmp_path, baseline_only=0, candidate_only=2, p=0.5)
    decision_path = tmp_path / "decision.json"

    report["reason_code"] = "tampered"
    decision_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ValueError, match="not reproducible"):
        audit_experience_candidate_decision(report, decision_path=decision_path)
