"""Model-independent policy inputs and decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol

from evomo.data.schema import JsonValue, StepRecord, TaskSpec, _copy_json_mapping


@dataclass(frozen=True, slots=True)
class HistoryItem:
    """The compact transition history exposed to a policy."""

    observation: str
    action: str
    next_observation: str
    reward: float

    @classmethod
    def from_step(cls, step: StepRecord) -> "HistoryItem":
        return cls(
            observation=step.observation,
            action=step.action,
            next_observation=step.next_observation,
            reward=step.reward,
        )


@dataclass(frozen=True, slots=True)
class PolicyInput:
    """Everything a policy may use to choose the next environment action."""

    task: TaskSpec
    observation: str
    admissible_actions: tuple[str, ...]
    history: tuple[HistoryItem, ...]
    step_index: int

    def __post_init__(self) -> None:
        if not isinstance(self.task, TaskSpec):
            raise TypeError("task must be a TaskSpec")
        if not isinstance(self.observation, str):
            raise TypeError("observation must be a string")
        if not isinstance(self.step_index, int) or self.step_index < 0:
            raise ValueError("step_index must be a non-negative integer")

        actions = tuple(self.admissible_actions)
        if any(not isinstance(action, str) or not action.strip() for action in actions):
            raise ValueError("admissible_actions must contain non-empty strings")
        history = tuple(self.history)
        if any(not isinstance(item, HistoryItem) for item in history):
            raise TypeError("history must contain HistoryItem objects")
        if len(history) != self.step_index:
            raise ValueError("history length must equal step_index")
        if history and history[-1].next_observation != self.observation:
            raise ValueError("history does not lead to the current observation")
        object.__setattr__(self, "admissible_actions", actions)
        object.__setattr__(self, "history", history)


@dataclass(frozen=True, slots=True)
class ActionDecision:
    """A selected action plus auditable policy metadata."""

    action: str
    policy_id: str
    source: str
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("action", "policy_id", "source"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        object.__setattr__(self, "metadata", _copy_json_mapping("metadata", self.metadata))


class Policy(Protocol):
    """Interface consumed by RolloutRunner."""

    @property
    def policy_id(self) -> str: ...

    def reset(self, *, task: TaskSpec, seed: int) -> None: ...

    def decide(self, policy_input: PolicyInput) -> ActionDecision: ...
