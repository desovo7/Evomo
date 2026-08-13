"""Audit cross-cycle uniqueness in an ALFWorld evaluation exposure ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.evaluation import audit_evaluation_ledger, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    audit = audit_evaluation_ledger(ledger, ledger_path=args.ledger)
    write_json(args.output, audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
