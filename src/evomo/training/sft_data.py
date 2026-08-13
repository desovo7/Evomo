"""Build faithful action-supervision examples from successful Episodes."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator

from evomo.data import Episode
from evomo.experience import ExperienceSet
from evomo.policies import HistoryItem, PolicyInput, PromptVariant
from evomo.policies.qwen_policy import build_action_messages


SFT_DATASET_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class SftExample:
    example_id: str
    episode_id: str
    task_id: str
    task_type: str
    step_index: int
    messages: tuple[dict[str, str], ...]
    target: str
    decision_source: str
    experience_override_reason: str | None
    experience_rule_ids: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def build_sft_examples(
    episodes: Iterable[Episode],
    *,
    experiences: ExperienceSet,
    max_history_items: int = 6,
) -> Iterator[SftExample]:
    """Yield one prompt/final-action pair per successful trajectory step."""

    if max_history_items < 0:
        raise ValueError("max_history_items must be non-negative")
    for episode in episodes:
        if not episode.success:
            continue
        if episode.experience_version != experiences.version:
            raise ValueError(
                f"{episode.episode_id}: episode experience version differs from SFT source"
            )
        history: list[HistoryItem] = []
        for step in episode.steps:
            policy_metadata = step.info.get("policy", {}).get("metadata", {})
            if not isinstance(policy_metadata, dict):
                raise ValueError(f"{episode.episode_id}: policy metadata is missing")
            policy_input = PolicyInput(
                task=episode.task,
                observation=step.observation,
                admissible_actions=step.admissible_actions,
                history=tuple(history),
                step_index=step.step_index,
            )
            # Historical episodes store the structured state rather than rendered text.
            # Re-render through the same deterministic state tracker for exact fidelity.
            from evomo.policies.alfworld_state import reconstruct_alfworld_state

            state_text = reconstruct_alfworld_state(
                episode.task, tuple(history), step.observation
            ).render()
            messages = build_action_messages(
                policy_input,
                max_history_items=max_history_items,
                prompt_variant=PromptVariant.EXPERIENCE_GUIDED_ACTION,
                state_text=state_text,
                experience_text=experiences.render(episode.task.task_type),
            )
            yield SftExample(
                example_id=f"{episode.episode_id}:{step.step_index}",
                episode_id=episode.episode_id,
                task_id=episode.task.task_id,
                task_type=episode.task.task_type,
                step_index=step.step_index,
                messages=tuple(messages),
                target=f"<action>{step.action}</action>",
                decision_source=str(step.info.get("policy", {}).get("source", "unknown")),
                experience_override_reason=(
                    str(policy_metadata["experience_override_reason"])
                    if policy_metadata.get("experience_override_reason")
                    else None
                ),
                experience_rule_ids=tuple(policy_metadata.get("experience_rule_ids", ())),
            )
            history.append(HistoryItem.from_step(step))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_sft_dataset(
    examples: Iterable[SftExample],
    *,
    output_path: str | Path,
    manifest_path: str | Path,
    source_episode_root: str | Path,
    experience_path: str | Path,
) -> dict:
    """Durably publish JSONL examples and a content-addressed manifest."""

    output_path = Path(output_path)
    manifest_path = Path(manifest_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + f".{os.getpid()}.tmp")
    count = 0
    episode_ids: set[str] = set()
    task_ids: set[str] = set()
    override_count = 0
    by_type: dict[str, int] = {}
    with temporary.open("w", encoding="utf-8") as stream:
        for example in examples:
            stream.write(json.dumps(example.to_dict(), ensure_ascii=False, separators=(",", ":")))
            stream.write("\n")
            count += 1
            episode_ids.add(example.episode_id)
            task_ids.add(example.task_id)
            override_count += int(example.experience_override_reason is not None)
            by_type[example.task_type] = by_type.get(example.task_type, 0) + 1
        stream.flush()
        os.fsync(stream.fileno())
    if count == 0:
        temporary.unlink(missing_ok=True)
        raise ValueError("SFT dataset contains no examples from successful episodes")
    temporary.replace(output_path)
    experience_path = Path(experience_path)
    manifest = {
        "schema_version": SFT_DATASET_SCHEMA_VERSION,
        "dataset_path": output_path.as_posix(),
        "dataset_sha256": _sha256(output_path),
        "dataset_bytes": output_path.stat().st_size,
        "source_episode_root": Path(source_episode_root).as_posix(),
        "experience_path": experience_path.as_posix(),
        "experience_sha256": _sha256(experience_path),
        "example_count": count,
        "source_success_episode_count": len(episode_ids),
        "source_task_count": len(task_ids),
        "planner_override_example_count": override_count,
        "task_type_example_counts": dict(sorted(by_type.items())),
        "selection": "every action in every native-success Episode",
        "target": "planner-final admissible action",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest
