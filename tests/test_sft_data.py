from __future__ import annotations

import json
from pathlib import Path

from evomo.data import Episode, StepRecord, TaskSpec, TerminationReason
from evomo.experience import ExperienceRule, ExperienceSet, save_experience_set
from evomo.training import build_sft_examples, write_sft_dataset


def experience() -> ExperienceSet:
    return ExperienceSet(
        version="exp-test",
        source_policy_id="planner",
        rules=(
            ExperienceRule(
                rule_id="ordered-task-recipe",
                kind="ordered_subgoals",
                task_types=("pick_and_place_simple",),
                instruction="Acquire and deliver the target.",
                evidence=(),
            ),
        ),
        source_episode_ids=("source",),
    )


def episode(*, success: bool) -> Episode:
    task = TaskSpec(
        task_id=f"train/task/{success}",
        split="train",
        task_type="pick_and_place_simple",
        goal="Put the apple on the table.",
        metadata={"pddl_params": {"object_target": "Apple", "parent_target": "Table"}},
    )
    step = StepRecord(
        step_index=0,
        observation="You see apple 1.",
        admissible_actions=("take apple 1 from counter 1", "look"),
        action="take apple 1 from counter 1",
        next_observation="You pick up apple 1.",
        reward=1 if success else 0,
        terminated=success,
        info={
            "policy": {
                "source": "experience_override",
                "metadata": {
                    "experience_override_reason": "take_visible_target_object",
                    "experience_rule_ids": ["ordered-task-recipe"],
                },
            }
        },
    )
    return Episode(
        episode_id=f"episode-{success}",
        task=task,
        policy_id="planner",
        seed=42,
        started_at="2026-01-01T00:00:00+00:00",
        ended_at="2026-01-01T00:00:01+00:00",
        initial_observation=step.observation,
        steps=(step,),
        success=success,
        termination_reason=TerminationReason.SUCCESS if success else TerminationReason.MAX_STEPS,
        total_reward=step.reward,
        experience_version="exp-test",
    )


def test_sft_uses_only_success_and_planner_final_action(tmp_path: Path) -> None:
    experiences = experience()
    examples = list(build_sft_examples([episode(success=False), episode(success=True)], experiences=experiences))

    assert len(examples) == 1
    assert examples[0].target == "<action>take apple 1 from counter 1</action>"
    assert examples[0].decision_source == "experience_override"
    assert "Learned experience rules" in examples[0].messages[1]["content"]

    experience_path = tmp_path / "experience.json"
    save_experience_set(experiences, experience_path)
    output = tmp_path / "sft.jsonl"
    manifest_path = tmp_path / "manifest.json"
    manifest = write_sft_dataset(
        examples,
        output_path=output,
        manifest_path=manifest_path,
        source_episode_root=tmp_path,
        experience_path=experience_path,
    )
    assert manifest["example_count"] == 1
    assert manifest["planner_override_example_count"] == 1
    assert json.loads(output.read_text().strip())["target"] == examples[0].target
