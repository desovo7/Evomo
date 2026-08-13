"""Promote an experience candidate per task type from a paired comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from evomo.experience import (
    load_experience_set,
    promote_experience_by_task_type,
    save_experience_set,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--incumbent", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    comparison = json.loads(args.comparison.read_text(encoding="utf-8"))
    paired = comparison.get("paired_success")
    if not paired:
        raise ValueError("comparison does not contain paired_success analysis")
    incumbent = load_experience_set(args.incumbent)
    candidate = load_experience_set(args.candidate)
    summaries = {summary["variant"]: summary for summary in comparison["variants"]}
    baseline_summary = summaries[paired["baseline"]]
    candidate_summary = summaries[paired["candidate"]]
    if baseline_summary["run"]["experience_version"] != incumbent.version:
        raise ValueError("comparison baseline does not use the incumbent experience")
    if candidate_summary["run"]["experience_version"] != candidate.version:
        raise ValueError("comparison candidate does not use the candidate experience")

    decisions = {}
    selected_versions = {}
    for task_type, item in paired["by_task_type"].items():
        promote = item["candidate_only"] > item["baseline_only"]
        selected = candidate.version if promote else incumbent.version
        selected_versions[task_type] = selected
        decisions[task_type] = {
            "incumbent_only_successes": item["baseline_only"],
            "candidate_only_successes": item["candidate_only"],
            "success_delta": item["success_delta"],
            "decision": "promote_candidate" if promote else "retain_incumbent",
            "selected_version": selected,
        }

    promoted = promote_experience_by_task_type(
        incumbent,
        candidate,
        selected_versions=selected_versions,
        version=args.version,
    )
    save_experience_set(promoted, args.output)
    manifest = {
        "schema_version": 1,
        "version": args.version,
        "criterion": "promote iff candidate_only_successes > incumbent_only_successes",
        "comparison": {
            "path": args.comparison.as_posix(),
            "sha256": sha256(args.comparison),
            "baseline_variant": paired["baseline"],
            "candidate_variant": paired["candidate"],
            "split": comparison["split"],
            "task_offset": comparison.get("task_offset", 0),
            "task_count": comparison["task_count_per_variant"],
        },
        "incumbent": {
            "path": args.incumbent.as_posix(),
            "version": incumbent.version,
            "sha256": sha256(args.incumbent),
        },
        "candidate": {
            "path": args.candidate.as_posix(),
            "version": candidate.version,
            "sha256": sha256(args.candidate),
        },
        "decisions": decisions,
        "output": {
            "path": args.output.as_posix(),
            "version": promoted.version,
            "sha256": sha256(args.output),
        },
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
