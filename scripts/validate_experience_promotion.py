"""Validate a promoted champion against its candidate on a blind comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--candidate-variant", required=True)
    parser.add_argument("--champion-variant", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    comparison = json.loads(args.comparison.read_text(encoding="utf-8"))
    summaries = {summary["variant"]: summary for summary in comparison["variants"]}
    candidate = summaries[args.candidate_variant]
    champion = summaries[args.champion_variant]
    pair = next(
        item
        for item in comparison["pairwise_success"]
        if item["baseline"] == args.candidate_variant
        and item["candidate"] == args.champion_variant
    )
    overall = pair["overall"]
    accepted = overall["success_delta"] >= 0
    report = {
        "schema_version": 1,
        "status": "passed",
        "decision": "accept_champion" if accepted else "reject_champion",
        "criterion": "champion success count must not be lower than candidate",
        "comparison": {
            "path": args.comparison.as_posix(),
            "sha256": hashlib.sha256(args.comparison.read_bytes()).hexdigest(),
            "split": comparison["split"],
            "task_count": comparison["task_count_per_variant"],
        },
        "candidate": {
            "variant": args.candidate_variant,
            "experience_version": candidate["run"]["experience_version"],
            "success_count": candidate["success_count"],
            "steps": candidate["totals"]["steps"],
        },
        "champion": {
            "variant": args.champion_variant,
            "experience_version": champion["run"]["experience_version"],
            "success_count": champion["success_count"],
            "steps": champion["totals"]["steps"],
        },
        "selected_deployment": {
            "variant": (
                args.champion_variant if accepted else args.candidate_variant
            ),
            "experience_version": (
                champion["run"]["experience_version"]
                if accepted
                else candidate["run"]["experience_version"]
            ),
            "experience_sha256": (
                champion["run"]["experience_sha256"]
                if accepted
                else candidate["run"]["experience_sha256"]
            ),
        },
        "paired": overall,
        "by_task_type": pair["by_task_type"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
