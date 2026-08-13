"""Machine-readable and human-readable logs for completed trajectories."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from evomo.data import Episode


@dataclass(frozen=True, slots=True)
class EpisodeMetrics:
    steps: int
    success: bool
    total_reward: float
    parsed_actions: int
    format_compliant_actions: int
    fallback_actions: int
    repaired_actions: int
    experience_overrides: int
    repeated_actions: int
    unchanged_observations: int
    unique_actions: int

    def to_dict(self) -> dict:
        return asdict(self)


def compute_episode_metrics(episode: Episode) -> EpisodeMetrics:
    parsed_actions = 0
    format_compliant_actions = 0
    repeated_actions = 0
    unchanged_observations = 0
    repaired_actions = 0
    experience_overrides = 0
    actions: list[str] = []
    for step in episode.steps:
        policy_info = step.info.get("policy", {})
        policy_metadata = policy_info.get("metadata", {})
        parsed_actions += int(bool(policy_metadata.get("parse_ok", False)))
        format_compliant_actions += int(bool(policy_metadata.get("required_format_ok", False)))
        repaired_actions += int(policy_info.get("source") == "state_prerequisite_repair")
        experience_overrides += int(policy_info.get("source") == "experience_override")
        unchanged_observations += int(step.observation == step.next_observation)
        if actions and actions[-1] == step.action:
            repeated_actions += 1
        actions.append(step.action)
    return EpisodeMetrics(
        steps=len(episode.steps),
        success=episode.success,
        total_reward=episode.total_reward,
        parsed_actions=parsed_actions,
        format_compliant_actions=format_compliant_actions,
        fallback_actions=sum(
            int(step.info.get("policy", {}).get("source") == "fallback_first_admissible")
            for step in episode.steps
        ),
        repaired_actions=repaired_actions,
        experience_overrides=experience_overrides,
        repeated_actions=repeated_actions,
        unchanged_observations=unchanged_observations,
        unique_actions=len(set(actions)),
    )


def write_trajectory_logs(episode: Episode, output_directory: str | Path) -> EpisodeMetrics:
    """Write summary JSON, step JSONL, and a readable Markdown trace."""

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    metrics = compute_episode_metrics(episode)
    summary = {
        "episode_id": episode.episode_id,
        "task_id": episode.task.task_id,
        "goal": episode.task.goal,
        "task_type": episode.task.task_type,
        "policy_id": episode.policy_id,
        "seed": episode.seed,
        "termination_reason": episode.termination_reason.value,
        "metrics": metrics.to_dict(),
    }
    (output_directory / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with (output_directory / "steps.jsonl").open("w", encoding="utf-8") as stream:
        for step in episode.steps:
            policy_metadata = step.info.get("policy", {}).get("metadata", {})
            record = {
                "step_index": step.step_index,
                "observation": step.observation,
                "admissible_actions": list(step.admissible_actions),
                "raw_response": policy_metadata.get("raw_response", ""),
                "decision_source": step.info.get("policy", {}).get("source"),
                "reasoning": policy_metadata.get("reasoning", ""),
                "parse_ok": policy_metadata.get("parse_ok", False),
                "required_format_ok": policy_metadata.get("required_format_ok", False),
                "parse_format": policy_metadata.get("parse_format"),
                "state_before": policy_metadata.get("state_before"),
                "proposed_action": policy_metadata.get("proposed_action"),
                "repair_reason": policy_metadata.get("repair_reason"),
                "experience_version": policy_metadata.get("experience_version"),
                "applicable_experience_rule_ids": policy_metadata.get(
                    "applicable_experience_rule_ids", []
                ),
                "experience_override_reason": policy_metadata.get(
                    "experience_override_reason"
                ),
                "experience_rule_ids": policy_metadata.get("experience_rule_ids", []),
                "action": step.action,
                "next_observation": step.next_observation,
                "reward": step.reward,
                "terminated": step.terminated,
                "success": step.info.get("success", False),
            }
            stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            stream.write("\n")

    lines = [
        f"# Trajectory: {episode.policy_id}",
        "",
        f"- Task: `{episode.task.task_id}`",
        f"- Goal: {episode.task.goal}",
        f"- Result: success={episode.success}, reason={episode.termination_reason.value}",
        f"- Steps: {metrics.steps}",
        f"- Parsed/fallback: {metrics.parsed_actions}/{metrics.fallback_actions}",
        f"- Repeated actions: {metrics.repeated_actions}",
        f"- Unchanged observations: {metrics.unchanged_observations}",
        "",
    ]
    for step in episode.steps:
        policy_metadata = step.info.get("policy", {}).get("metadata", {})
        lines.extend(
            [
                f"## Step {step.step_index}",
                "",
                "Observation:",
                "```text",
                step.observation,
                "```",
                "",
                f"Model response: `{policy_metadata.get('raw_response', '')}`",
                f"Parsed: `{policy_metadata.get('parse_ok', False)}` "
                f"(`{policy_metadata.get('parse_format')}`)",
                f"Action: `{step.action}`",
                f"Proposed action: `{policy_metadata.get('proposed_action')}`",
                f"Repair reason: `{policy_metadata.get('repair_reason')}`",
                f"Experience version: `{policy_metadata.get('experience_version')}`",
                f"Experience override: `{policy_metadata.get('experience_override_reason')}`",
                f"Experience rules: `{policy_metadata.get('experience_rule_ids', [])}`",
                "",
                "Reconstructed state before decision:",
                "```json",
                json.dumps(
                    policy_metadata.get("state_before"),
                    ensure_ascii=False,
                    indent=2,
                ),
                "```",
                "",
                "Result:",
                "```text",
                step.next_observation,
                "```",
                "",
            ]
        )
    (output_directory / "trajectory.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )
    return metrics
