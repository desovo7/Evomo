"""Build a content-addressed manifest for a completed evolution cycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.evaluation import build_evolution_cycle_manifest, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle-id", required=True)
    for name in (
        "incumbent-experience",
        "development-trajectories",
        "development-summary",
        "development-audit",
        "candidate-experience",
        "evolution-audit",
        "validation-trajectories",
        "validation-incumbent-summary",
        "validation-candidate-summary",
        "comparison",
        "validation-audit",
        "decision",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    values = vars(args).copy()
    output = values.pop("output")
    manifest = build_evolution_cycle_manifest(**values)
    write_json(output, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
