from dataclasses import replace
from datetime import UTC, datetime

import pytest

from evomo.data import Episode, TaskSpec, TerminationReason
from evomo.experience import validate_evolution_source


def make_failed_episode() -> Episode:
    task = TaskSpec(
        task_id="valid_train/pick_and_place_simple/trial",
        split="valid_train",
        task_type="pick_and_place_simple",
        goal="Put an apple in the bowl.",
    )
    timestamp = datetime.now(UTC).isoformat()
    return Episode(
        episode_id="failure",
        task=task,
        policy_id="policy-i",
        seed=42,
        started_at=timestamp,
        ended_at=timestamp,
        initial_observation="start",
        steps=(),
        success=False,
        termination_reason=TerminationReason.MAX_STEPS,
        total_reward=0.0,
    )


def test_evolution_source_accepts_declared_development_split() -> None:
    episode = make_failed_episode()

    assert validate_evolution_source(
        [episode], expected_split="valid_train"
    ) == (episode,)


@pytest.mark.parametrize("split", ["valid_seen", "valid_unseen"])
def test_evolution_source_rejects_evaluation_split(split: str) -> None:
    episode = make_failed_episode()
    evaluation_task = replace(episode.task, split=split)

    with pytest.raises(ValueError, match="role 'evaluation'"):
        validate_evolution_source(
            [replace(episode, task=evaluation_task)], expected_split=split
        )


def test_evolution_source_rejects_mixed_or_mislabeled_episodes() -> None:
    episode = make_failed_episode()
    unseen = replace(episode, task=replace(episode.task, split="valid_unseen"))

    with pytest.raises(ValueError, match="observed.*valid_unseen"):
        validate_evolution_source(
            [episode, unseen], expected_split="valid_train"
        )


def test_evolution_source_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="no episodes"):
        validate_evolution_source([], expected_split="valid_train")
