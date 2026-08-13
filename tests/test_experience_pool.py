from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evomo.data import TaskSpec
from evomo.evaluation.experience_pool import (
    file_sha256,
    freeze_experience_pool,
    load_frozen_experience_pool,
)


def task(index: int, *, split: str = "train") -> TaskSpec:
    return TaskSpec(
        task_id=f"{split}/problem-{index}/trial-{index}",
        split=split,
        task_type="pick_and_place_simple",
        goal="Put an apple on the table.",
        game_file=f"{split}/problem-{index}/trial-{index}/game.tw-pddl",
    )


class ExperiencePoolTest(unittest.TestCase):
    def test_freezes_all_unrun_tasks_with_balanced_stable_shards(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "tasks.jsonl"
            protocol_path = root / "protocol.json"
            protocol = freeze_experience_pool(
                [task(index) for index in range(8)],
                pool_id="pool-v1",
                manifest_path=manifest,
                protocol_path=protocol_path,
                excluded_task_ids={task(2).task_id},
                shard_count=3,
            )

            self.assertEqual(protocol["task_count"], 7)
            self.assertEqual(protocol["sharding"]["shard_sizes"], [3, 2, 2])
            self.assertEqual(protocol["manifest"]["sha256"], file_sha256(manifest))
            self.assertEqual(len(load_frozen_experience_pool(manifest)), 7)
            self.assertEqual(json.loads(protocol_path.read_text()), protocol)

    def test_rejects_non_train_tasks_and_changed_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "only train"):
                freeze_experience_pool(
                    [task(0, split="valid_train")],
                    pool_id="bad",
                    manifest_path=root / "bad.jsonl",
                    protocol_path=root / "bad.json",
                )
            manifest = root / "tasks.jsonl"
            freeze_experience_pool(
                [task(0)],
                pool_id="pool-v1",
                manifest_path=manifest,
                protocol_path=root / "protocol.json",
            )
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                load_frozen_experience_pool(manifest, expected_sha256="0" * 64)


if __name__ == "__main__":
    unittest.main()
