"""Append-only exposure ledger for evaluation tasks across evolution cycles."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Mapping

from evomo.benchmarks.alfworld import discover_tasks
from evomo.experience import EVALUATION_SPLITS

from .candidate_gate import file_sha256
from .cycle_executor import audit_cycle_executor_state
from .evolution_cycle import audit_evolution_cycle_manifest
from .multitask import CANONICAL_TASK_TYPES

EVALUATION_LEDGER_SCHEMA_VERSION = 1


def task_ids_sha256(task_ids: Iterable[str]) -> str:
    values = tuple(sorted(task_ids))
    if not values or len(values) != len(set(values)):
        raise ValueError("evaluation task IDs must be non-empty and unique")
    digest = hashlib.sha256()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("evaluation task IDs must be non-empty strings")
        payload = value.encode("utf-8")
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _empty_ledger(benchmark: str) -> dict:
    return {
        "schema_version": EVALUATION_LEDGER_SCHEMA_VERSION,
        "benchmark": benchmark,
        "entries": [],
    }


def _load_ledger(path: Path, *, benchmark: str) -> dict:
    if not path.exists():
        return _empty_ledger(benchmark)
    ledger = json.loads(path.read_text(encoding="utf-8"))
    if ledger.get("schema_version") != EVALUATION_LEDGER_SCHEMA_VERSION:
        raise ValueError("unsupported evaluation ledger schema")
    if ledger.get("benchmark") != benchmark:
        raise ValueError("evaluation ledger benchmark mismatch")
    if not isinstance(ledger.get("entries"), list):
        raise ValueError("evaluation ledger entries must be a list")
    return ledger


@contextmanager
def _ledger_lock(path: Path):
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _write_durable_json(path: Path, value: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    directory_fd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _validate_entry(entry: Mapping) -> None:
    required = {
        "cycle_id",
        "exposure_order",
        "status",
        "benchmark",
        "split",
        "task_types",
        "task_count",
        "task_ids_sha256",
        "task_ids",
        "prior_overlaps",
        "source",
    }
    if set(entry) != required:
        raise ValueError("evaluation ledger entry fields are invalid")
    if entry.get("status") not in {"reserved", "completed"}:
        raise ValueError("evaluation ledger status is invalid")
    if not isinstance(entry.get("exposure_order"), int) or isinstance(
        entry.get("exposure_order"), bool
    ) or entry["exposure_order"] <= 0:
        raise ValueError("evaluation ledger exposure_order must be positive")
    if entry.get("benchmark") != "alfworld":
        raise ValueError("evaluation ledger entry benchmark is invalid")
    if entry.get("split") not in EVALUATION_SPLITS:
        raise ValueError("evaluation ledger entry split is not evaluation")
    task_ids = entry.get("task_ids", ())
    if task_ids != sorted(task_ids) or entry.get("task_count") != len(task_ids):
        raise ValueError("evaluation ledger task IDs are not canonical")
    if entry.get("task_ids_sha256") != task_ids_sha256(task_ids):
        raise ValueError("evaluation ledger task digest mismatch")
    task_types = entry.get("task_types", ())
    if task_types != sorted(task_types) or not set(task_types).issubset(
        CANONICAL_TASK_TYPES
    ):
        raise ValueError("evaluation ledger task types are invalid")
    if not isinstance(entry.get("source"), dict):
        raise ValueError("evaluation ledger source must be an object")
    overlaps = entry.get("prior_overlaps")
    if not isinstance(overlaps, list):
        raise ValueError("evaluation ledger prior_overlaps must be a list")
    for overlap in overlaps:
        if set(overlap) != {"cycle_id", "task_count", "task_ids_sha256"}:
            raise ValueError("evaluation ledger overlap record fields are invalid")
        if not overlap["cycle_id"] or overlap["task_count"] <= 0:
            raise ValueError("evaluation ledger overlap record is invalid")


def audit_evaluation_ledger(ledger: Mapping, *, ledger_path: str | Path) -> dict:
    if ledger.get("schema_version") != EVALUATION_LEDGER_SCHEMA_VERSION:
        raise ValueError("unsupported evaluation ledger schema")
    if ledger.get("benchmark") != "alfworld":
        raise ValueError("evaluation ledger benchmark is invalid")
    entries = ledger.get("entries", ())
    exposure_orders = [entry.get("exposure_order") for entry in entries]
    if len(exposure_orders) != len(set(exposure_orders)):
        raise ValueError("evaluation ledger exposure orders must be unique")
    chronological_entries = sorted(entries, key=lambda item: item["exposure_order"])
    cycle_ids: set[str] = set()
    seen_tasks: dict[str, str] = {}
    overlap_event_count = 0
    overlapped_tasks: set[str] = set()
    verified_source_file_count = 0
    replayed_completed_cycle_count = 0
    for entry in chronological_entries:
        _validate_entry(entry)
        source = entry["source"]
        kind = source.get("kind")
        if kind == "historical_audited_report":
            for prefix in ("validation_audit", "validation_summary"):
                path = Path(str(source.get(f"{prefix}_path", "")))
                if not path.is_file() or file_sha256(path) != source.get(
                    f"{prefix}_sha256"
                ):
                    raise ValueError(f"evaluation ledger {prefix} evidence mismatch")
                verified_source_file_count += 1
        elif kind == "completed_cycle":
            manifest_path = Path(str(source.get("manifest_path", "")))
            config_path = Path(str(source.get("executor_config_path", "")))
            state_path = Path(str(source.get("executor_state_path", "")))
            summary_path = Path(str(source.get("validation_summary_path", "")))
            for name, path in (
                ("manifest", manifest_path),
                ("executor_config", config_path),
                ("executor_state", state_path),
                ("validation_summary", summary_path),
            ):
                if not path.is_file() or file_sha256(path) != source.get(
                    f"{name}_sha256"
                ):
                    raise ValueError(f"evaluation ledger {name} evidence mismatch")
                verified_source_file_count += 1
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_audit = audit_evolution_cycle_manifest(
                manifest, manifest_path=manifest_path
            )
            executor_audit = audit_cycle_executor_state(
                config_path, state_dir=state_path.parent
            )
            if (
                manifest.get("cycle_id") != entry["cycle_id"]
                or executor_audit.get("cycle_id") != entry["cycle_id"]
                or manifest_audit["result"].get("validation_split")
                != entry["split"]
                or manifest_audit["result"].get("validation_task_count")
                != entry["task_count"]
            ):
                raise ValueError("evaluation ledger completed cycle evidence differs")
            replayed_completed_cycle_count += 1
        elif kind == "dataset_discovery_reservation":
            if entry["status"] != "reserved":
                raise ValueError("completed ledger entry retains reservation source")
        else:
            raise ValueError(f"evaluation ledger source kind is unsupported: {kind!r}")
        cycle_id = entry["cycle_id"]
        if cycle_id in cycle_ids:
            raise ValueError("evaluation ledger contains duplicate cycle IDs")
        cycle_ids.add(cycle_id)
        expected_overlaps = []
        prior_cycles = sorted(set(seen_tasks.get(task_id, "") for task_id in entry["task_ids"]) - {""})
        for prior_cycle in prior_cycles:
            overlap_ids = sorted(
                task_id
                for task_id in entry["task_ids"]
                if seen_tasks.get(task_id) == prior_cycle
            )
            expected_overlaps.append(
                {
                    "cycle_id": prior_cycle,
                    "task_count": len(overlap_ids),
                    "task_ids_sha256": task_ids_sha256(overlap_ids),
                }
            )
            overlapped_tasks.update(overlap_ids)
        if entry["prior_overlaps"] != expected_overlaps:
            raise ValueError("evaluation ledger prior overlap metadata is not reproducible")
        overlap_event_count += len(expected_overlaps)
        for task_id in entry["task_ids"]:
            seen_tasks.setdefault(task_id, cycle_id)
    return {
        "status": "passed",
        "ledger_path": Path(ledger_path).as_posix(),
        "ledger_sha256": file_sha256(ledger_path),
        "benchmark": ledger["benchmark"],
        "cycle_count": len(entries),
        "reserved_cycle_count": sum(entry["status"] == "reserved" for entry in entries),
        "completed_cycle_count": sum(entry["status"] == "completed" for entry in entries),
        "exposed_task_count": len(seen_tasks),
        "historical_overlap_event_count": overlap_event_count,
        "historical_overlap_task_count": len(overlapped_tasks),
        "verified_source_file_count": verified_source_file_count,
        "replayed_completed_cycle_count": replayed_completed_cycle_count,
        "splits": sorted({entry["split"] for entry in entries}),
        "chronological_cycle_ids": [
            entry["cycle_id"] for entry in chronological_entries
        ],
        "protocol_clean": overlap_event_count == 0,
    }


def _rebuild_prior_overlaps(entries: list[dict]) -> None:
    orders = [entry["exposure_order"] for entry in entries]
    if len(orders) != len(set(orders)):
        raise ValueError("evaluation ledger exposure orders must be unique")
    seen_tasks: dict[str, str] = {}
    for entry in sorted(entries, key=lambda item: item["exposure_order"]):
        overlaps = []
        prior_cycles = sorted(
            set(seen_tasks.get(task_id, "") for task_id in entry["task_ids"]) - {""}
        )
        for prior_cycle in prior_cycles:
            task_ids = sorted(
                task_id
                for task_id in entry["task_ids"]
                if seen_tasks.get(task_id) == prior_cycle
            )
            overlaps.append(
                {
                    "cycle_id": prior_cycle,
                    "task_count": len(task_ids),
                    "task_ids_sha256": task_ids_sha256(task_ids),
                }
            )
        entry["prior_overlaps"] = overlaps
        for task_id in entry["task_ids"]:
            seen_tasks.setdefault(task_id, entry["cycle_id"])


def _commit_entry(
    entry: dict,
    *,
    ledger_path: Path,
    receipt_path: Path,
    allow_historical_overlap: bool = False,
) -> dict:
    with _ledger_lock(ledger_path):
        ledger = _load_ledger(ledger_path, benchmark=entry["benchmark"])
        existing = next(
            (
                item
                for item in ledger["entries"]
                if item.get("cycle_id") == entry["cycle_id"]
            ),
            None,
        )
        if existing is not None and existing.get("status") == "reserved":
            if not entry.get("exposure_order"):
                entry["exposure_order"] = existing["exposure_order"]
            if not entry.get("prior_overlaps"):
                entry["prior_overlaps"] = existing["prior_overlaps"]
        elif not entry.get("exposure_order"):
            entry["exposure_order"] = 1 + max(
                (item["exposure_order"] for item in ledger["entries"]), default=0
            )
        if existing is not None and existing == entry:
            idempotent = True
            operation = "idempotent_replay"
        elif existing is not None and existing.get("status") == "reserved":
            scope_keys = (
                "cycle_id",
                "exposure_order",
                "benchmark",
                "split",
                "task_types",
                "task_count",
                "task_ids_sha256",
                "task_ids",
                "prior_overlaps",
            )
            if any(existing.get(key) != entry.get(key) for key in scope_keys):
                raise ValueError("reserved cycle has a different evaluation exposure")
            if entry.get("status") != "completed":
                raise ValueError("reserved cycle can only advance to completed")
            ledger["entries"][ledger["entries"].index(existing)] = entry
            _write_durable_json(ledger_path, ledger)
            idempotent = False
            operation = "reservation_completed"
        elif existing is not None:
            if existing != entry:
                raise ValueError("cycle ID already has a different evaluation exposure")
        else:
            requested = set(entry["task_ids"])
            overlaps = [
                (item["cycle_id"], sorted(requested.intersection(item["task_ids"])))
                for item in ledger["entries"]
                if requested.intersection(item["task_ids"])
            ]
            if overlaps and not allow_historical_overlap:
                cycle, tasks = overlaps[0]
                raise ValueError(
                    f"evaluation tasks overlap prior cycle {cycle!r}: {tasks[:3]}"
                )
            ledger["entries"].append(entry)
            _rebuild_prior_overlaps(ledger["entries"])
            for item in ledger["entries"]:
                _validate_entry(item)
            _write_durable_json(ledger_path, ledger)
            idempotent = False
            operation = "entry_appended"
        ledger_sha = file_sha256(ledger_path)
        receipt = {
            "schema_version": EVALUATION_LEDGER_SCHEMA_VERSION,
            "status": "registered",
            "operation": entry["status"],
            "commit_result": operation,
            "cycle_id": entry["cycle_id"],
            "exposure_order": entry["exposure_order"],
            "benchmark": entry["benchmark"],
            "split": entry["split"],
            "task_count": entry["task_count"],
            "task_ids_sha256": entry["task_ids_sha256"],
            "ledger_path": ledger_path.as_posix(),
            "ledger_sha256_after_operation": ledger_sha,
            "idempotent_replay": idempotent,
        }
        _write_durable_json(receipt_path, receipt)
        return receipt


def reserve_alfworld_evaluation_tasks(
    *,
    ledger_path: str | Path,
    receipt_path: str | Path,
    cycle_id: str,
    data_root: str | Path,
    split: str,
    task_types: Iterable[str] = CANONICAL_TASK_TYPES,
) -> dict:
    task_types = tuple(task_types)
    if split not in EVALUATION_SPLITS:
        raise ValueError("reservation split is not an evaluation split")
    if not cycle_id.strip() or not task_types or len(task_types) != len(set(task_types)):
        raise ValueError("cycle ID and unique task types are required")
    unknown = set(task_types) - set(CANONICAL_TASK_TYPES)
    if unknown:
        raise ValueError(f"unknown ALFWorld task types: {sorted(unknown)}")
    discovered = discover_tasks(data_root, splits=[split]).tasks
    task_ids = sorted(
        task.task_id for task in discovered if task.task_type in set(task_types)
    )
    entry = {
        "cycle_id": cycle_id,
        "exposure_order": 0,
        "status": "reserved",
        "benchmark": "alfworld",
        "split": split,
        "task_types": sorted(task_types),
        "task_count": len(task_ids),
        "task_ids_sha256": task_ids_sha256(task_ids),
        "task_ids": task_ids,
        "prior_overlaps": [],
        "source": {
            "kind": "dataset_discovery_reservation",
            "data_root": Path(data_root).as_posix(),
        },
    }
    return _commit_entry(
        entry, ledger_path=Path(ledger_path), receipt_path=Path(receipt_path)
    )


def register_completed_evaluation_cycle(
    *,
    ledger_path: str | Path,
    receipt_path: str | Path,
    manifest_path: str | Path,
    executor_config_path: str | Path,
    executor_state_dir: str | Path,
    validation_summary_path: str | Path,
    allow_historical_overlap: bool = False,
    exposure_order: int | None = None,
) -> dict:
    manifest_path = Path(manifest_path)
    config_path = Path(executor_config_path)
    summary_path = Path(validation_summary_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_audit = audit_evolution_cycle_manifest(
        manifest, manifest_path=manifest_path
    )
    executor_audit = audit_cycle_executor_state(
        config_path, state_dir=executor_state_dir
    )
    if manifest.get("cycle_id") != executor_audit.get("cycle_id"):
        raise ValueError("manifest and executor cycle IDs differ")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    run = summary.get("run", {})
    task_ids = sorted(run.get("task_ids", ()))
    split = run.get("split")
    if split not in EVALUATION_SPLITS:
        raise ValueError("completed cycle summary is not an evaluation split")
    if len(task_ids) != summary.get("task_count"):
        raise ValueError("completed cycle summary task count mismatch")
    result = manifest_audit["result"]
    if result.get("validation_split") != split or result.get(
        "validation_task_count"
    ) != len(task_ids):
        raise ValueError("manifest validation scope differs from summary")
    manifest_summary_path = Path(
        manifest["artifacts"]["validation_incumbent_summary"]["path"]
    )
    if manifest_summary_path != summary_path:
        raise ValueError("summary path is not the manifest incumbent validation summary")
    entry = {
        "cycle_id": manifest["cycle_id"],
        "exposure_order": exposure_order or 0,
        "status": "completed",
        "benchmark": "alfworld",
        "split": split,
        "task_types": sorted(run.get("task_types", ())),
        "task_count": len(task_ids),
        "task_ids_sha256": task_ids_sha256(task_ids),
        "task_ids": task_ids,
        "prior_overlaps": [],
        "source": {
            "kind": "completed_cycle",
            "manifest_path": manifest_path.as_posix(),
            "manifest_sha256": file_sha256(manifest_path),
            "executor_config_path": config_path.as_posix(),
            "executor_config_sha256": file_sha256(config_path),
            "executor_state_path": executor_audit["state_path"],
            "executor_state_sha256": executor_audit["state_sha256"],
            "validation_summary_path": summary_path.as_posix(),
            "validation_summary_sha256": file_sha256(summary_path),
        },
    }
    return _commit_entry(
        entry,
        ledger_path=Path(ledger_path),
        receipt_path=Path(receipt_path),
        allow_historical_overlap=allow_historical_overlap,
    )


def register_audited_evaluation_report(
    *,
    ledger_path: str | Path,
    receipt_path: str | Path,
    cycle_id: str,
    validation_audit_path: str | Path,
    validation_summary_path: str | Path,
    allow_historical_overlap: bool = False,
    exposure_order: int | None = None,
) -> dict:
    """Backfill a pre-executor exposure from its audited report and summary."""

    audit_path = Path(validation_audit_path)
    summary_path = Path(validation_summary_path)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if audit.get("status") != "passed":
        raise ValueError("historical validation audit did not pass")
    audited = {item.get("variant"): item for item in audit.get("variants", ())}.get(
        summary.get("variant")
    )
    if not audited:
        raise ValueError("historical audit does not contain the summary variant")
    run = summary.get("run", {})
    task_ids = sorted(run.get("task_ids", ()))
    if audit.get("protocol_role") == "evaluation":
        audit_protocol = "explicit_evaluation_role"
    elif audit.get("protocol_role") is None:
        legacy_requirements = {
            "same_task_ids": True,
            "experience_evidence_task_overlap": 0,
            "excluded_source_task_overlap": 0,
            "discovery_task_count": len(task_ids),
        }
        if run.get("selection_mode") != "all_tasks" or any(
            audit.get(key) != expected
            for key, expected in legacy_requirements.items()
        ):
            raise ValueError(
                "legacy historical audit lacks full-coverage evaluation evidence"
            )
        audit_protocol = "legacy_full_coverage_evaluation"
    else:
        raise ValueError("historical validation audit is not evaluation")
    if (
        len(task_ids) != summary.get("task_count")
        or audited.get("episode_count") != len(task_ids)
        or audited.get("success_count") != summary.get("success_count")
    ):
        raise ValueError("historical evaluation counts are inconsistent")
    split = run.get("split")
    if split not in EVALUATION_SPLITS:
        raise ValueError("historical summary is not an evaluation split")
    entry = {
        "cycle_id": cycle_id,
        "exposure_order": exposure_order or 0,
        "status": "completed",
        "benchmark": "alfworld",
        "split": split,
        "task_types": sorted(run.get("task_types", ())),
        "task_count": len(task_ids),
        "task_ids_sha256": task_ids_sha256(task_ids),
        "task_ids": task_ids,
        "prior_overlaps": [],
        "source": {
            "kind": "historical_audited_report",
            "audit_protocol": audit_protocol,
            "validation_audit_path": audit_path.as_posix(),
            "validation_audit_sha256": file_sha256(audit_path),
            "validation_summary_path": summary_path.as_posix(),
            "validation_summary_sha256": file_sha256(summary_path),
        },
    }
    return _commit_entry(
        entry,
        ledger_path=Path(ledger_path),
        receipt_path=Path(receipt_path),
        allow_historical_overlap=allow_historical_overlap,
    )
