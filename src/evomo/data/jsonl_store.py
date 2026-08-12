"""Append-only JSONL persistence for completed episodes."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator

from evomo.data.schema import Episode


class EpisodeStore:
    """Store one complete Episode per UTF-8 JSONL line."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, episode: Episode, *, durable: bool = False) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            episode.to_dict(),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(payload)
            stream.write("\n")
            stream.flush()
            if durable:
                os.fsync(stream.fileno())

    def __iter__(self) -> Iterator[Episode]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                    yield Episode.from_dict(value)
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(
                        f"invalid episode at {self.path}:{line_number}: {exc}"
                    ) from exc

    def load_all(self) -> list[Episode]:
        return list(self)
