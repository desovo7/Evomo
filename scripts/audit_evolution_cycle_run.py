"""Audit a completed cycle executor state and its append-only event log."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.evaluation import audit_cycle_executor_state, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = audit_cycle_executor_state(args.config, state_dir=args.state_dir)
    write_json(args.output, audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
