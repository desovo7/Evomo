"""Freeze every previously unrun ALFWorld train task for self-evolution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.benchmarks.alfworld import discover_tasks
from evomo.evaluation.experience_pool import freeze_experience_pool, previously_run_task_ids


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--pool-id", required=True)
    parser.add_argument("--exclude-episodes-root", type=Path, action="append", default=[])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--shard-count", type=int, default=3)
    args = parser.parse_args()
    tasks = discover_tasks(args.data_root, splits=["train"]).tasks
    excluded = previously_run_task_ids(args.exclude_episodes_root)
    protocol = freeze_experience_pool(
        tasks,
        pool_id=args.pool_id,
        manifest_path=args.manifest,
        protocol_path=args.protocol,
        excluded_task_ids=excluded,
        shard_count=args.shard_count,
    )
    print(json.dumps(protocol, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
