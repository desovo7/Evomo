"""Content-addressed contract for one complete experience-evolution cycle."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from evomo.data import EpisodeStore
from evomo.experience import DEVELOPMENT_SPLITS, EVALUATION_SPLITS, load_experience_set

from .candidate_gate import audit_experience_candidate_decision, file_sha256

EVOLUTION_CYCLE_SCHEMA_VERSION = 1


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def directory_sha256(path: str | Path) -> tuple[str, int, int]:
    """Hash a tree using length-framed relative paths and file contents."""

    root = Path(path)
    if not root.is_dir():
        raise ValueError(f"trajectory directory is missing: {root}")
    files = tuple(sorted(item for item in root.rglob("*") if item.is_file()))
    if not files:
        raise ValueError(f"trajectory directory is empty: {root}")
    if any(item.is_symlink() for item in files):
        raise ValueError(f"trajectory directory contains a symlink: {root}")
    digest = hashlib.sha256()
    total_bytes = 0
    for item in files:
        relative = item.relative_to(root).as_posix().encode()
        payload = item.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
        total_bytes += len(payload)
    return digest.hexdigest(), len(files), total_bytes


def _file_record(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"artifact file is missing: {path}")
    return {"kind": "file", "path": path.as_posix(), "sha256": file_sha256(path), "bytes": path.stat().st_size}


def _directory_record(path: str | Path) -> dict:
    path = Path(path)
    digest, count, size = directory_sha256(path)
    return {"kind": "directory", "path": path.as_posix(), "sha256": digest, "file_count": count, "bytes": size}


def _checked_artifact(name: str, record: Mapping) -> Path:
    path = Path(str(record.get("path", "")))
    if record.get("kind") == "file":
        actual = _file_record(path)
    elif record.get("kind") == "directory":
        actual = _directory_record(path)
    else:
        raise ValueError(f"{name}: unsupported artifact kind")
    if actual != dict(record):
        raise ValueError(f"{name}: content-addressed artifact differs from manifest")
    return path


def _episodes(root: Path):
    paths = sorted(root.rglob("episode.jsonl"))
    if not paths:
        raise ValueError(f"{root}: contains no episode trajectories")
    result = []
    for path in paths:
        rows = EpisodeStore(path).load_all()
        if len(rows) != 1:
            raise ValueError(f"{path}: expected exactly one episode")
        result.append(rows[0])
    return result


def _validate_episode_transitions(episodes) -> None:
    for episode in episodes:
        previous = episode.initial_observation
        for step in episode.steps:
            if step.observation != previous:
                raise ValueError(f"{episode.episode_id}: broken observation chain")
            if step.action not in step.admissible_actions:
                raise ValueError(f"{episode.episode_id}: inadmissible recorded action")
            previous = step.next_observation
        if episode.success:
            if (
                not episode.steps
                or not episode.steps[-1].terminated
                or episode.steps[-1].reward <= 0
            ):
                raise ValueError(
                    f"{episode.episode_id}: success lacks native terminal reward"
                )


def _validate_cycle(paths: Mapping[str, Path]) -> dict:
    incumbent = load_experience_set(paths["incumbent_experience"])
    candidate = load_experience_set(paths["candidate_experience"])
    development = _json(paths["development_summary"])
    development_audit = _json(paths["development_audit"])
    evolution_audit = _json(paths["evolution_audit"])
    comparison = _json(paths["comparison"])
    validation_audit = _json(paths["validation_audit"])
    decision = _json(paths["decision"])

    run = development.get("run", {})
    source_split = run.get("split")
    if source_split not in DEVELOPMENT_SPLITS:
        raise ValueError("development summary does not use a development split")
    if run.get("experience_version") != incumbent.version or run.get("experience_sha256") != file_sha256(paths["incumbent_experience"]):
        raise ValueError("development rollout did not use the content-addressed incumbent")
    episodes = _episodes(paths["development_trajectories"])
    _validate_episode_transitions(episodes)
    episode_ids = [item.episode_id for item in episodes]
    task_ids = [item.task.task_id for item in episodes]
    if len(episode_ids) != len(set(episode_ids)) or len(task_ids) != len(set(task_ids)):
        raise ValueError("development trajectories contain duplicate IDs")
    if set(task_ids) != set(run.get("task_ids", ())) or len(episodes) != development.get("task_count"):
        raise ValueError("development trajectories differ from summary")
    success_count = sum(item.success for item in episodes)
    if success_count != development.get("success_count") or {item.task.split for item in episodes} != {source_split}:
        raise ValueError("development trajectory outcomes differ from summary")
    if {item.policy_id for item in episodes} != {development.get("policy_id")}:
        raise ValueError("development policy differs from summary")
    observed_versions = {step.info.get("policy", {}).get("metadata", {}).get("experience_version") for episode in episodes for step in episode.steps}
    if observed_versions != {incumbent.version}:
        raise ValueError("development steps did not consistently use the incumbent")
    failed_ids = {item.episode_id for item in episodes if not item.success}
    if set(candidate.source_episode_ids) != failed_ids:
        raise ValueError("candidate sources are not exactly the failed development episodes")
    if candidate.parent_version != incumbent.version or candidate.source_policy_id != development.get("policy_id"):
        raise ValueError("candidate lineage differs from development rollout")

    if development_audit.get("status") != "passed" or development_audit.get("protocol_role") != "development":
        raise ValueError("development trajectory audit did not pass")
    audited = {item.get("variant"): item for item in development_audit.get("variants", ())}.get(development.get("variant"))
    if not audited or audited.get("episode_count") != len(episodes) or audited.get("success_count") != success_count:
        raise ValueError("development trajectory audit counts mismatch")
    expected_evolution = {"status": "passed", "base_version": incumbent.version, "child_version": candidate.version, "parent_version": incumbent.version, "source_policy_id": candidate.source_policy_id, "source_split": source_split, "source_role": "development", "source_episode_count": len(failed_ids)}
    for key, expected in expected_evolution.items():
        if evolution_audit.get(key) != expected:
            raise ValueError(f"evolution audit {key} mismatch")

    if comparison.get("split") not in EVALUATION_SPLITS:
        raise ValueError("comparison does not use an evaluation split")
    paired = comparison.get("paired_success", {})
    variants = {str(item.get("variant")): item for item in comparison.get("variants", ())}
    if len(variants) != 2:
        raise ValueError("comparison must contain exactly two variants")
    baseline_variant, candidate_variant = str(paired.get("baseline")), str(paired.get("candidate"))
    if baseline_variant == candidate_variant:
        raise ValueError("paired validation variants must differ")
    baseline = _json(paths["validation_incumbent_summary"])
    proposed = _json(paths["validation_candidate_summary"])
    for label, summary, variant, experience, experience_path in (("incumbent", baseline, baseline_variant, incumbent, paths["incumbent_experience"]), ("candidate", proposed, candidate_variant, candidate, paths["candidate_experience"])):
        summary_run = summary.get("run", {})
        if summary.get("variant") != variant or variants.get(variant) != summary:
            raise ValueError(f"comparison does not embed the exact {label} summary")
        if summary_run.get("split") != comparison.get("split") or summary_run.get("experience_version") != experience.version or summary_run.get("experience_sha256") != file_sha256(experience_path):
            raise ValueError(f"validation {label} run contract mismatch")
    if set(baseline.get("run", {}).get("task_ids", ())) != set(proposed.get("run", {}).get("task_ids", ())):
        raise ValueError("paired validation summaries cover different tasks")
    validation_episodes = _episodes(paths["validation_trajectories"])
    _validate_episode_transitions(validation_episodes)
    by_policy = {}
    for episode in validation_episodes:
        by_policy.setdefault(episode.policy_id, []).append(episode)
    expected_policies = {baseline.get("policy_id"), proposed.get("policy_id")}
    if set(by_policy) != expected_policies:
        raise ValueError("validation trajectories contain unexpected policies")
    for label, summary, experience in (
        ("incumbent", baseline, incumbent),
        ("candidate", proposed, candidate),
    ):
        policy_episodes = by_policy[summary["policy_id"]]
        policy_task_ids = [episode.task.task_id for episode in policy_episodes]
        if len(policy_task_ids) != len(set(policy_task_ids)):
            raise ValueError(f"validation {label} trajectories contain duplicate tasks")
        if set(policy_task_ids) != set(summary.get("run", {}).get("task_ids", ())):
            raise ValueError(f"validation {label} trajectories differ from summary")
        if len(policy_episodes) != summary.get("task_count") or sum(
            episode.success for episode in policy_episodes
        ) != summary.get("success_count"):
            raise ValueError(f"validation {label} outcomes differ from summary")
        if {episode.task.split for episode in policy_episodes} != {
            comparison.get("split")
        }:
            raise ValueError(f"validation {label} trajectories use the wrong split")
        versions = {
            step.info.get("policy", {}).get("metadata", {}).get(
                "experience_version"
            )
            for episode in policy_episodes
            for step in episode.steps
        }
        if versions != {experience.version}:
            raise ValueError(
                f"validation {label} steps did not consistently use its experience"
            )
    if validation_audit.get("status") != "passed" or validation_audit.get("protocol_role") != "evaluation":
        raise ValueError("validation audit did not pass with evaluation role")

    replay = audit_experience_candidate_decision(decision, decision_path=paths["decision"])
    if Path(decision.get("incumbent", {}).get("path", "")) != paths["incumbent_experience"] or Path(decision.get("candidate", {}).get("path", "")) != paths["candidate_experience"]:
        raise ValueError("decision experience paths differ from cycle artifacts")
    decision_inputs = {key: Path(value.get("path", "")) for key, value in decision.get("inputs", {}).items()}
    for key in ("comparison", "validation_audit", "evolution_audit"):
        if decision_inputs.get(key) != paths[key]:
            raise ValueError(f"decision {key} path differs from cycle artifact")
    return {"incumbent_version": incumbent.version, "candidate_version": candidate.version, "source_split": source_split, "development_episode_count": len(episodes), "development_failure_count": len(failed_ids), "validation_split": comparison["split"], "validation_task_count": comparison["task_count_per_variant"], "decision": decision["decision"], "selected_stable_version": decision["selected_stable"]["version"], "decision_replay_verified": replay["replay_equal"]}


ARTIFACT_NAMES = ("incumbent_experience", "development_trajectories", "development_summary", "development_audit", "candidate_experience", "evolution_audit", "validation_trajectories", "validation_incumbent_summary", "validation_candidate_summary", "comparison", "validation_audit", "decision")
DIRECTORY_NAMES = frozenset({"development_trajectories", "validation_trajectories"})


def build_evolution_cycle_manifest(*, cycle_id: str, **values: str | Path) -> dict:
    if not cycle_id.strip():
        raise ValueError("cycle_id must be non-empty")
    if set(values) != set(ARTIFACT_NAMES):
        raise ValueError("evolution cycle artifact set is incomplete")
    records = {name: (_directory_record(values[name]) if name in DIRECTORY_NAMES else _file_record(values[name])) for name in ARTIFACT_NAMES}
    result = _validate_cycle({name: Path(values[name]) for name in ARTIFACT_NAMES})
    return {"schema_version": EVOLUTION_CYCLE_SCHEMA_VERSION, "cycle_id": cycle_id, "status": "complete", "stages": ["development_rollout", "experience_evolution", "paired_validation", "candidate_gate"], "artifacts": records, "result": result}


def audit_evolution_cycle_manifest(manifest: Mapping, *, manifest_path: str | Path) -> dict:
    if manifest.get("schema_version") != EVOLUTION_CYCLE_SCHEMA_VERSION or manifest.get("status") != "complete":
        raise ValueError("unsupported or incomplete evolution cycle manifest")
    artifacts = manifest.get("artifacts", {})
    if set(artifacts) != set(ARTIFACT_NAMES):
        raise ValueError("evolution cycle manifest artifact set is incomplete")
    paths = {name: _checked_artifact(name, artifacts[name]) for name in ARTIFACT_NAMES}
    result = _validate_cycle(paths)
    if result != manifest.get("result"):
        raise ValueError("evolution cycle result is not reproducible")
    return {"status": "passed", "cycle_id": manifest.get("cycle_id"), "manifest_path": Path(manifest_path).as_posix(), "manifest_sha256": file_sha256(manifest_path), "artifact_count": len(ARTIFACT_NAMES), "file_artifact_count": len(ARTIFACT_NAMES) - len(DIRECTORY_NAMES), "directory_artifact_count": len(DIRECTORY_NAMES), "content_file_count": sum(int(record.get("file_count", 1)) for record in artifacts.values()), "replay_equal": True, "result": result}
