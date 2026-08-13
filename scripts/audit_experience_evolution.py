"""Audit that a child experience set is grounded in persisted failed episodes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evomo.data import EpisodeStore
from evomo.experience import load_experience_set, validate_evolution_source


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--child", type=Path, required=True)
    parser.add_argument("--episodes-root", type=Path, required=True)
    parser.add_argument("--source-split", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    base = load_experience_set(args.base)
    child = load_experience_set(args.child)
    if child.parent_version != base.version:
        raise ValueError("child parent_version does not match base version")

    episodes = []
    for path in sorted(args.episodes_root.rglob("episode.jsonl")):
        episodes.extend(EpisodeStore(path).load_all())
    episodes = list(
        validate_evolution_source(episodes, expected_split=args.source_split)
    )
    failed = {episode.episode_id: episode for episode in episodes if not episode.success}
    if len(failed) != sum(not episode.success for episode in episodes):
        raise ValueError("duplicate failed episode IDs")
    if set(child.source_episode_ids) != set(failed):
        raise ValueError("child source IDs do not equal all failed episode IDs")
    if {episode.policy_id for episode in failed.values()} != {child.source_policy_id}:
        raise ValueError("child source policy does not match failed episodes")

    observed_versions = {
        step.info.get("policy", {}).get("metadata", {}).get("experience_version")
        for episode in failed.values()
        for step in episode.steps
    }
    if observed_versions != {base.version}:
        raise ValueError("source trajectories did not consistently use the base version")

    base_evidence = {
        (item.episode_id, item.task_id, item.step_index, item.action, item.observation)
        for rule in base.rules
        for item in rule.evidence
    }
    base_rule_ids = {rule.rule_id for rule in base.rules}
    new_evidence_count = 0
    evidence_by_rule = {}
    source_task_types = {episode.task.task_type for episode in failed.values()}
    for rule in child.rules:
        new_items = []
        for item in rule.evidence:
            key = (item.episode_id, item.task_id, item.step_index, item.action, item.observation)
            if key in base_evidence:
                continue
            episode = failed.get(item.episode_id)
            if episode is None or episode.task.task_id != item.task_id:
                raise ValueError(f"rule {rule.rule_id}: evidence does not resolve to a source episode")
            if item.step_index is not None:
                if item.step_index < 0 or item.step_index >= len(episode.steps):
                    raise ValueError(f"rule {rule.rule_id}: evidence step is out of range")
                if item.action != episode.steps[item.step_index].action:
                    raise ValueError(f"rule {rule.rule_id}: evidence action differs from trajectory")
            new_items.append(item)
        if not new_items and rule.rule_id not in base_rule_ids:
            raise ValueError(f"new rule {rule.rule_id}: child contains no new evidence")
        evidence_types = {
            failed[item.episode_id].task.task_type for item in new_items
        }
        if not evidence_types.issubset(set(rule.task_types)):
            raise ValueError(f"rule {rule.rule_id}: evidence type lies outside rule scope")
        new_evidence_count += len(new_items)
        evidence_by_rule[rule.rule_id] = {
            "new_evidence_count": len(new_items),
            "new_evidence_task_types": sorted(evidence_types),
            "declared_task_types": list(rule.task_types),
        }

    report = {
        "status": "passed",
        "base_version": base.version,
        "child_version": child.version,
        "parent_version": child.parent_version,
        "source_policy_id": child.source_policy_id,
        "source_split": args.source_split,
        "source_role": "development",
        "source_episode_count": len(failed),
        "source_task_types": sorted(source_task_types),
        "new_evidence_count": new_evidence_count,
        "rules": evidence_by_rule,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
