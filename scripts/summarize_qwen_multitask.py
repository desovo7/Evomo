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
    parser.add_argument("--per-type", type=int, default=1)
    parser.add_argument("--variants", nargs="+", default=("B", "C", "D"))
    parser.add_argument(
        "--summary",
        action="append",
        default=[],
        metavar="VARIANT=PATH",
        help="Override one variant summary path (repeatable).",
    )
    args = parser.parse_args()
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
        per_type=args.per_type,
    )
    write_json(args.input_dir / "comparison.json", comparison)
    (args.input_dir / "README.md").write_text(
        render_comparison_markdown(comparison),
        encoding="utf-8",
    )
    print(json.dumps(comparison, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
