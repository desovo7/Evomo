"""Convert successful planner trajectories into faithful action SFT data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.data import EpisodeStore
from evomo.experience import load_experience_set
from evomo.training import build_sft_examples, write_sft_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes-root", type=Path, required=True)
    parser.add_argument("--experience-file", type=Path, required=True)
    parser.add_argument("--max-history-items", type=int, default=6)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    episodes = []
    for path in sorted(args.episodes_root.rglob("episode.jsonl")):
        episodes.extend(EpisodeStore(path).load_all())
    experiences = load_experience_set(args.experience_file)
    examples = build_sft_examples(
        episodes, experiences=experiences, max_history_items=args.max_history_items
    )
    manifest = write_sft_dataset(
        examples,
        output_path=args.output,
        manifest_path=args.manifest,
        source_episode_root=args.episodes_root,
        experience_path=args.experience_file,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
