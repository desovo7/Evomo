"""Deterministic random baseline over admissible actions."""

from __future__ import annotations

import random

from evomo.data.schema import TaskSpec
from evomo.policies.contracts import ActionDecision, PolicyInput


class RandomPolicy:
    """Choose uniformly from the environment's admissible actions."""

    def __init__(self, policy_id: str = "random-admissible-v1") -> None:
        if not isinstance(policy_id, str) or not policy_id.strip():
            raise ValueError("policy_id must be a non-empty string")
        self._policy_id = policy_id
        self._rng: random.Random | None = None
        self._task_id: str | None = None
        self._seed: int | None = None

    @property
    def policy_id(self) -> str:
        return self._policy_id

    def reset(self, *, task: TaskSpec, seed: int) -> None:
        if not isinstance(task, TaskSpec):
            raise TypeError("task must be a TaskSpec")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise TypeError("seed must be an integer")
        self._rng = random.Random(seed)
        self._task_id = task.task_id
        self._seed = seed

    def decide(self, policy_input: PolicyInput) -> ActionDecision:
        if self._rng is None or self._task_id is None or self._seed is None:
            raise RuntimeError("reset() must be called before decide()")
        if policy_input.task.task_id != self._task_id:
            raise ValueError("PolicyInput task does not match the reset task")
        if not policy_input.admissible_actions:
            raise ValueError("cannot choose an action from an empty admissible action set")

        selected_index = self._rng.randrange(len(policy_input.admissible_actions))
        return ActionDecision(
            action=policy_input.admissible_actions[selected_index],
            policy_id=self.policy_id,
            source="admissible_actions",
            metadata={
                "candidate_count": len(policy_input.admissible_actions),
                "selected_index": selected_index,
                "seed": self._seed,
            },
        )
