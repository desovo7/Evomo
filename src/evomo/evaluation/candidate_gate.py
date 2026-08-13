"""Deterministic promotion gate for a child experience candidate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from evomo.experience import (
    DEVELOPMENT_SPLITS,
    EVALUATION_SPLITS,
    ExperienceSet,
    load_experience_set,
)


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decide_experience_candidate(
    *,
    comparison: Mapping,
    validation_audit: Mapping,
    evolution_audit: Mapping,
    incumbent: ExperienceSet,
    candidate: ExperienceSet,
    incumbent_path: str | Path,
    candidate_path: str | Path,
    comparison_path: str | Path,
    validation_audit_path: str | Path,
    evolution_audit_path: str | Path,
    alpha: float = 0.05,
    minimum_candidate_only: int = 1,
) -> dict:
    """Validate the protocol and select promote, retain-candidate, or reject."""

    if not 0 < alpha <= 1:
        raise ValueError("alpha must lie in (0, 1]")
    if minimum_candidate_only < 1:
        raise ValueError("minimum_candidate_only must be positive")
    if candidate.parent_version != incumbent.version:
        raise ValueError("candidate parent_version does not match incumbent version")

    paired = comparison.get("paired_success")
    if not isinstance(paired, Mapping):
        raise ValueError("comparison must contain paired_success")
    summaries = {
        summary["variant"]: summary for summary in comparison.get("variants", ())
    }
    if len(summaries) != 2:
        raise ValueError("candidate gate requires exactly two unique variants")
    try:
        baseline = summaries[paired["baseline"]]
        proposed = summaries[paired["candidate"]]
    except KeyError as exc:
        raise ValueError("paired variants do not resolve to comparison summaries") from exc

    incumbent_path = Path(incumbent_path)
    candidate_path = Path(candidate_path)
    incumbent_sha = file_sha256(incumbent_path)
    candidate_sha = file_sha256(candidate_path)
    expected_experiences = (
        ("baseline", baseline, incumbent, incumbent_sha),
        ("candidate", proposed, candidate, candidate_sha),
    )
    for label, summary, experience, digest in expected_experiences:
        run = summary.get("run", {})
        if run.get("experience_version") != experience.version:
            raise ValueError(f"{label} experience version mismatch")
        if run.get("experience_sha256") != digest:
            raise ValueError(f"{label} experience SHA-256 mismatch")

    if validation_audit.get("status") != "passed":
        raise ValueError("validation audit did not pass")
    if validation_audit.get("protocol_role") != "evaluation":
        raise ValueError("validation audit must have evaluation role")
    if comparison.get("split") not in EVALUATION_SPLITS:
        raise ValueError("comparison split is not an evaluation split")
    for field in ("experience_evidence_task_overlap", "excluded_source_task_overlap"):
        if validation_audit.get(field) != 0:
            raise ValueError(f"validation audit requires zero {field}")
    task_count = comparison.get("task_count_per_variant")
    if validation_audit.get("discovery_task_count") != task_count:
        raise ValueError("validation audit discovery coverage differs from comparison")
    audited_variants = {
        item.get("variant"): item for item in validation_audit.get("variants", ())
    }
    for summary in (baseline, proposed):
        audited = audited_variants.get(summary["variant"])
        if audited is None:
            raise ValueError("validation audit is missing a compared variant")
        if audited.get("episode_count") != task_count:
            raise ValueError("validation audit episode count differs from comparison")
        if audited.get("success_count") != summary.get("success_count"):
            raise ValueError("validation audit success count differs from comparison")

    if evolution_audit.get("status") != "passed":
        raise ValueError("evolution audit did not pass")
    if evolution_audit.get("source_role") != "development":
        raise ValueError("evolution audit must have development role")
    if evolution_audit.get("source_split") not in DEVELOPMENT_SPLITS:
        raise ValueError("evolution source is not a development split")
    if evolution_audit.get("base_version") != incumbent.version:
        raise ValueError("evolution audit base version mismatch")
    if evolution_audit.get("child_version") != candidate.version:
        raise ValueError("evolution audit child version mismatch")
    if evolution_audit.get("parent_version") != incumbent.version:
        raise ValueError("evolution audit parent version mismatch")

    overall = paired.get("overall", {})
    incumbent_only = int(overall.get("baseline_only", -1))
    candidate_only = int(overall.get("candidate_only", -1))
    exact_p_value = float(overall.get("exact_p_value", -1))
    if min(incumbent_only, candidate_only) < 0 or not 0 <= exact_p_value <= 1:
        raise ValueError("paired overall counts or p-value are invalid")
    if overall.get("task_count") != task_count:
        raise ValueError("paired task count differs from comparison")
    if overall.get("success_delta") != candidate_only - incumbent_only:
        raise ValueError("paired success delta is inconsistent")
    paired_total = sum(
        int(overall.get(key, -task_count))
        for key in ("both_success", "baseline_only", "candidate_only", "both_fail")
    )
    if paired_total != task_count:
        raise ValueError("paired outcome cells do not sum to task count")
    if baseline["success_count"] != overall["both_success"] + incumbent_only:
        raise ValueError("baseline success count is inconsistent with paired cells")
    if proposed["success_count"] != overall["both_success"] + candidate_only:
        raise ValueError("candidate success count is inconsistent with paired cells")

    if incumbent_only > 0:
        decision = "reject_candidate"
        reason_code = "paired_regression_detected"
        selected = incumbent
        selected_path = incumbent_path
        selected_sha = incumbent_sha
    elif candidate_only < minimum_candidate_only:
        decision = "reject_candidate"
        reason_code = "no_minimum_gain"
        selected = incumbent
        selected_path = incumbent_path
        selected_sha = incumbent_sha
    elif exact_p_value <= alpha:
        decision = "promote_candidate"
        reason_code = "significant_no_regression_gain"
        selected = candidate
        selected_path = candidate_path
        selected_sha = candidate_sha
    else:
        decision = "retain_candidate"
        reason_code = "positive_no_regression_but_weak_evidence"
        selected = incumbent
        selected_path = incumbent_path
        selected_sha = incumbent_sha

    return {
        "schema_version": 2,
        "status": "passed",
        "decision": decision,
        "reason_code": reason_code,
        "criterion": {
            "require_zero_incumbent_only_successes": True,
            "minimum_candidate_only_successes": minimum_candidate_only,
            "maximum_exact_p_value_for_promotion": alpha,
        },
        "protocol": {
            "source_split": evolution_audit.get("source_split"),
            "source_role": evolution_audit.get("source_role"),
            "source_episode_count": evolution_audit.get("source_episode_count"),
            "validation_split": comparison.get("split"),
            "validation_role": validation_audit.get("protocol_role"),
            "validation_task_count": task_count,
            "experience_evidence_task_overlap": validation_audit.get(
                "experience_evidence_task_overlap"
            ),
            "source_task_overlap": validation_audit.get(
                "excluded_source_task_overlap"
            ),
        },
        "inputs": {
            "comparison": {
                "path": Path(comparison_path).as_posix(),
                "sha256": file_sha256(comparison_path),
            },
            "validation_audit": {
                "path": Path(validation_audit_path).as_posix(),
                "sha256": file_sha256(validation_audit_path),
            },
            "evolution_audit": {
                "path": Path(evolution_audit_path).as_posix(),
                "sha256": file_sha256(evolution_audit_path),
            },
        },
        "incumbent": {
            "variant": baseline["variant"],
            "path": incumbent_path.as_posix(),
            "version": incumbent.version,
            "sha256": incumbent_sha,
            "success_count": baseline["success_count"],
            "steps": baseline["totals"]["steps"],
        },
        "candidate": {
            "variant": proposed["variant"],
            "path": candidate_path.as_posix(),
            "version": candidate.version,
            "sha256": candidate_sha,
            "success_count": proposed["success_count"],
            "steps": proposed["totals"]["steps"],
        },
        "paired": dict(overall),
        "by_task_type": dict(paired.get("by_task_type", {})),
        "selected_stable": {
            "path": selected_path.as_posix(),
            "version": selected.version,
            "sha256": selected_sha,
        },
        "candidate_retained_for_future_evidence": decision == "retain_candidate",
    }


def audit_experience_candidate_decision(
    decision: Mapping, *, decision_path: str | Path
) -> dict:
    """Replay a persisted gate decision from its content-addressed inputs."""

    if decision.get("schema_version") != 2:
        raise ValueError("unsupported candidate decision schema")
    inputs = decision.get("inputs", {})

    def checked_json(name: str) -> tuple[Path, dict]:
        record = inputs.get(name, {})
        path = Path(record.get("path", ""))
        if not path.is_file():
            raise ValueError(f"{name} input path is missing")
        if file_sha256(path) != record.get("sha256"):
            raise ValueError(f"{name} input SHA-256 mismatch")
        return path, json.loads(path.read_text(encoding="utf-8"))

    comparison_path, comparison = checked_json("comparison")
    validation_path, validation_audit = checked_json("validation_audit")
    evolution_path, evolution_audit = checked_json("evolution_audit")
    incumbent_path = Path(decision.get("incumbent", {}).get("path", ""))
    candidate_path = Path(decision.get("candidate", {}).get("path", ""))
    for label, path, expected in (
        ("incumbent", incumbent_path, decision.get("incumbent", {}).get("sha256")),
        ("candidate", candidate_path, decision.get("candidate", {}).get("sha256")),
    ):
        if not path.is_file():
            raise ValueError(f"{label} experience path is missing")
        if file_sha256(path) != expected:
            raise ValueError(f"{label} experience SHA-256 mismatch")

    criterion = decision.get("criterion", {})
    rebuilt = decide_experience_candidate(
        comparison=comparison,
        validation_audit=validation_audit,
        evolution_audit=evolution_audit,
        incumbent=load_experience_set(incumbent_path),
        candidate=load_experience_set(candidate_path),
        incumbent_path=incumbent_path,
        candidate_path=candidate_path,
        comparison_path=comparison_path,
        validation_audit_path=validation_path,
        evolution_audit_path=evolution_path,
        alpha=float(criterion["maximum_exact_p_value_for_promotion"]),
        minimum_candidate_only=int(criterion["minimum_candidate_only_successes"]),
    )
    if rebuilt != decision:
        raise ValueError("persisted candidate decision is not reproducible")
    return {
        "status": "passed",
        "decision_path": Path(decision_path).as_posix(),
        "decision_sha256": file_sha256(decision_path),
        "replay_equal": True,
        "input_hash_count": 5,
        "decision": decision["decision"],
        "selected_stable_version": decision["selected_stable"]["version"],
    }
