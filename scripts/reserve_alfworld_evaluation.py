"""Atomically reserve ALFWorld evaluation tasks before a cycle reveals them."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.evaluation import CANONICAL_TASK_TYPES, reserve_alfworld_evaluation_tasks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--task-types", nargs="+", default=CANONICAL_TASK_TYPES)
    args = parser.parse_args()
    receipt = reserve_alfworld_evaluation_tasks(
        ledger_path=args.ledger,
        receipt_path=args.receipt,
        cycle_id=args.cycle_id,
        data_root=args.data_root,
        split=args.split,
        task_types=args.task_types,
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
