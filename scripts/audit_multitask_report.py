"""Audit persisted ALFWorld trajectories and cross-variant run contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def audit_variant(directory: Path, *, experience: dict | None = None) -> dict:
    summary = load_json(directory / "summary.json")
    expected_ids = {row["task_id"] for row in summary["tasks"]}
    episodes: list[dict] = []
    step_count = 0
    override_count = 0
    used_rule_ids: set[str] = set()
    rule_types = (
        {rule["rule_id"]: set(rule["task_types"]) for rule in experience["rules"]}
        if experience is not None
        else {}
    )
    for episode_path in sorted(directory.glob("shard_*/*/episode.jsonl")):
        rows = load_jsonl(episode_path)
        if len(rows) != 1:
            raise ValueError(f"{episode_path}: expected one episode, got {len(rows)}")
        episode = rows[0]
        steps = episode["steps"]
        step_rows = load_jsonl(episode_path.with_name("steps.jsonl"))
        if len(step_rows) != len(steps):
            raise ValueError(f"{episode_path}: step log count mismatch")
        if [row["step_index"] for row in steps] != list(range(len(steps))):
            raise ValueError(f"{episode_path}: non-contiguous step indices")
        previous = episode["initial_observation"]
        for step, logged in zip(steps, step_rows):
            if step["observation"] != previous:
                raise ValueError(f"{episode_path}: broken observation chain")
            if step["action"] not in step["admissible_actions"]:
                raise ValueError(f"{episode_path}: inadmissible action {step['action']!r}")
            metadata = step["info"]["policy"]["metadata"]
            if not isinstance(metadata.get("state_before"), dict):
                raise ValueError(f"{episode_path}: missing state_before")
            if logged.get("state_before") != metadata["state_before"]:
                raise ValueError(f"{episode_path}: step log state differs from episode")
            rule_ids = metadata.get("experience_rule_ids", [])
            applicable_ids = metadata.get("applicable_experience_rule_ids", [])
            scoped_ids = {
                rule_id
                for rule_id, task_types in rule_types.items()
                if episode["task"]["task_type"] in task_types
            }
            if experience is not None and set(applicable_ids) != scoped_ids:
                raise ValueError(f"{episode_path}: applicable experience rules violate scope")
            if not set(rule_ids).issubset(scoped_ids):
                raise ValueError(f"{episode_path}: used experience rule outside task scope")
            if bool(metadata.get("experience_override_reason")) != bool(rule_ids):
                raise ValueError(f"{episode_path}: experience override metadata is inconsistent")
            used_rule_ids.update(rule_ids)
            override_count += int(bool(metadata.get("experience_override_reason")))
            previous = step["next_observation"]
        if episode["success"]:
            if (
                episode["termination_reason"] != "success"
                or not steps[-1]["terminated"]
                or steps[-1]["reward"] <= 0
            ):
                raise ValueError(f"{episode_path}: success is not native terminal reward")
        episodes.append(episode)
        step_count += len(steps)

    actual_ids = {episode["task"]["task_id"] for episode in episodes}
    if actual_ids != expected_ids:
        raise ValueError(f"{directory}: episode task IDs differ from summary")
    if len(actual_ids) != len(episodes):
        raise ValueError(f"{directory}: duplicate episode task IDs")
    declared_ids = set(summary["run"]["task_ids"])
    if actual_ids != declared_ids:
        raise ValueError(f"{directory}: run task IDs differ from episodes")
    if step_count != summary["totals"]["steps"]:
        raise ValueError(f"{directory}: aggregate step count mismatch")

    rule_ids = set()
    if experience is not None:
        rule_ids = {rule["rule_id"] for rule in experience["rules"]}
        unknown = used_rule_ids - rule_ids
        if unknown:
            raise ValueError(f"{directory}: unknown experience rules {sorted(unknown)}")
    elif used_rule_ids or override_count:
        raise ValueError(f"{directory}: experience behavior without an experience file")

    return {
        "variant": summary["variant"],
        "episode_count": len(episodes),
        "step_count": step_count,
        "success_count": sum(bool(episode["success"]) for episode in episodes),
        "task_type_counts": dict(sorted(Counter(ep["task"]["task_type"] for ep in episodes).items())),
        "experience_override_count": override_count,
        "used_experience_rule_ids": sorted(used_rule_ids),
        "task_ids": sorted(actual_ids),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--experience-file", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    experience = load_json(args.experience_file) if args.experience_file else None
    results = [
        audit_variant(args.report_dir / "F"),
        audit_variant(args.report_dir / "H", experience=experience),
    ]
    if results[0]["task_ids"] != results[1]["task_ids"]:
        raise ValueError("F and H do not cover identical task IDs")
    evaluation_ids = set(results[0]["task_ids"])
    if experience is not None:
        evidence_ids = {
            item["task_id"]
            for rule in experience["rules"]
            for item in rule["evidence"]
        }
        overlap = evaluation_ids.intersection(evidence_ids)
        if overlap:
            raise ValueError(f"evaluation tasks overlap experience evidence: {sorted(overlap)}")
    h_summary = load_json(args.report_dir / "H" / "summary.json")
    if experience is not None:
        digest = hashlib.sha256(args.experience_file.read_bytes()).hexdigest()
        if h_summary["run"]["experience_version"] != experience["version"]:
            raise ValueError("H run experience version mismatch")
        if h_summary["run"]["experience_sha256"] != digest:
            raise ValueError("H run experience SHA-256 mismatch")

    public_results = [{k: v for k, v in result.items() if k != "task_ids"} for result in results]
    report = {
        "status": "passed",
        "report_dir": str(args.report_dir),
        "same_task_ids": True,
        "experience_evidence_task_overlap": 0 if experience is not None else None,
        "variants": public_results,
        "totals": {
            "episodes": sum(item["episode_count"] for item in public_results),
            "steps": sum(item["step_count"] for item in public_results),
            "successes": sum(item["success_count"] for item in public_results),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
