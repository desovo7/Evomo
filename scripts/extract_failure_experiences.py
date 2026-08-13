"""Extract a versioned experience set from persisted failed trajectories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.data import EpisodeStore
from evomo.experience import extract_failure_experiences, save_experience_set


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes-root", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    episodes = []
    for path in sorted(args.episodes_root.rglob("episode.jsonl")):
        episodes.extend(EpisodeStore(path).load_all())
    experiences = extract_failure_experiences(episodes, version=args.version)
    save_experience_set(experiences, args.output)
    print(json.dumps(experiences.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
