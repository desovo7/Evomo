"""Stateful episode construction with transition-order checks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Mapping
from uuid import uuid4

from evomo.data.schema import Episode, JsonValue, StepRecord, TaskSpec, TerminationReason

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("clock must return timezone-aware datetimes")
    return value.astimezone(timezone.utc).isoformat()


class EpisodeRecorder:
    """Build an immutable Episode while enforcing valid data flow."""

    def __init__(
        self,
        *,
        task: TaskSpec,
        policy_id: str,
        seed: int,
        initial_observation: str,
        experience_version: str | None = None,
        episode_id: str | None = None,
        metadata: Mapping[str, JsonValue] | None = None,
        clock: Clock = _utc_now,
    ) -> None:
        # Validate constructor inputs before creating identity or timestamps.
        if not isinstance(task, TaskSpec):
            raise TypeError("task must be a TaskSpec")
        if not isinstance(initial_observation, str):
            raise TypeError("initial_observation must be a string")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise TypeError("seed must be an integer")
        if not isinstance(policy_id, str) or not policy_id.strip():
            raise ValueError("policy_id must be a non-empty string")

        self._task = task
        self._policy_id = policy_id
        self._seed = seed
        self._initial_observation = initial_observation
        self._experience_version = experience_version
        self._episode_id = episode_id or str(uuid4())
        self._metadata = dict(metadata or {})
        self._clock = clock
        self._started_at = _iso_utc(clock())
        self._steps: list[StepRecord] = []
        self._finished = False

    @property
    def next_observation(self) -> str:
        """Observation that the policy must consume for the next action."""

        if self._finished:
            raise RuntimeError("episode is already finished")
        if not self._steps:
            return self._initial_observation
        return self._steps[-1].next_observation

    @property
    def step_count(self) -> int:
        return len(self._steps)

    def record_step(
        self,
        *,
        observation: str,
        admissible_actions: tuple[str, ...] | list[str],
        action: str,
        next_observation: str,
        reward: float,
        terminated: bool,
        info: Mapping[str, Any] | None = None,
    ) -> StepRecord:
        if self._finished:
            raise RuntimeError("cannot record a step after finish()")
        if self._steps and self._steps[-1].terminated:
            raise RuntimeError("cannot record a step after the environment terminated")
        if observation != self.next_observation:
            raise ValueError(
                "observation does not match the previous transition's next_observation"
            )

        step = StepRecord(
            step_index=len(self._steps),
            observation=observation,
            admissible_actions=tuple(admissible_actions),
            action=action,
            next_observation=next_observation,
            reward=reward,
            terminated=terminated,
            info=dict(info or {}),
        )
        self._steps.append(step)
        return step

    def finish(
        self,
        *,
        success: bool,
        termination_reason: TerminationReason,
        metadata: Mapping[str, Any] | None = None,
    ) -> Episode:
        if self._finished:
            raise RuntimeError("finish() may only be called once")

        combined_metadata = dict(self._metadata)
        combined_metadata.update(metadata or {})
        episode = Episode(
            episode_id=self._episode_id,
            task=self._task,
            policy_id=self._policy_id,
            seed=self._seed,
            started_at=self._started_at,
            ended_at=_iso_utc(self._clock()),
            initial_observation=self._initial_observation,
            steps=tuple(self._steps),
            success=success,
            termination_reason=termination_reason,
            total_reward=sum(step.reward for step in self._steps),
            experience_version=self._experience_version,
            metadata=combined_metadata,
        )
        self._finished = True
        return episode
