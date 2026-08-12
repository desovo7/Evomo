"""Atomic JSONL manifests for discovered tasks."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Iterable, Iterator

from evomo.data.schema import TaskSpec


class TaskStore:
    """Read and atomically replace a TaskSpec JSONL manifest."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def write_all(self, tasks: Iterable[TaskSpec], *, overwrite: bool = False) -> int:
        if self.path.exists() and not overwrite:
            raise FileExistsError(f"task manifest already exists: {self.path}")

        materialized = tuple(tasks)
        task_ids = [task.task_id for task in materialized]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("task manifest contains duplicate task_id values")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary_path = Path(stream.name)
                for task in materialized:
                    json.dump(
                        task.to_dict(),
                        stream,
                        ensure_ascii=False,
                        allow_nan=False,
                        separators=(",", ":"),
                    )
                    stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
        return len(materialized)

    def __iter__(self) -> Iterator[TaskSpec]:
        if not self.path.exists():
            return

        seen: set[str] = set()
        with self.path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                    task = TaskSpec.from_dict(value)
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(
                        f"invalid task at {self.path}:{line_number}: {exc}"
                    ) from exc
                if task.task_id in seen:
                    raise ValueError(
                        f"duplicate task_id at {self.path}:{line_number}: {task.task_id}"
                    )
                seen.add(task.task_id)
                yield task

    def load_all(self) -> list[TaskSpec]:
        return list(self)
