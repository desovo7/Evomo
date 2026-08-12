from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from evomo.data import EpisodeRecorder, EpisodeStore, TaskSpec, TerminationReason


class FixedClock:
    def __init__(self) -> None:
        self._second = 0

    def __call__(self) -> datetime:
        value = datetime(2026, 8, 12, 0, 0, self._second, tzinfo=timezone.utc)
        self._second += 1
        return value


def make_task() -> TaskSpec:
    return TaskSpec(
        task_id="train/pick_and_place/001",
        split="train",
        task_type="pick_and_place",
        goal="Put the apple on the table.",
        metadata={"source": "synthetic"},
    )


class DataFlowTest(unittest.TestCase):
    def test_record_finish_store_and_restore(self) -> None:
        recorder = EpisodeRecorder(
            task=make_task(),
            policy_id="test-policy-v1",
            seed=42,
            initial_observation="An apple is on the counter.",
            episode_id="episode-001",
            clock=FixedClock(),
        )
        recorder.record_step(
            observation=recorder.next_observation,
            admissible_actions=["take apple from counter", "look"],
            action="take apple from counter",
            next_observation="You are holding the apple.",
            reward=0,
            terminated=False,
        )
        recorder.record_step(
            observation=recorder.next_observation,
            admissible_actions=["put apple on table"],
            action="put apple on table",
            next_observation="Task completed.",
            reward=1,
            terminated=True,
            info={"won": True},
        )
        episode = recorder.finish(
            success=True,
            termination_reason=TerminationReason.SUCCESS,
        )

        self.assertEqual(episode.total_reward, 1.0)
        self.assertEqual([step.step_index for step in episode.steps], [0, 1])
        self.assertEqual(episode.started_at, "2026-08-12T00:00:00+00:00")
        self.assertEqual(episode.ended_at, "2026-08-12T00:00:01+00:00")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "episodes.jsonl"
            store = EpisodeStore(path)
            store.append(episode)
            restored = store.load_all()

            self.assertEqual(restored, [episode])
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 1)

    def test_observation_chain_must_be_contiguous(self) -> None:
        recorder = EpisodeRecorder(
            task=make_task(),
            policy_id="test-policy-v1",
            seed=42,
            initial_observation="initial",
        )
        with self.assertRaisesRegex(ValueError, "previous transition"):
            recorder.record_step(
                observation="stale observation",
                admissible_actions=["look"],
                action="look",
                next_observation="next",
                reward=0,
                terminated=False,
            )

    def test_cannot_record_after_terminal_step(self) -> None:
        recorder = EpisodeRecorder(
            task=make_task(),
            policy_id="test-policy-v1",
            seed=42,
            initial_observation="initial",
        )
        recorder.record_step(
            observation="initial",
            admissible_actions=["finish"],
            action="finish",
            next_observation="done",
            reward=1,
            terminated=True,
        )
        with self.assertRaisesRegex(RuntimeError, "environment terminated"):
            recorder.record_step(
                observation="done",
                admissible_actions=["look"],
                action="look",
                next_observation="impossible",
                reward=0,
                terminated=False,
            )

    def test_finish_is_single_use(self) -> None:
        recorder = EpisodeRecorder(
            task=make_task(),
            policy_id="test-policy-v1",
            seed=42,
            initial_observation="initial",
        )
        recorder.finish(
            success=False,
            termination_reason=TerminationReason.MAX_STEPS,
        )
        with self.assertRaisesRegex(RuntimeError, "only be called once"):
            recorder.finish(
                success=False,
                termination_reason=TerminationReason.MAX_STEPS,
            )

    def test_success_and_reason_must_agree(self) -> None:
        recorder = EpisodeRecorder(
            task=make_task(),
            policy_id="test-policy-v1",
            seed=42,
            initial_observation="initial",
        )
        with self.assertRaisesRegex(ValueError, "successful episodes"):
            recorder.finish(
                success=True,
                termination_reason=TerminationReason.MAX_STEPS,
            )
        episode = recorder.finish(
            success=False,
            termination_reason=TerminationReason.MAX_STEPS,
        )
        self.assertFalse(episode.success)

    def test_metadata_must_be_json_serializable(self) -> None:
        with self.assertRaisesRegex(TypeError, "non-JSON"):
            TaskSpec(
                task_id="id",
                split="train",
                task_type="type",
                goal="goal",
                metadata={"bad": object()},
            )

    def test_store_reports_corrupt_line_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "episodes.jsonl"
            path.write_text(json.dumps({"not": "an episode"}) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, r"episodes.jsonl:1"):
                EpisodeStore(path).load_all()


if __name__ == "__main__":
    unittest.main()
