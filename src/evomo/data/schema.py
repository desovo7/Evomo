"""Versioned, serializable data contracts for ALFWorld trajectories."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping

SCHEMA_VERSION = 1
JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


class TerminationReason(str, Enum):
    """Why an episode stopped."""

    SUCCESS = "success"
    ENV_TERMINATED = "env_terminated"
    MAX_STEPS = "max_steps"
    POLICY_ERROR = "policy_error"
    ENV_ERROR = "env_error"


def _require_non_empty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _copy_json_mapping(name: str, value: Mapping[str, Any]) -> dict[str, JsonValue]:
    """Validate and detach metadata from caller-owned mutable objects."""

    def copy_value(path: str, item: Any) -> JsonValue:
        if item is None or isinstance(item, (bool, int, float, str)):
            return item
        if isinstance(item, Mapping):
            copied: dict[str, JsonValue] = {}
            for key, child in item.items():
                if not isinstance(key, str):
                    raise TypeError(f"{path} keys must be strings")
                copied[key] = copy_value(f"{path}.{key}", child)
            return copied
        if isinstance(item, (list, tuple)):
            return [copy_value(f"{path}[{index}]", child) for index, child in enumerate(item)]
        raise TypeError(f"{path} contains non-JSON value {type(item).__name__}")

    copied = copy_value(name, value)
    assert isinstance(copied, dict)
    return copied


@dataclass(frozen=True, slots=True)
class TaskSpec:
    """Stable identity and goal of one ALFWorld game."""

    task_id: str
    split: str
    task_type: str
    goal: str
    game_file: str | None = None
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("task_id", "split", "task_type", "goal"):
            _require_non_empty(name, getattr(self, name))
        if self.game_file is not None:
            _require_non_empty("game_file", self.game_file)
        object.__setattr__(self, "metadata", _copy_json_mapping("metadata", self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TaskSpec":
        return cls(**dict(value))


@dataclass(frozen=True, slots=True)
class StepRecord:
    """One environment transition: observation --action--> next observation."""

    step_index: int
    observation: str
    admissible_actions: tuple[str, ...]
    action: str
    next_observation: str
    reward: float
    terminated: bool
    info: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.step_index, int) or self.step_index < 0:
            raise ValueError("step_index must be a non-negative integer")
        if not isinstance(self.observation, str):
            raise TypeError("observation must be a string")
        if not isinstance(self.next_observation, str):
            raise TypeError("next_observation must be a string")
        _require_non_empty("action", self.action)
        actions = tuple(self.admissible_actions)
        if any(not isinstance(item, str) or not item.strip() for item in actions):
            raise ValueError("admissible_actions must contain non-empty strings")
        if not isinstance(self.reward, (int, float)) or isinstance(self.reward, bool):
            raise TypeError("reward must be numeric")
        if not isinstance(self.terminated, bool):
            raise TypeError("terminated must be bool")
        object.__setattr__(self, "admissible_actions", actions)
        object.__setattr__(self, "reward", float(self.reward))
        object.__setattr__(self, "info", _copy_json_mapping("info", self.info))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StepRecord":
        data = dict(value)
        data["admissible_actions"] = tuple(data.get("admissible_actions", ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class Episode:
    """A completed trajectory and the smallest unit written to storage."""

    episode_id: str
    task: TaskSpec
    policy_id: str
    seed: int
    started_at: str
    ended_at: str
    initial_observation: str
    steps: tuple[StepRecord, ...]
    success: bool
    termination_reason: TerminationReason
    total_reward: float
    schema_version: int = SCHEMA_VERSION
    experience_version: str | None = None
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty("episode_id", self.episode_id)
        _require_non_empty("policy_id", self.policy_id)
        _require_non_empty("started_at", self.started_at)
        _require_non_empty("ended_at", self.ended_at)
        if not isinstance(self.initial_observation, str):
            raise TypeError("initial_observation must be a string")
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise TypeError("seed must be an integer")
        if not isinstance(self.success, bool):
            raise TypeError("success must be bool")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported schema_version={self.schema_version}; expected {SCHEMA_VERSION}"
            )

        steps = tuple(self.steps)
        expected_indices = list(range(len(steps)))
        actual_indices = [step.step_index for step in steps]
        if actual_indices != expected_indices:
            raise ValueError(
                f"step indices must be contiguous from zero: got {actual_indices}"
            )
        if any(step.terminated for step in steps[:-1]):
            raise ValueError("only the final step may terminate the environment")
        if self.success and self.termination_reason is not TerminationReason.SUCCESS:
            raise ValueError("successful episodes must use termination_reason='success'")
        if not self.success and self.termination_reason is TerminationReason.SUCCESS:
            raise ValueError("termination_reason='success' requires success=True")

        object.__setattr__(self, "steps", steps)
        object.__setattr__(self, "total_reward", float(self.total_reward))
        object.__setattr__(self, "metadata", _copy_json_mapping("metadata", self.metadata))

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["termination_reason"] = self.termination_reason.value
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Episode":
        data = dict(value)
        data["task"] = TaskSpec.from_dict(data["task"])
        data["steps"] = tuple(StepRecord.from_dict(item) for item in data["steps"])
        data["termination_reason"] = TerminationReason(data["termination_reason"])
        return cls(**data)
