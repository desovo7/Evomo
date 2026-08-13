"""Merge completed B/C/D multi-task summaries into one auditable report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.evaluation import (
    build_cross_variant_comparison,
    render_comparison_markdown,
    write_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--split", default="valid_train")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--per-type", type=int)
    selection.add_argument("--all-tasks", action="store_true")
    parser.add_argument("--task-offset", type=int, default=0)
    parser.add_argument("--variants", nargs="+", default=("B", "C", "D"))
    parser.add_argument(
        "--summary",
        action="append",
        default=[],
        metavar="VARIANT=PATH",
        help="Override one variant summary path (repeatable).",
    )
    args = parser.parse_args()
    if not args.all_tasks and args.per_type is None:
        args.per_type = 1
    summary_paths = {}
    for item in args.summary:
        if "=" not in item:
            parser.error("--summary must use VARIANT=PATH")
        variant, path = item.split("=", 1)
        if not variant or not path or variant in summary_paths:
            parser.error("--summary variants and paths must be non-empty and unique")
        summary_paths[variant] = Path(path)
    summaries = []
    for variant in args.variants:
        path = summary_paths.get(variant, args.input_dir / variant / "summary.json")
        with path.open(encoding="utf-8") as stream:
            summary = json.load(stream)
        if summary.get("variant") != variant:
            raise ValueError(f"{path} does not contain variant {variant}")
        summaries.append(summary)
    comparison = build_cross_variant_comparison(
        summaries,
        split=args.split,
        per_type=None if args.all_tasks else args.per_type,
    )
    comparison["task_offset"] = args.task_offset
    write_json(args.input_dir / "comparison.json", comparison)
    (args.input_dir / "README.md").write_text(
        render_comparison_markdown(comparison),
        encoding="utf-8",
    )
    print(json.dumps(comparison, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
