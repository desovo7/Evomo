"""Replay a content-addressed experience-evolution cycle manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.evaluation import audit_evolution_cycle_manifest, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    audit = audit_evolution_cycle_manifest(manifest, manifest_path=args.manifest)
    write_json(args.output, audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
