"""Execute or safely resume a configured self-evolution cycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.evaluation import run_cycle_executor


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    args = parser.parse_args()
    state = run_cycle_executor(args.config, state_dir=args.state_dir)
    print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
