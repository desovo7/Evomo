"""Discover ALFWorld trials and convert their metadata into TaskSpec objects."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from evomo.data.schema import TaskSpec

DEFAULT_SPLITS = ("train", "valid_train", "valid_seen", "valid_unseen")
DATASET_DIRECTORY_NAME = "json_2.1.1"


class TaskDiscoveryError(ValueError):
    """Raised when an ALFWorld trial has invalid or incomplete metadata."""


@dataclass(frozen=True, slots=True)
class SplitReport:
    """Discovery counts for one split."""

    split: str
    trajectories_found: int
    tasks_included: int
    missing_game_files: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DiscoveryReport:
    """Auditable summary of one discovery pass."""

    dataset_root: str
    playable_only: bool
    splits: tuple[SplitReport, ...]

    @property
    def trajectories_found(self) -> int:
        return sum(item.trajectories_found for item in self.splits)

    @property
    def tasks_included(self) -> int:
        return sum(item.tasks_included for item in self.splits)

    @property
    def missing_game_files(self) -> int:
        return sum(item.missing_game_files for item in self.splits)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_root": self.dataset_root,
            "playable_only": self.playable_only,
            "trajectories_found": self.trajectories_found,
            "tasks_included": self.tasks_included,
            "missing_game_files": self.missing_game_files,
            "splits": [item.to_dict() for item in self.splits],
        }


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """Discovered tasks together with the counts that produced them."""

    tasks: tuple[TaskSpec, ...]
    report: DiscoveryReport


def resolve_dataset_root(path: str | Path) -> Path:
    """Resolve either ALFWORLD_DATA or its json_2.1.1 child directory."""

    candidate = Path(path).expanduser().resolve()
    versioned_child = candidate / DATASET_DIRECTORY_NAME
    if versioned_child.is_dir():
        candidate = versioned_child
    if not candidate.is_dir():
        raise FileNotFoundError(f"ALFWorld dataset root does not exist: {candidate}")
    return candidate


def _validate_splits(splits: Sequence[str]) -> tuple[str, ...]:
    if not splits:
        raise ValueError("at least one ALFWorld split is required")

    normalized: list[str] = []
    seen: set[str] = set()
    for split in splits:
        if not isinstance(split, str) or not split.strip():
            raise ValueError("split names must be non-empty strings")
        split = split.strip()
        if Path(split).name != split or split in {".", ".."}:
            raise ValueError(f"invalid split name: {split!r}")
        if split in seen:
            raise ValueError(f"duplicate split: {split}")
        seen.add(split)
        normalized.append(split)
    return tuple(normalized)


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise TaskDiscoveryError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise TaskDiscoveryError(f"expected a JSON object in {path}")
    return value


def _require_text(metadata: Mapping[str, Any], key: str, path: Path) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TaskDiscoveryError(f"{path}: {key} must be a non-empty string")
    return value.strip()


def _extract_goal(metadata: Mapping[str, Any], path: Path) -> tuple[str, int, int]:
    annotations = metadata.get("turk_annotations")
    if not isinstance(annotations, Mapping):
        raise TaskDiscoveryError(f"{path}: turk_annotations must be an object")
    values = annotations.get("anns")
    if not isinstance(values, list):
        raise TaskDiscoveryError(f"{path}: turk_annotations.anns must be a list")

    for index, annotation in enumerate(values):
        if not isinstance(annotation, Mapping):
            continue
        task_description = annotation.get("task_desc")
        if isinstance(task_description, str) and task_description.strip():
            goal = " ".join(task_description.split())
            return goal, len(values), index
    raise TaskDiscoveryError(f"{path}: no non-empty task_desc annotation")


def _extract_scene_number(metadata: Mapping[str, Any], path: Path) -> int:
    scene = metadata.get("scene")
    if not isinstance(scene, Mapping):
        raise TaskDiscoveryError(f"{path}: scene must be an object")
    scene_number = scene.get("scene_num")
    if not isinstance(scene_number, int) or isinstance(scene_number, bool):
        raise TaskDiscoveryError(f"{path}: scene.scene_num must be an integer")
    return scene_number


def _task_from_trial(
    *,
    dataset_root: Path,
    split: str,
    trajectory_file: Path,
    game_file: Path,
) -> TaskSpec:
    metadata = _load_json_object(trajectory_file)
    raw_task_id = _require_text(metadata, "task_id", trajectory_file)
    task_type = _require_text(metadata, "task_type", trajectory_file)
    goal, annotation_count, goal_annotation_index = _extract_goal(metadata, trajectory_file)
    scene_number = _extract_scene_number(metadata, trajectory_file)

    pddl_params = metadata.get("pddl_params")
    if not isinstance(pddl_params, Mapping):
        raise TaskDiscoveryError(f"{trajectory_file}: pddl_params must be an object")

    trial_directory = trajectory_file.parent
    problem_directory = trial_directory.parent
    relative_trial = trial_directory.relative_to(dataset_root).as_posix()
    relative_trajectory = trajectory_file.relative_to(dataset_root).as_posix()
    relative_game = game_file.relative_to(dataset_root).as_posix() if game_file.is_file() else None

    return TaskSpec(
        task_id=relative_trial,
        split=split,
        task_type=task_type,
        goal=goal,
        game_file=relative_game,
        metadata={
            "alfworld_task_id": raw_task_id,
            "problem_id": problem_directory.name,
            "trial_id": trial_directory.name,
            "scene_num": scene_number,
            "pddl_params": dict(pddl_params),
            "annotation_count": annotation_count,
            "goal_source": f"turk_annotations.anns[{goal_annotation_index}].task_desc",
            "trajectory_file": relative_trajectory,
        },
    )


def discover_tasks(
    data_root: str | Path,
    *,
    splits: Sequence[str] = DEFAULT_SPLITS,
    playable_only: bool = True,
) -> DiscoveryResult:
    """Discover tasks in deterministic path order.

    A trial is playable when ``game.tw-pddl`` exists next to
    ``traj_data.json``. Missing game files are counted in the report and are
    excluded by default. Malformed metadata always fails loudly.
    """

    dataset_root = resolve_dataset_root(data_root)
    normalized_splits = _validate_splits(splits)
    tasks: list[TaskSpec] = []
    reports: list[SplitReport] = []
    task_ids: set[str] = set()

    for split in normalized_splits:
        split_directory = dataset_root / split
        if not split_directory.is_dir():
            raise FileNotFoundError(f"ALFWorld split does not exist: {split_directory}")

        trajectory_files = sorted(split_directory.glob("*/*/traj_data.json"))
        included = 0
        missing_games = 0
        for trajectory_file in trajectory_files:
            game_file = trajectory_file.with_name("game.tw-pddl")
            if not game_file.is_file():
                missing_games += 1
                if playable_only:
                    continue

            task = _task_from_trial(
                dataset_root=dataset_root,
                split=split,
                trajectory_file=trajectory_file,
                game_file=game_file,
            )
            if task.task_id in task_ids:
                raise TaskDiscoveryError(f"duplicate task_id discovered: {task.task_id}")
            task_ids.add(task.task_id)
            tasks.append(task)
            included += 1

        reports.append(
            SplitReport(
                split=split,
                trajectories_found=len(trajectory_files),
                tasks_included=included,
                missing_game_files=missing_games,
            )
        )

    return DiscoveryResult(
        tasks=tuple(tasks),
        report=DiscoveryReport(
            dataset_root=str(dataset_root),
            playable_only=playable_only,
            splits=tuple(reports),
        ),
    )
