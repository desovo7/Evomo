"""Register evaluation exposure from a completed audited evolution cycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.evaluation import register_completed_evaluation_cycle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--executor-config", type=Path, required=True)
    parser.add_argument("--executor-state-dir", type=Path, required=True)
    parser.add_argument("--validation-summary", type=Path, required=True)
    parser.add_argument("--allow-historical-overlap", action="store_true")
    parser.add_argument("--exposure-order", type=int)
    args = parser.parse_args()
    receipt = register_completed_evaluation_cycle(
        ledger_path=args.ledger,
        receipt_path=args.receipt,
        manifest_path=args.manifest,
        executor_config_path=args.executor_config,
        executor_state_dir=args.executor_state_dir,
        validation_summary_path=args.validation_summary,
        allow_historical_overlap=args.allow_historical_overlap,
        exposure_order=args.exposure_order,
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
