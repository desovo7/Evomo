"""Model-independent environment input and output contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol

from evomo.data.schema import JsonValue, TaskSpec


def _validate_actions(actions: tuple[str, ...]) -> None:
    if any(not isinstance(action, str) or not action.strip() for action in actions):
        raise ValueError("admissible_actions must contain non-empty strings")


@dataclass(frozen=True, slots=True)
class EnvironmentReset:
    """Information available to a policy immediately after reset."""

    observation: str
    admissible_actions: tuple[str, ...]
    info: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.observation, str):
            raise TypeError("observation must be a string")
        actions = tuple(self.admissible_actions)
        _validate_actions(actions)
        object.__setattr__(self, "admissible_actions", actions)
        object.__setattr__(self, "info", dict(self.info))


@dataclass(frozen=True, slots=True)
class EnvironmentStep:
    """Result produced by applying one action to the environment."""

    observation: str
    admissible_actions: tuple[str, ...]
    reward: float
    terminated: bool
    success: bool
    info: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.observation, str):
            raise TypeError("observation must be a string")
        actions = tuple(self.admissible_actions)
        _validate_actions(actions)
        if not isinstance(self.reward, (int, float)) or isinstance(self.reward, bool):
            raise TypeError("reward must be numeric")
        if not isinstance(self.terminated, bool):
            raise TypeError("terminated must be bool")
        if not isinstance(self.success, bool):
            raise TypeError("success must be bool")
        if self.success and not self.terminated:
            raise ValueError("a successful step must terminate the episode")
        object.__setattr__(self, "admissible_actions", actions)
        object.__setattr__(self, "reward", float(self.reward))
        object.__setattr__(self, "info", dict(self.info))


class EnvironmentAdapter(Protocol):
    """Minimal interface consumed by the future rollout runner."""

    def reset(self, task: TaskSpec, *, seed: int) -> EnvironmentReset: ...

    def step(self, action: str) -> EnvironmentStep: ...

    def close(self) -> None: ...
