"""Verify and record the completed full-pool slime GRPO checkpoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.evaluation import directory_sha256, file_sha256


def directory(path: Path) -> dict:
    digest, files, size = directory_sha256(path)
    return {"path": path.as_posix(), "sha256": digest, "file_count": files, "bytes": size}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hf-checkpoint", type=Path, required=True)
    parser.add_argument("--torch-dist-checkpoint", type=Path, required=True)
    parser.add_argument("--prompt-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prompt = json.loads(args.prompt_manifest.read_text(encoding="utf-8"))
    if prompt.get("task_count") != 3553:
        raise ValueError("formal GRPO run must use the complete 3553-task pool")
    if not (args.hf_checkpoint / "config.json").is_file():
        raise FileNotFoundError("final GRPO Hugging Face checkpoint is incomplete")
    if not (args.torch_dist_checkpoint / "latest_checkpointed_iteration.txt").is_file():
        raise FileNotFoundError("final GRPO torch_dist checkpoint is incomplete")
    report = {
        "schema_version": 1,
        "status": "complete",
        "training_kind": "slime_episode_level_grpo",
        "task_count": prompt["task_count"],
        "n_samples_per_prompt": 2,
        "rollout_batch_size": 11,
        "num_rollout": prompt["task_count"] // 11,
        "epochs": 1,
        "prompt_manifest": {
            "path": args.prompt_manifest.as_posix(),
            "sha256": file_sha256(args.prompt_manifest),
        },
        "hf_checkpoint": directory(args.hf_checkpoint),
        "torch_dist_checkpoint": directory(args.torch_dist_checkpoint),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
