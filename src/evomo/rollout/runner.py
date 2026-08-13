"""Connect task, environment, policy, recorder, and optional storage."""

from __future__ import annotations

from typing import Mapping

from evomo.data import Episode, EpisodeRecorder, EpisodeStore, TerminationReason
from evomo.data.schema import TaskSpec
from evomo.data.schema import JsonValue
from evomo.envs.contracts import EnvironmentAdapter
from evomo.policies.contracts import HistoryItem, Policy, PolicyInput


class RolloutRunner:
    """Run one policy episode with strict transition bookkeeping."""

    def __init__(self, *, max_steps: int = 50) -> None:
        if not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps <= 0:
            raise ValueError("max_steps must be a positive integer")
        self.max_steps = max_steps

    def run_episode(
        self,
        *,
        task: TaskSpec,
        environment: EnvironmentAdapter,
        policy: Policy,
        seed: int,
        store: EpisodeStore | None = None,
        experience_version: str | None = None,
        episode_metadata: Mapping[str, JsonValue] | None = None,
    ) -> Episode:
        """Run one episode and optionally append it after successful construction.

        Policy or environment exceptions are allowed to propagate. This avoids
        silently turning infrastructure failures into benchmark failures. The
        batch runner added later can decide how to retry and report them.
        """

        reset = environment.reset(task, seed=seed)
        policy.reset(task=task, seed=seed)
        recorder = EpisodeRecorder(
            task=task,
            policy_id=policy.policy_id,
            seed=seed,
            initial_observation=reset.observation,
            experience_version=experience_version,
            metadata={
                "max_steps": self.max_steps,
                "reset_info": dict(reset.info),
                **dict(episode_metadata or {}),
            },
        )

        observation = reset.observation
        admissible_actions = reset.admissible_actions
        history: list[HistoryItem] = []
        success = bool(reset.info.get("success", False))
        reason = TerminationReason.SUCCESS if success else TerminationReason.MAX_STEPS

        try:
            if not success:
                for step_index in range(self.max_steps):
                    policy_input = PolicyInput(
                        task=task,
                        observation=observation,
                        admissible_actions=admissible_actions,
                        history=tuple(history),
                        step_index=step_index,
                    )
                    decision = policy.decide(policy_input)
                    if decision.policy_id != policy.policy_id:
                        raise ValueError(
                            "ActionDecision.policy_id does not match the active policy"
                        )

                    transition = environment.step(decision.action)
                    reached_limit = step_index + 1 == self.max_steps
                    record = recorder.record_step(
                        observation=observation,
                        admissible_actions=admissible_actions,
                        action=decision.action,
                        next_observation=transition.observation,
                        reward=transition.reward,
                        terminated=transition.terminated,
                        info={
                            "environment": dict(transition.info),
                            "policy": {
                                "source": decision.source,
                                "metadata": dict(decision.metadata),
                            },
                            "success": transition.success,
                            "reached_runner_limit": reached_limit,
                        },
                    )
                    history.append(HistoryItem.from_step(record))

                    if transition.terminated:
                        success = transition.success
                        reason = (
                            TerminationReason.SUCCESS
                            if success
                            else TerminationReason.ENV_TERMINATED
                        )
                        break

                    observation = transition.observation
                    admissible_actions = transition.admissible_actions
        finally:
            environment.close()

        episode = recorder.finish(
            success=success,
            termination_reason=reason,
            metadata={"steps_executed": recorder.step_count},
        )
        if store is not None:
            store.append(episode)
        return episode
