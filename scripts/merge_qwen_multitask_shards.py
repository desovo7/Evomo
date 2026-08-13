"""Merge disjoint per-variant task-type shards into one summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.evaluation import merge_variant_summaries, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary_paths = sorted(args.shard_root.glob("shard_*/summary.json"))
    if not summary_paths:
        parser.error(f"no shard_*/summary.json files under {args.shard_root}")
    summaries = []
    for path in summary_paths:
        with path.open(encoding="utf-8") as stream:
            summaries.append(json.load(stream))
    merged = merge_variant_summaries(summaries)
    write_json(args.output, merged)
    print(json.dumps(merged, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
