"""Gate an evolved experience candidate using audited paired evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.evaluation import decide_experience_candidate
from evomo.experience import load_experience_set


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--validation-audit", type=Path, required=True)
    parser.add_argument("--evolution-audit", type=Path, required=True)
    parser.add_argument("--incumbent", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--minimum-candidate-only", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = decide_experience_candidate(
        comparison=load_json(args.comparison),
        validation_audit=load_json(args.validation_audit),
        evolution_audit=load_json(args.evolution_audit),
        incumbent=load_experience_set(args.incumbent),
        candidate=load_experience_set(args.candidate),
        incumbent_path=args.incumbent,
        candidate_path=args.candidate,
        comparison_path=args.comparison,
        validation_audit_path=args.validation_audit,
        evolution_audit_path=args.evolution_audit,
        alpha=args.alpha,
        minimum_candidate_only=args.minimum_candidate_only,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
