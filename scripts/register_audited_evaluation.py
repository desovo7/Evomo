"""Backfill evaluation exposure from a passed historical audit and summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.evaluation import register_audited_evaluation_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--validation-audit", type=Path, required=True)
    parser.add_argument("--validation-summary", type=Path, required=True)
    parser.add_argument("--allow-historical-overlap", action="store_true")
    parser.add_argument("--exposure-order", type=int)
    args = parser.parse_args()
    receipt = register_audited_evaluation_report(
        ledger_path=args.ledger,
        receipt_path=args.receipt,
        cycle_id=args.cycle_id,
        validation_audit_path=args.validation_audit,
        validation_summary_path=args.validation_summary,
        allow_historical_overlap=args.allow_historical_overlap,
        exposure_order=args.exposure_order,
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
