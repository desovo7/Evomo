"""Generate a complete three-GPU Qwen evolution cycle executor config."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from evomo.evaluation import build_qwen_evolution_cycle_plan, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--report-root", type=Path, required=True)
    parser.add_argument("--incumbent-experience", type=Path, required=True)
    parser.add_argument("--candidate-version", required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, default=Path("../models/Qwen3-1.7B"))
    parser.add_argument("--python-executable", type=Path, default=Path(sys.executable))
    parser.add_argument("--gpus", nargs=3, default=("0", "1", "2"))
    parser.add_argument("--development-offset", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--max-history-items", type=int, default=6)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    values = vars(args).copy()
    output = values.pop("output")
    values["gpus"] = tuple(values["gpus"])
    plan = build_qwen_evolution_cycle_plan(**values)
    write_json(output, plan)
    print(json.dumps(plan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
