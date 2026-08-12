from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from evomo.data import EpisodeStore, TaskSpec, TerminationReason
from evomo.envs.contracts import EnvironmentReset, EnvironmentStep
from evomo.policies import HistoryItem, PolicyInput, RandomPolicy
from evomo.rollout import RolloutRunner


def make_task() -> TaskSpec:
    return TaskSpec(
        task_id="train/problem/trial",
        split="train",
        task_type="pick_and_place_simple",
        goal="Put the apple on the table.",
        game_file="train/problem/trial/game.tw-pddl",
    )


class FakeEnvironment:
    def __init__(self, transitions: list[EnvironmentStep]) -> None:
        self.transitions = list(transitions)
        self.actions: list[str] = []
        self.closed = False

    def reset(self, task: TaskSpec, *, seed: int) -> EnvironmentReset:
        return EnvironmentReset(
            observation="initial",
            admissible_actions=("look", "go north", "go south"),
            info={"task_id": task.task_id, "requested_seed": seed, "success": False},
        )

    def step(self, action: str) -> EnvironmentStep:
        self.actions.append(action)
        if not self.transitions:
            raise AssertionError("test environment ran out of transitions")
        return self.transitions.pop(0)

    def close(self) -> None:
        self.closed = True


class FailingPolicy(RandomPolicy):
    def decide(self, policy_input: PolicyInput):
        raise RuntimeError("policy failed")


def continuing_step(index: int) -> EnvironmentStep:
    return EnvironmentStep(
        observation=f"observation-{index}",
        admissible_actions=("look", "go north", "go south"),
        reward=0,
        terminated=False,
        success=False,
        info={"transition": index},
    )


class RandomPolicyTest(unittest.TestCase):
    def test_same_seed_produces_same_decisions(self) -> None:
        task = make_task()
        inputs = [
            PolicyInput(
                task=task,
                observation="initial",
                admissible_actions=("a", "b", "c"),
                history=(),
                step_index=0,
            )
        ]
        decisions: list[str] = []
        for _ in range(2):
            policy = RandomPolicy()
            policy.reset(task=task, seed=42)
            decisions.append(policy.decide(inputs[0]).action)
        self.assertEqual(decisions[0], decisions[1])

    def test_empty_action_set_fails(self) -> None:
        task = make_task()
        policy = RandomPolicy()
        policy.reset(task=task, seed=42)
        policy_input = PolicyInput(
            task=task,
            observation="initial",
            admissible_actions=(),
            history=(),
            step_index=0,
        )
        with self.assertRaisesRegex(ValueError, "empty"):
            policy.decide(policy_input)

    def test_policy_input_requires_contiguous_history(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not lead"):
            PolicyInput(
                task=make_task(),
                observation="current",
                admissible_actions=("look",),
                history=(HistoryItem("old", "look", "different", 0),),
                step_index=1,
            )


class RolloutRunnerTest(unittest.TestCase):
    def test_max_steps_episode_is_stored_and_read_back(self) -> None:
        task = make_task()
        environment = FakeEnvironment([continuing_step(1), continuing_step(2)])
        policy = RandomPolicy()

        with tempfile.TemporaryDirectory() as directory:
            store = EpisodeStore(Path(directory) / "episodes.jsonl")
            episode = RolloutRunner(max_steps=2).run_episode(
                task=task,
                environment=environment,
                policy=policy,
                seed=42,
                store=store,
            )

            self.assertEqual(store.load_all(), [episode])
        self.assertEqual(episode.termination_reason, TerminationReason.MAX_STEPS)
        self.assertFalse(episode.success)
        self.assertEqual(len(episode.steps), 2)
        self.assertFalse(episode.steps[-1].terminated)
        self.assertTrue(episode.steps[-1].info["reached_runner_limit"])
        self.assertIn("selected_index", episode.steps[0].info["policy"]["metadata"])
        self.assertTrue(environment.closed)

    def test_successful_environment_transition_finishes_episode(self) -> None:
        environment = FakeEnvironment(
            [
                EnvironmentStep(
                    observation="task completed",
                    admissible_actions=(),
                    reward=1,
                    terminated=True,
                    success=True,
                )
            ]
        )
        episode = RolloutRunner(max_steps=10).run_episode(
            task=make_task(),
            environment=environment,
            policy=RandomPolicy(),
            seed=7,
        )

        self.assertTrue(episode.success)
        self.assertEqual(episode.termination_reason, TerminationReason.SUCCESS)
        self.assertEqual(episode.total_reward, 1.0)
        self.assertEqual(len(episode.steps), 1)
        self.assertTrue(episode.steps[0].terminated)
        self.assertTrue(environment.closed)

    def test_non_success_terminal_transition_is_preserved(self) -> None:
        environment = FakeEnvironment(
            [
                EnvironmentStep(
                    observation="game over",
                    admissible_actions=(),
                    reward=0,
                    terminated=True,
                    success=False,
                )
            ]
        )
        episode = RolloutRunner(max_steps=10).run_episode(
            task=make_task(),
            environment=environment,
            policy=RandomPolicy(),
            seed=7,
        )
        self.assertEqual(episode.termination_reason, TerminationReason.ENV_TERMINATED)
        self.assertFalse(episode.success)

    def test_environment_closes_when_policy_raises(self) -> None:
        environment = FakeEnvironment([continuing_step(1)])
        with self.assertRaisesRegex(RuntimeError, "policy failed"):
            RolloutRunner(max_steps=2).run_episode(
                task=make_task(),
                environment=environment,
                policy=FailingPolicy(),
                seed=7,
            )
        self.assertTrue(environment.closed)


if __name__ == "__main__":
    unittest.main()
