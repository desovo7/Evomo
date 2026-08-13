from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from evomo.evaluation import (
    audit_evolution_cycle_manifest,
    directory_sha256,
)


REPOSITORY = Path(__file__).resolve().parents[1]
MANIFEST = REPOSITORY / "reports/experience_v4/cycle_manifest.json"


def test_directory_hash_is_path_sensitive_and_detects_content_change(
    tmp_path: Path,
) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    (root / "a.txt").write_text("same", encoding="utf-8")
    first = directory_sha256(root)

    (root / "a.txt").rename(root / "b.txt")
    renamed = directory_sha256(root)
    assert renamed[0] != first[0]

    (root / "b.txt").write_text("changed", encoding="utf-8")
    changed = directory_sha256(root)
    assert changed[0] != renamed[0]
    assert changed[1] == 1
    assert changed[2] == len("changed")


def test_checked_in_real_cycle_manifest_replays_all_links() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    audit = audit_evolution_cycle_manifest(manifest, manifest_path=MANIFEST)

    assert audit["status"] == "passed"
    assert audit["artifact_count"] == 12
    assert audit["directory_artifact_count"] == 2
    assert audit["result"]["development_episode_count"] == 200
    assert audit["result"]["development_failure_count"] == 42
    assert audit["result"]["validation_task_count"] == 140
    assert audit["result"]["decision"] == "retain_candidate"
    assert audit["result"]["decision_replay_verified"] is True


def test_cycle_manifest_rejects_a_changed_artifact_digest() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tampered = deepcopy(manifest)
    tampered["artifacts"]["candidate_experience"]["sha256"] = "0" * 64

    with pytest.raises(ValueError, match="differs from manifest"):
        audit_evolution_cycle_manifest(tampered, manifest_path=MANIFEST)


def test_cycle_manifest_rejects_a_changed_derived_result() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tampered = deepcopy(manifest)
    tampered["result"]["development_failure_count"] += 1

    with pytest.raises(ValueError, match="result is not reproducible"):
        audit_evolution_cycle_manifest(tampered, manifest_path=MANIFEST)
