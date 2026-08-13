"""Persist a compact stage result while content-addressing large local artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.evaluation import file_sha256


def artifact(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    return {"path": path.as_posix(), "sha256": file_sha256(path), "bytes": path.stat().st_size}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--training-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    result = {
        "schema_version": 1,
        "stage": args.stage,
        "status": "complete",
        "task_count": summary["task_count"],
        "success_count": summary["success_count"],
        "success_rate": summary["success_rate"],
        "by_task_type": summary["by_task_type"],
        "summary": artifact(args.summary),
        "audit": artifact(args.audit),
        "audit_status": audit.get("status", "complete"),
    }
    if args.training_report:
        training = json.loads(args.training_report.read_text(encoding="utf-8"))
        result["training"] = training
        result["training_report"] = artifact(args.training_report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
