from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evomo.data import TaskSpec
from evomo.envs.alfworld_textworld import AlfworldTextEnvironment
from evomo.envs.contracts import EnvironmentStep


class FakeState:
    def __init__(
        self,
        feedback: str,
        admissible_commands: list[str],
        *,
        won: bool = False,
    ) -> None:
        self.feedback = feedback
        self.admissible_commands = admissible_commands
        self.won = won


class FakeBackend:
    def __init__(self) -> None:
        self.closed = False
        self.actions: list[str] = []

    def reset(self) -> FakeState:
        return FakeState("initial observation", ["go to table", "look"])

    def step(self, action: str) -> tuple[FakeState, float, bool]:
        self.actions.append(action)
        return FakeState("next observation", ["take apple"], won=False), 0.5, False

    def close(self) -> None:
        self.closed = True


def make_dataset(directory: str) -> tuple[Path, TaskSpec]:
    dataset_root = Path(directory) / "json_2.1.1"
    game_file = dataset_root / "train" / "problem" / "trial" / "game.tw-pddl"
    game_file.parent.mkdir(parents=True)
    game_file.write_text(json.dumps({"solvable": True}), encoding="utf-8")
    task = TaskSpec(
        task_id="train/problem/trial",
        split="train",
        task_type="pick_and_place_simple",
        goal="Put the apple on the table.",
        game_file="train/problem/trial/game.tw-pddl",
    )
    return dataset_root, task


class AlfworldEnvironmentTest(unittest.TestCase):
    def test_reset_then_step_converts_backend_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dataset_root, task = make_dataset(directory)
            backend = FakeBackend()
            opened_paths: list[Path] = []

            def factory(path: Path) -> FakeBackend:
                opened_paths.append(path)
                return backend

            environment = AlfworldTextEnvironment(dataset_root, backend_factory=factory)
            reset = environment.reset(task, seed=42)
            transition = environment.step("go to table")

            self.assertEqual(opened_paths, [dataset_root / task.game_file])
            self.assertEqual(reset.observation, "initial observation")
            self.assertEqual(reset.admissible_actions, ("go to table", "look"))
            self.assertEqual(reset.info["requested_seed"], 42)
            self.assertFalse(reset.info["domain_randomization"])
            self.assertEqual(transition.observation, "next observation")
            self.assertEqual(transition.reward, 0.5)
            self.assertFalse(transition.terminated)
            self.assertFalse(transition.success)
            self.assertTrue(transition.info["action_was_admissible"])
            self.assertEqual(backend.actions, ["go to table"])
            environment.close()
            self.assertTrue(backend.closed)

    def test_step_requires_reset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dataset_root, _ = make_dataset(directory)
            environment = AlfworldTextEnvironment(dataset_root, backend_factory=lambda _: FakeBackend())
            with self.assertRaisesRegex(RuntimeError, "reset"):
                environment.step("look")

    def test_rejects_task_path_outside_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dataset_root, task = make_dataset(directory)
            escaped = TaskSpec(
                task_id=task.task_id,
                split=task.split,
                task_type=task.task_type,
                goal=task.goal,
                game_file="../outside/game.tw-pddl",
            )
            environment = AlfworldTextEnvironment(dataset_root, backend_factory=lambda _: FakeBackend())
            with self.assertRaisesRegex(ValueError, "escapes"):
                environment.reset(escaped, seed=42)

    def test_rejects_game_not_marked_solvable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dataset_root, task = make_dataset(directory)
            (dataset_root / task.game_file).write_text(
                json.dumps({"solvable": False}), encoding="utf-8"
            )
            environment = AlfworldTextEnvironment(dataset_root, backend_factory=lambda _: FakeBackend())
            with self.assertRaisesRegex(ValueError, "not marked solvable"):
                environment.reset(task, seed=42)

    def test_successful_step_must_terminate(self) -> None:
        with self.assertRaisesRegex(ValueError, "must terminate"):
            EnvironmentStep(
                observation="done",
                admissible_actions=(),
                reward=1,
                terminated=False,
                success=True,
            )


if __name__ == "__main__":
    unittest.main()
