"""Audit a task-type experience promotion manifest and compiled output."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from evomo.experience import load_experience_set, promote_experience_by_task_type


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    comparison_path = Path(manifest["comparison"]["path"])
    incumbent_path = Path(manifest["incumbent"]["path"])
    candidate_path = Path(manifest["candidate"]["path"])
    for label, path in (
        ("comparison", comparison_path),
        ("incumbent", incumbent_path),
        ("candidate", candidate_path),
    ):
        if digest(path) != manifest[label]["sha256"]:
            raise ValueError(f"{label} SHA-256 mismatch")
    if args.output.as_posix() != manifest["output"]["path"]:
        raise ValueError("output path differs from manifest")
    if digest(args.output) != manifest["output"]["sha256"]:
        raise ValueError("compiled output SHA-256 mismatch")

    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    paired = comparison["paired_success"]
    selected = {}
    for task_type, item in paired["by_task_type"].items():
        promote = item["candidate_only"] > item["baseline_only"]
        expected_decision = "promote_candidate" if promote else "retain_incumbent"
        decision = manifest["decisions"][task_type]
        if decision["decision"] != expected_decision:
            raise ValueError(f"{task_type}: promotion decision violates criterion")
        for key in ("candidate_only_successes", "incumbent_only_successes", "success_delta"):
            source_key = {
                "candidate_only_successes": "candidate_only",
                "incumbent_only_successes": "baseline_only",
                "success_delta": "success_delta",
            }[key]
            if decision[key] != item[source_key]:
                raise ValueError(f"{task_type}: decision count differs from comparison")
        selected[task_type] = decision["selected_version"]

    incumbent = load_experience_set(incumbent_path)
    candidate = load_experience_set(candidate_path)
    rebuilt = promote_experience_by_task_type(
        incumbent,
        candidate,
        selected_versions=selected,
        version=manifest["version"],
    )
    actual = load_experience_set(args.output)
    if rebuilt != actual:
        raise ValueError("compiled output is not reproducible from the manifest")
    sources = {incumbent.version: incumbent, candidate.version: candidate}
    for task_type, source_version in selected.items():
        if actual.render(task_type) != sources[source_version].render(task_type):
            raise ValueError(f"{task_type}: compiled rule text differs from selected source")

    report = {
        "status": "passed",
        "manifest_sha256": digest(args.manifest),
        "comparison_sha256": digest(comparison_path),
        "compiled_output_sha256": digest(args.output),
        "decision_count": len(selected),
        "render_equivalence_task_count": len(selected),
        "promoted_task_types": sorted(
            task_type
            for task_type, decision in manifest["decisions"].items()
            if decision["decision"] == "promote_candidate"
        ),
        "retained_task_types": sorted(
            task_type
            for task_type, decision in manifest["decisions"].items()
            if decision["decision"] == "retain_incumbent"
        ),
    }
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
