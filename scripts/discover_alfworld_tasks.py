"""Build a portable TaskSpec manifest from an ALFWorld data directory."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from evomo.benchmarks.alfworld import DEFAULT_SPLITS, discover_tasks
from evomo.data import TaskStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        default=os.environ.get("ALFWORLD_DATA"),
        help="ALFWORLD_DATA directory or its json_2.1.1 child",
    )
    parser.add_argument(
        "--split",
        action="append",
        dest="splits",
        help="split to scan; repeat this flag (default: all canonical splits)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/manifests/alfworld_tasks.jsonl"),
    )
    parser.add_argument(
        "--include-incomplete",
        action="store_true",
        help="include trials without game.tw-pddl (not runnable by TextWorld)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing output manifest atomically",
    )
    args = parser.parse_args()
    if not args.data_root:
        parser.error("--data-root is required when ALFWORLD_DATA is unset")
    return args


def main() -> None:
    args = parse_args()
    result = discover_tasks(
        args.data_root,
        splits=args.splits or DEFAULT_SPLITS,
        playable_only=not args.include_incomplete,
    )
    TaskStore(args.output).write_all(result.tasks, overwrite=args.overwrite)
    summary = result.report.to_dict()
    summary["manifest"] = str(args.output.resolve())
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
