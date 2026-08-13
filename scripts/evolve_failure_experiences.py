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
    validate_evolution_source,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--episodes-root", type=Path, required=True)
    parser.add_argument(
        "--source-split",
        required=True,
        help="Declared development split; evaluation splits are rejected.",
    )
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--enable-progress-rules",
        action="store_true",
        help="Extract opt-in delivered-object and destination-opening rules.",
    )
    args = parser.parse_args()
    episodes = []
    for path in sorted(args.episodes_root.rglob("episode.jsonl")):
        episodes.extend(EpisodeStore(path).load_all())
    episodes = list(
        validate_evolution_source(episodes, expected_split=args.source_split)
    )
    episode_ids = [episode.episode_id for episode in episodes]
    if len(episode_ids) != len(set(episode_ids)):
        raise ValueError("evolution source contains duplicate episode IDs")
    base = load_experience_set(args.base)
    observed_versions = {
        step.info.get("policy", {}).get("metadata", {}).get("experience_version")
        for episode in episodes
        for step in episode.steps
    }
    if observed_versions != {base.version}:
        raise ValueError(
            f"evolution episodes must all use base version {base.version!r}; "
            f"observed {sorted(map(str, observed_versions))}"
        )
    evolved = evolve_experience_set(
        base,
        episodes,
        version=args.version,
        enable_progress_rules=args.enable_progress_rules,
    )
    save_experience_set(evolved, args.output)
    print(json.dumps(evolved.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
