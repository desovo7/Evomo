"""Replay and audit a persisted experience candidate gate decision."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.evaluation import audit_experience_candidate_decision


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    decision = json.loads(args.decision.read_text(encoding="utf-8"))
    report = audit_experience_candidate_decision(
        decision, decision_path=args.decision
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
