from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evomo.benchmarks.alfworld import TaskDiscoveryError, discover_tasks
from evomo.data import TaskStore


def trajectory_payload(
    *,
    task_id: str,
    task_type: str = "pick_and_place_simple",
    goal: str = "Put the apple on the table.",
    scene_num: int = 1,
) -> dict:
    return {
        "task_id": task_id,
        "task_type": task_type,
        "scene": {"scene_num": scene_num},
        "pddl_params": {
            "object_target": "Apple",
            "parent_target": "DiningTable",
        },
        "turk_annotations": {
            "anns": [
                {
                    "task_desc": goal,
                    "high_descs": ["Pick up the apple", "Put it on the table"],
                }
            ]
        },
    }


def create_trial(
    dataset_root: Path,
    *,
    split: str,
    problem: str,
    trial: str,
    playable: bool,
    payload: dict | None = None,
) -> Path:
    trial_directory = dataset_root / split / problem / trial
    trial_directory.mkdir(parents=True)
    trajectory_file = trial_directory / "traj_data.json"
    trajectory_file.write_text(
        json.dumps(payload or trajectory_payload(task_id=trial)),
        encoding="utf-8",
    )
    if playable:
        (trial_directory / "game.tw-pddl").write_text("game", encoding="utf-8")
    return trajectory_file


class AlfworldDiscoveryTest(unittest.TestCase):
    def test_discovers_playable_tasks_in_stable_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            alfworld_root = Path(directory)
            dataset_root = alfworld_root / "json_2.1.1"
            create_trial(
                dataset_root,
                split="train",
                problem="problem-z",
                trial="trial-z",
                playable=True,
                payload=trajectory_payload(
                    task_id="trial-z",
                    goal="  Put   the apple on the table.  ",
                    scene_num=7,
                ),
            )
            create_trial(
                dataset_root,
                split="train",
                problem="problem-a",
                trial="trial-a",
                playable=True,
            )
            create_trial(
                dataset_root,
                split="train",
                problem="problem-missing",
                trial="trial-missing",
                playable=False,
            )

            result = discover_tasks(alfworld_root, splits=["train"])

            self.assertEqual(
                [task.task_id for task in result.tasks],
                ["train/problem-a/trial-a", "train/problem-z/trial-z"],
            )
            self.assertEqual(result.tasks[1].goal, "Put the apple on the table.")
            self.assertEqual(
                result.tasks[1].game_file,
                "train/problem-z/trial-z/game.tw-pddl",
            )
            self.assertEqual(result.tasks[1].metadata["scene_num"], 7)
            self.assertEqual(result.report.trajectories_found, 3)
            self.assertEqual(result.report.tasks_included, 2)
            self.assertEqual(result.report.missing_game_files, 1)

    def test_can_include_trials_without_game_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dataset_root = Path(directory) / "json_2.1.1"
            create_trial(
                dataset_root,
                split="valid_seen",
                problem="problem-a",
                trial="trial-a",
                playable=False,
            )

            result = discover_tasks(
                dataset_root,
                splits=["valid_seen"],
                playable_only=False,
            )

            self.assertEqual(len(result.tasks), 1)
            self.assertIsNone(result.tasks[0].game_file)
            self.assertFalse(result.report.playable_only)
            self.assertEqual(result.report.missing_game_files, 1)

    def test_missing_split_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dataset_root = Path(directory) / "json_2.1.1"
            dataset_root.mkdir()
            with self.assertRaisesRegex(FileNotFoundError, "valid_unseen"):
                discover_tasks(dataset_root, splits=["valid_unseen"])

    def test_malformed_metadata_names_the_source_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dataset_root = Path(directory) / "json_2.1.1"
            trajectory_file = create_trial(
                dataset_root,
                split="train",
                problem="problem-a",
                trial="trial-a",
                playable=True,
                payload={"task_id": "trial-a"},
            )
            with self.assertRaisesRegex(TaskDiscoveryError, str(trajectory_file)):
                discover_tasks(dataset_root, splits=["train"])

    def test_rejects_duplicate_and_unsafe_split_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dataset_root = Path(directory) / "json_2.1.1"
            (dataset_root / "train").mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "duplicate split"):
                discover_tasks(dataset_root, splits=["train", "train"])
            with self.assertRaisesRegex(ValueError, "invalid split"):
                discover_tasks(dataset_root, splits=["../train"])


class TaskStoreTest(unittest.TestCase):
    def test_atomic_manifest_round_trip_and_overwrite_guard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dataset_root = Path(directory) / "json_2.1.1"
            create_trial(
                dataset_root,
                split="train",
                problem="problem-a",
                trial="trial-a",
                playable=True,
            )
            tasks = discover_tasks(dataset_root, splits=["train"]).tasks
            manifest = Path(directory) / "manifests" / "tasks.jsonl"
            store = TaskStore(manifest)

            self.assertEqual(store.write_all(tasks), 1)
            self.assertEqual(store.load_all(), list(tasks))
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                store.write_all(tasks)
            self.assertEqual(store.write_all(tasks, overwrite=True), 1)


if __name__ == "__main__":
    unittest.main()
