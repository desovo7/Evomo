from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from evomo.data import Episode, StepRecord, TaskSpec, TerminationReason
from evomo.experience import (
    ExperienceEvidence,
    ExperienceRule,
    ExperienceSet,
    choose_experience_override,
    evolve_experience_set,
    extract_failure_experiences,
    load_experience_set,
    promote_experience_by_task_type,
    save_experience_set,
)
from evomo.policies import reconstruct_alfworld_state


def make_task(task_type: str = "pick_cool_then_place_in_recep") -> TaskSpec:
    return TaskSpec(
        task_id=f"valid_train/{task_type}/trial",
        split="valid_train",
        task_type=task_type,
        goal="Place a cooled bowl in a cabinet.",
        metadata={
            "pddl_params": {
                "object_target": "Bowl",
                "parent_target": "Cabinet",
                "toggle_target": "",
            }
        },
    )


def make_failed_episode() -> Episode:
    task = make_task()
    steps = (
        StepRecord(
            0,
            "start",
            ("go to cabinet 1",),
            "go to cabinet 1",
            "You arrive at cabinet 1. In it, you see a cup 1.",
            0,
            False,
            {"policy": {"source": "model_generation", "metadata": {}}},
        ),
        StepRecord(
            1,
            "You arrive at cabinet 1. In it, you see a cup 1.",
            ("take cup 1 from cabinet 1",),
            "take cup 1 from cabinet 1",
            "You pick up the cup 1 from the cabinet 1.",
            0,
            False,
            {"policy": {"source": "model_generation", "metadata": {}}},
        ),
    )
    return Episode(
        episode_id="failed-episode",
        task=task,
        policy_id="policy-f",
        seed=42,
        started_at="2026-01-01T00:00:00+00:00",
        ended_at="2026-01-01T00:00:01+00:00",
        initial_observation="start",
        steps=steps,
        success=False,
        termination_reason=TerminationReason.MAX_STEPS,
        total_reward=0,
    )


def experience_set(task_type: str = "pick_cool_then_place_in_recep") -> ExperienceSet:
    evidence = ExperienceEvidence(
        "episode",
        f"valid_train/{task_type}-Bowl-None-Cabinet-1/trial",
        1,
        "take cup",
        "wrong target",
    )
    return ExperienceSet(
        version="exp-v1",
        source_policy_id="policy-f",
        source_episode_ids=("episode",),
        rules=(
            ExperienceRule(
                "target-object-lock",
                "target_object_lock",
                (task_type,),
                "Only manipulate the target object type.",
                (evidence,),
            ),
            ExperienceRule(
                "novelty-before-revisit",
                "novelty_exploration",
                (task_type,),
                "Explore new locations first.",
                (evidence,),
            ),
            ExperienceRule(
                "ordered-task-recipe",
                "ordered_subgoals",
                (task_type,),
                "Transform the target before delivery.",
                (evidence,),
            ),
        ),
    )


def test_extracts_versioned_rules_with_source_evidence(tmp_path: Path) -> None:
    experiences = extract_failure_experiences([make_failed_episode()], version="exp-v1")
    output = tmp_path / "experience.json"
    save_experience_set(experiences, output)

    restored = load_experience_set(output)

    assert restored == experiences
    assert [rule.rule_id for rule in restored.rules] == [
        "target-object-lock",
        "ordered-task-recipe",
    ]
    assert restored.rules[0].evidence[0].action == "take cup 1 from cabinet 1"
    assert restored.source_episode_ids == ("failed-episode",)


def test_visible_target_overrides_wrong_model_object() -> None:
    override = choose_experience_override(
        task=make_task(),
        state=reconstruct_alfworld_state(make_task(), (), "cabinet contents"),
        proposed_action="take cup 1 from cabinet 1",
        admissible_actions=(
            "take cup 1 from cabinet 1",
            "take bowl 2 from cabinet 1",
        ),
        experiences=experience_set(),
    )

    assert override is not None
    assert override.action_index == 1
    assert override.reason == "take_visible_target_object"
    assert override.rule_ids == ("target-object-lock",)


