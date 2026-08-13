from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from evomo.data import EpisodeRecorder, TaskSpec, TerminationReason
from evomo.evaluation import compute_episode_metrics, write_trajectory_logs


def fixed_clock() -> datetime:
    return datetime(2026, 8, 13, tzinfo=timezone.utc)


class TrajectoryLogTest(unittest.TestCase):
    def test_writes_summary_steps_and_markdown(self) -> None:
        task = TaskSpec("task", "valid_train", "type", "goal")
        recorder = EpisodeRecorder(
            task=task,
            policy_id="policy",
            seed=42,
            initial_observation="same",
            clock=fixed_clock,
        )
        recorder.record_step(
            observation="same",
            admissible_actions=["look"],
            action="look",
            next_observation="same",
            reward=0,
            terminated=False,
            info={
                "success": False,
                "policy": {
                    "metadata": {
                        "raw_response": "<action>0</action>",
                        "reasoning": "",
                        "parse_ok": True,
                        "required_format_ok": True,
                        "parse_format": "tagged_index",
                    }
                },
            },
        )
        recorder.record_step(
            observation="same",
            admissible_actions=["look"],
            action="look",
            next_observation="done",
            reward=1,
            terminated=True,
            info={
                "success": True,
                "policy": {
                    "metadata": {
                        "raw_response": "0",
                        "reasoning": "finish",
                        "parse_ok": True,
                        "required_format_ok": True,
                        "parse_format": "bare_index",
                    }
                },
            },
        )
        episode = recorder.finish(success=True, termination_reason=TerminationReason.SUCCESS)
        metrics = compute_episode_metrics(episode)
        self.assertEqual(metrics.repeated_actions, 1)
        self.assertEqual(metrics.format_compliant_actions, 2)
        self.assertEqual(metrics.unchanged_observations, 1)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            written = write_trajectory_logs(episode, output)
            self.assertEqual(written, metrics)
            self.assertTrue((output / "summary.json").is_file())
            self.assertEqual(len((output / "steps.jsonl").read_text().splitlines()), 2)
            markdown = (output / "trajectory.md").read_text()
            self.assertIn("## Step 0", markdown)
            self.assertIn("Model response", markdown)
            self.assertIn("Action: `look`", markdown)


if __name__ == "__main__":
    unittest.main()
