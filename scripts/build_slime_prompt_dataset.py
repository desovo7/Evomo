"""Convert a frozen TaskSpec pool into slime's prompt/label JSONL contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from evomo.data import TaskStore
from evomo.evaluation import file_sha256, task_ids_sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    tasks = tuple(TaskStore(args.task_manifest).load_all())
    if not tasks or len({task.task_id for task in tasks}) != len(tasks):
        raise ValueError("task manifest must be non-empty and unique")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with args.output.open("wb") as stream:
        for task in tasks:
            row = json.dumps(
                {"prompt": task.goal, "label": {"task": task.to_dict()}},
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8") + b"\n"
            stream.write(row)
            digest.update(row)
    manifest = {
        "schema_version": 1,
        "format": "slime_alfworld_task_prompts",
        "task_manifest": args.task_manifest.as_posix(),
        "task_manifest_sha256": file_sha256(args.task_manifest),
        "task_ids_sha256": task_ids_sha256(task.task_id for task in tasks),
        "task_count": len(tasks),
        "dataset_sha256": digest.hexdigest(),
        "dataset_bytes": args.output.stat().st_size,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
