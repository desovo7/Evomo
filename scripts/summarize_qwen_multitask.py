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
    args = parser.parse_args()
    summaries = []
    for variant in ("B", "C", "D"):
        path = args.input_dir / variant / "summary.json"
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