def test_target_must_be_cooled_before_delivery() -> None:
    task = make_task()
    state = reconstruct_alfworld_state(
        task,
        (),
        "holding bowl",
    )
    state = type(state)(
        **{
            **state.to_dict(),
            "inventory": "bowl 2",
        }
    )
    override = choose_experience_override(
        task=task,
        state=state,
        proposed_action="move bowl 2 to cabinet 1",
        admissible_actions=(
            "move bowl 2 to cabinet 1",
            "cool bowl 2 with fridge 1",
        ),
        experiences=experience_set(),
    )

    assert override is not None
    assert override.action_index == 1
    assert override.reason == "execute_required_cool"


def test_rules_do_not_apply_to_unlisted_task_type() -> None:
    task = make_task("pick_clean_then_place_in_recep")
    assert choose_experience_override(
        task=task,
        state=reconstruct_alfworld_state(task, (), "start"),
        proposed_action="look",
        admissible_actions=("look", "go to cabinet 1"),
        experiences=experience_set(),
    ) is None


def test_experience_module_imports_in_fresh_interpreter() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "from evomo.experience import ExperienceSet"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_evolves_location_type_diversity_from_repeated_search() -> None:
    task = make_task("pick_heat_then_place_in_recep")
    steps = []
    observation = "start"
    for index in range(4):
        next_observation = f"You arrive at cabinet {index + 1}. It is closed."
        steps.append(
            StepRecord(
                index,
                observation,
                (f"go to cabinet {index + 1}", "go to countertop 1"),
                f"go to cabinet {index + 1}",
                next_observation,
                0,
                False,
                {"policy": {"source": "experience_override", "metadata": {}}},
            )
        )
        observation = next_observation
    episode = Episode(
        "g-heat-failure",
        task,
        "policy-g",
        42,
        "2026-01-01T00:00:00+00:00",
        "2026-01-01T00:00:01+00:00",
        "start",
        tuple(steps),
        False,
        TerminationReason.MAX_STEPS,
        0,
    )

    evolved = evolve_experience_set(
        experience_set("pick_heat_then_place_in_recep"),
        [episode],
        version="exp-v2",
    )

    assert evolved.parent_version == "exp-v1"
    assert evolved.rules[-1].rule_id == "diversify-location-types"
    assert evolved.rules[-1].evidence[0].step_index == 3


def test_diversity_rule_prefers_new_location_type() -> None:
    task = make_task("pick_heat_then_place_in_recep")
    base = experience_set("pick_heat_then_place_in_recep")
    diversity = ExperienceRule(
        "diversify-location-types",
        "location_type_diversity",
        (task.task_type,),
        "Try a different location type.",
        base.rules[0].evidence,
    )
    evolved = ExperienceSet(
        "exp-v2",
        "policy-g",
        base.rules + (diversity,),
        ("g-failure",),
        parent_version="exp-v1",
    )
    state = reconstruct_alfworld_state(
        task,
        (),
        "You arrive at cabinet 1. It is open.",
    )

    override = choose_experience_override(
        task=task,
        state=state,
        proposed_action="go to cabinet 2",
        admissible_actions=("go to cabinet 2", "go to countertop 1"),
        experiences=evolved,
    )

    assert override is not None
    assert override.action_index == 1
    assert override.reason == "explore_unvisited_location_type"
    assert override.rule_ids == (
        "novelty-before-revisit",
        "diversify-location-types",
    )


def test_evolves_an_existing_diversity_rule_and_expands_task_scope() -> None:
    base = experience_set("pick_heat_then_place_in_recep")
    diversity = ExperienceRule(
        "diversify-location-types",
        "location_type_diversity",
        ("pick_heat_then_place_in_recep",),
        "Try a different location type.",
        base.rules[0].evidence,
    )
    exp_v2 = ExperienceSet(
        "exp-v2",
        "policy-g",
        base.rules + (diversity,),
        ("g-failure",),
        parent_version="exp-v1",
    )
    failure = make_failed_episode()

    exp_v3 = evolve_experience_set(exp_v2, [failure], version="exp-v3")

    assert exp_v3.parent_version == "exp-v2"
    assert exp_v3.source_policy_id == "policy-f"
    rules = {rule.rule_id: rule for rule in exp_v3.rules}
    assert "pick_cool_then_place_in_recep" in rules["target-object-lock"].task_types
    assert len(rules["target-object-lock"].evidence) == 2
    assert rules["diversify-location-types"] == diversity


