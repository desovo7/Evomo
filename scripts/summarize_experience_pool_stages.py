"""Create a compact, auditable comparison of full experience-pool stages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.evaluation import file_sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", action="append", nargs=2, metavar=("NAME", "SUMMARY"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    stages = []
    expected_ids = None
    for name, value in args.stage:
        path = Path(value)
        summary = json.loads(path.read_text(encoding="utf-8"))
        ids = {row["task_id"] for row in summary["tasks"]}
        if expected_ids is None:
            expected_ids = ids
        elif ids != expected_ids:
            raise ValueError("stage summaries do not cover identical tasks")
        stages.append({
            "name": name,
            "summary_path": path.as_posix(),
            "summary_sha256": file_sha256(path),
            "variant": summary["variant"],
            "policy_id": summary["policy_id"],
            "task_count": summary["task_count"],
            "success_count": summary["success_count"],
            "success_rate": summary["success_rate"],
            "by_task_type": summary["by_task_type"],
        })
    result = {
        "schema_version": 1,
        "task_count": len(expected_ids or ()),
        "stages": stages,
        "success_count_deltas": {
            f"{left['name']}->{right['name']}": right["success_count"] - left["success_count"]
            for left, right in zip(stages, stages[1:])
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
