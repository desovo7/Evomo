"""Evolve an experience set from failures produced while using its prior version."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.data import EpisodeStore
from evomo.experience import (
    evolve_experience_set,
    load_experience_set,
    save_experience_set,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--episodes-root", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    episodes = []
    for path in sorted(args.episodes_root.glob("*/episode.jsonl")):
        episodes.extend(EpisodeStore(path).load_all())
    evolved = evolve_experience_set(
        load_experience_set(args.base), episodes, version=args.version
    )
    save_experience_set(evolved, args.output)
    print(json.dumps(evolved.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