def test_evolution_retains_evidence_for_every_expanded_task_type() -> None:
    base = experience_set("pick_heat_then_place_in_recep")
    base = ExperienceSet(
        "exp-v2",
        "policy-g",
        base.rules
        + (
            ExperienceRule(
                "diversify-location-types",
                "location_type_diversity",
                ("pick_heat_then_place_in_recep",),
                "Try a different location type.",
                base.rules[0].evidence,
            ),
        ),
        ("g-failure",),
        parent_version="exp-v1",
    )
    failures = []
    for task_type in ("pick_and_place_simple", "pick_two_obj_and_place"):
        original = make_failed_episode()
        failures.append(
            Episode(
                f"failure-{task_type}",
                make_task(task_type),
                original.policy_id,
                original.seed,
                original.started_at,
                original.ended_at,
                original.initial_observation,
                original.steps,
                False,
                original.termination_reason,
                0,
            )
        )

    evolved = evolve_experience_set(base, failures, version="exp-v2")
    rule = next(rule for rule in evolved.rules if rule.rule_id == "target-object-lock")

    for task_type in rule.task_types:
        if task_type in {"pick_and_place_simple", "pick_two_obj_and_place"}:
            assert any(
                task_type in evidence.task_id.split("/")
                or any(
                    segment.startswith(f"{task_type}-")
                    for segment in evidence.task_id.split("/")
                )
                for evidence in rule.evidence
            )


def test_two_object_rule_skips_an_instance_already_delivered() -> None:
    task = make_task("pick_two_obj_and_place")
    state = reconstruct_alfworld_state(task, (), "start")
    state = type(state)(
        **{
            **state.to_dict(),
            "known_placements": ("bowl 1 in/on cabinet 1",),
        }
    )

    override = choose_experience_override(
        task=task,
        state=state,
        proposed_action="take bowl 1 from cabinet 1",
        admissible_actions=(
            "take bowl 1 from cabinet 1",
            "take bowl 2 from cabinet 1",
        ),
        experiences=experience_set("pick_two_obj_and_place"),
    )

    assert override is not None
    assert override.action_index == 1
    assert override.reason == "take_visible_target_object"


def test_promotes_candidate_rules_only_for_selected_task_types() -> None:
    incumbent = experience_set("pick_heat_then_place_in_recep")
    candidate_rule = ExperienceRule(
        "target-object-lock",
        "target_object_lock",
        ("pick_heat_then_place_in_recep", "pick_two_obj_and_place"),
        incumbent.rules[0].instruction,
        incumbent.rules[0].evidence
        + (
            ExperienceEvidence(
                "two-failure",
                "valid_train/pick_two_obj_and_place-Bowl-None-Cabinet-1/trial",
                1,
                "take cup 1 from cabinet 1",
                "wrong target",
            ),
        ),
    )
    candidate = ExperienceSet(
        "exp-v2",
        "policy-h",
        (candidate_rule,) + incumbent.rules[1:],
        ("two-failure",),
        parent_version=incumbent.version,
    )

    promoted = promote_experience_by_task_type(
        incumbent,
        candidate,
        selected_versions={
            "pick_heat_then_place_in_recep": incumbent.version,
            "pick_two_obj_and_place": candidate.version,
        },
        version="champion-v1",
    )

    target_rule = next(rule for rule in promoted.rules if rule.rule_id == "target-object-lock")
    assert target_rule.task_types == (
        "pick_heat_then_place_in_recep",
        "pick_two_obj_and_place",
    )
    assert {item.episode_id for item in target_rule.evidence} == {
        "episode",
        "two-failure",
    }
    assert promoted.parent_version == candidate.version


def test_promotion_rejects_rule_semantic_drift() -> None:
    incumbent = experience_set()
    changed = ExperienceRule(
        incumbent.rules[0].rule_id,
        incumbent.rules[0].kind,
        incumbent.rules[0].task_types,
        "A different instruction.",
        incumbent.rules[0].evidence,
    )
    candidate = ExperienceSet(
        "exp-v2",
        "policy-h",
        (changed,) + incumbent.rules[1:],
        ("failure",),
        parent_version=incumbent.version,
    )

    with pytest.raises(ValueError, match="changed semantics"):
        promote_experience_by_task_type(
            incumbent,
            candidate,
            selected_versions={
                "pick_cool_then_place_in_recep": candidate.version,
            },
            version="champion-v1",
        )
