"""Immutable task manifests for large self-evolution experiments."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from evomo.data import EpisodeStore, TaskSpec, TaskStore


EXPERIENCE_POOL_SCHEMA_VERSION = 1


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def task_ids_sha256(tasks: Iterable[TaskSpec]) -> str:
    digest = hashlib.sha256()
    values = tuple(sorted(task.task_id for task in tasks))
    if not values or len(values) != len(set(values)):
        raise ValueError("experience pool task IDs must be non-empty and unique")
    for value in values:
        payload = value.encode("utf-8")
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def previously_run_task_ids(episode_roots: Iterable[str | Path]) -> set[str]:
    """Read task identities from every complete Episode beneath the roots."""

    task_ids: set[str] = set()
    for root in episode_roots:
        path = Path(root)
        candidates = (path,) if path.name == "episode.jsonl" else path.rglob("episode.jsonl")
        for episode_path in sorted(candidates):
            for episode in EpisodeStore(episode_path):
                task_ids.add(episode.task.task_id)
    return task_ids


def freeze_experience_pool(
    tasks: Iterable[TaskSpec],
    *,
    pool_id: str,
    manifest_path: str | Path,
    protocol_path: str | Path,
    excluded_task_ids: Iterable[str] = (),
    shard_count: int = 3,
) -> dict:
    """Freeze all previously unrun tasks and describe deterministic shards."""

    if not pool_id.strip():
        raise ValueError("pool_id must be non-empty")
    if not isinstance(shard_count, int) or isinstance(shard_count, bool) or shard_count <= 0:
        raise ValueError("shard_count must be positive")
    excluded = set(excluded_task_ids)
    selected = tuple(sorted(
        (task for task in tasks if task.task_id not in excluded),
        key=lambda task: task.task_id,
    ))
    if not selected:
        raise ValueError("experience pool contains no previously unrun tasks")
    splits = {task.split for task in selected}
    if splits != {"train"}:
        raise ValueError(f"experience pool must contain only train tasks; observed {sorted(splits)}")

    manifest_path = Path(manifest_path)
    protocol_path = Path(protocol_path)
    TaskStore(manifest_path).write_all(selected)
    shard_sizes = [len(selected[index::shard_count]) for index in range(shard_count)]
    by_type: dict[str, int] = {}
    for task in selected:
        by_type[task.task_type] = by_type.get(task.task_type, 0) + 1
    protocol = {
        "schema_version": EXPERIENCE_POOL_SCHEMA_VERSION,
        "pool_id": pool_id,
        "role": "development_experience_pool",
        "source_split": "train",
        "task_count": len(selected),
        "task_ids_sha256": task_ids_sha256(selected),
        "manifest": {
            "path": manifest_path.as_posix(),
            "sha256": file_sha256(manifest_path),
            "bytes": manifest_path.stat().st_size,
        },
        "selection": {
            "rule": "all playable train tasks absent from pre-freeze Episode artifacts",
            "excluded_previously_run_task_count": len(excluded),
        },
        "task_types": dict(sorted(by_type.items())),
        "sharding": {
            "method": "stable_task_id_round_robin",
            "shard_count": shard_count,
            "shard_sizes": shard_sizes,
        },
    }
    protocol_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = protocol_path.with_suffix(protocol_path.suffix + ".tmp")
    temporary.write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(protocol_path)
    return protocol


def load_frozen_experience_pool(
    manifest_path: str | Path,
    *,
    expected_sha256: str | None = None,
) -> tuple[TaskSpec, ...]:
    path = Path(manifest_path)
    if expected_sha256 is not None and file_sha256(path) != expected_sha256:
        raise ValueError("experience pool manifest SHA-256 mismatch")
    tasks = tuple(TaskStore(path).load_all())
    if not tasks or len({task.task_id for task in tasks}) != len(tasks):
        raise ValueError("experience pool manifest is empty or contains duplicate tasks")
    return tasks
