"""Recoverable, logged execution of an ordered self-evolution pipeline."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from .candidate_gate import file_sha256
from .evolution_cycle import audit_evolution_cycle_manifest, directory_sha256
from .multitask import write_json

CYCLE_EXECUTOR_SCHEMA_VERSION = 1


def _canonical_sha256(value: Mapping) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _command_sha256(argv: list[str]) -> str:
    return hashlib.sha256(
        json.dumps(argv, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event_digest(record: Mapping) -> str:
    return hashlib.sha256(
        json.dumps(
            record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _validate_event_chain(
    events: list[dict], *, cycle_id: str, config_hash: str
) -> str | None:
    previous = None
    for index, event in enumerate(events, start=1):
        if (
            event.get("schema_version") != 1
            or event.get("sequence") != index
            or event.get("cycle_id") != cycle_id
            or event.get("config_sha256") != config_hash
            or event.get("previous_event_sha256") != previous
        ):
            raise ValueError("cycle executor event identity or hash chain mismatch")
        body = {key: value for key, value in event.items() if key != "event_sha256"}
        if event.get("event_sha256") != _event_digest(body):
            raise ValueError("cycle executor event digest mismatch")
        previous = event["event_sha256"]
    return previous


def _artifact_record(path: Path) -> dict:
    if path.is_file():
        return {
            "kind": "file",
            "path": path.as_posix(),
            "sha256": file_sha256(path),
            "bytes": path.stat().st_size,
        }
    if path.is_dir():
        digest, file_count, size = directory_sha256(path)
        return {
            "kind": "directory",
            "path": path.as_posix(),
            "sha256": digest,
            "file_count": file_count,
            "bytes": size,
        }
    raise ValueError(f"stage output is missing: {path}")


def _workspace_path(workspace: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else workspace / path


def _validate_config(config: Mapping) -> tuple[dict, ...]:
    if config.get("schema_version") != CYCLE_EXECUTOR_SCHEMA_VERSION:
        raise ValueError("unsupported cycle executor config schema")
    if not str(config.get("cycle_id", "")).strip():
        raise ValueError("cycle executor cycle_id must be non-empty")
    max_parallel = config.get("max_parallel", 3)
    if not isinstance(max_parallel, int) or isinstance(max_parallel, bool) or not 1 <= max_parallel <= 3:
        raise ValueError("max_parallel must be an integer from 1 to 3")
    stages = tuple(config.get("stages", ()))
    if not stages:
        raise ValueError("cycle executor requires at least one stage")
    identifiers = [str(stage.get("stage_id", "")) for stage in stages]
    if any(not value.strip() for value in identifiers) or len(set(identifiers)) != len(identifiers):
        raise ValueError("stage IDs must be non-empty and unique")
    seen: set[str] = set()
    job_ids: set[str] = set()
    output_paths: set[str] = set()
    for stage in stages:
        stage_id = str(stage["stage_id"])
        dependencies = tuple(stage.get("depends_on", ()))
        if any(item not in seen for item in dependencies):
            raise ValueError(f"{stage_id}: dependencies must refer to earlier stages")
        if len(dependencies) != len(set(dependencies)):
            raise ValueError(f"{stage_id}: dependencies must be unique")
        outputs = tuple(stage.get("outputs", ()))
        if not outputs or any(not str(item).strip() for item in outputs):
            raise ValueError(f"{stage_id}: outputs must be non-empty")
        for output in outputs:
            normalized = Path(str(output)).as_posix()
            if normalized in output_paths:
                raise ValueError(f"duplicate executor output path: {normalized}")
            output_paths.add(normalized)
        for job in stage.get("jobs", ()):
            job_id = str(job.get("job_id", ""))
            argv = job.get("argv")
            if not job_id.strip() or job_id in job_ids:
                raise ValueError("executor job IDs must be non-empty and globally unique")
            if not isinstance(argv, list) or not argv or any(
                not isinstance(item, str) or not item for item in argv
            ):
                raise ValueError(f"{job_id}: argv must be a non-empty string list")
            environment = job.get("env", {})
            if not isinstance(environment, Mapping) or any(
                not isinstance(key, str) or not isinstance(value, str)
                for key, value in environment.items()
            ):
                raise ValueError(f"{job_id}: env must map strings to strings")
            job_ids.add(job_id)
        seen.add(stage_id)
    if not config.get("adopt_manifest") and any(
        not stage.get("jobs") for stage in stages
    ):
        raise ValueError("stages without jobs require adopt_manifest")
    return stages


class CycleExecutor:
    """Execute or content-verify stages while persisting resumable state."""

    def __init__(self, config: Mapping, *, state_dir: str | Path) -> None:
        self.config = json.loads(json.dumps(config))
        self.stages = _validate_config(self.config)
        self.state_dir = Path(state_dir)
        self.state_path = self.state_dir / "state.json"
        self.events_path = self.state_dir / "events.jsonl"
        self.logs_dir = self.state_dir / "logs"
        self.config_hash = _canonical_sha256(self.config)
        self.workspace = Path(str(self.config.get("workspace", ".")))
        self.max_parallel = int(self.config.get("max_parallel", 3))
        self._sequence = 0
        self._event_head: str | None = None
        self._event_lock = threading.Lock()
        self._job_attempts: dict[tuple[str, str], int] = {}

    def _event(self, event: str, **values) -> str:
        with self._event_lock:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            self._sequence += 1
            record = {
                "schema_version": 1,
                "sequence": self._sequence,
                "timestamp": _timestamp(),
                "cycle_id": self.config["cycle_id"],
                "config_sha256": self.config_hash,
                "event": event,
                "previous_event_sha256": self._event_head,
                **values,
            }
            record["event_sha256"] = _event_digest(record)
            with self.events_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            self._event_head = record["event_sha256"]
            return self._event_head

    def _initial_state(self) -> dict:
        return {
            "schema_version": 1,
            "cycle_id": self.config["cycle_id"],
            "config_sha256": self.config_hash,
            "status": "running",
            "stages": {},
        }

    def _load_state(self) -> dict:
        if not self.state_path.exists():
            return self._initial_state()
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        if state.get("schema_version") != 1:
            raise ValueError("unsupported cycle executor state schema")
        if state.get("cycle_id") != self.config["cycle_id"] or state.get(
            "config_sha256"
        ) != self.config_hash:
            raise ValueError("executor config differs from immutable saved state")
        return state

    def _save_state(self, state: dict) -> None:
        write_json(self.state_path, state)

    def _records(self, stage: Mapping) -> list[dict]:
        return [
            _artifact_record(_workspace_path(self.workspace, str(path)))
            for path in stage["outputs"]
        ]

    def _adopt(self, state: dict) -> bool:
        manifest_value = self.config.get("adopt_manifest")
        if not manifest_value or state["stages"]:
            return False
        manifest_path = _workspace_path(self.workspace, str(manifest_value))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        audit = audit_evolution_cycle_manifest(
            manifest, manifest_path=manifest_path
        )
        covered_files = {
            Path(str(record["path"]))
            for record in manifest.get("artifacts", {}).values()
            if record.get("kind") == "file"
        }
        covered_directories = tuple(
            Path(str(record["path"]))
            for record in manifest.get("artifacts", {}).values()
            if record.get("kind") == "directory"
        )
        for stage in self.stages:
            for value in stage["outputs"]:
                output = _workspace_path(self.workspace, str(value))
                directory_covered = any(
                    output == root or output.is_relative_to(root)
                    for root in covered_directories
                )
                if (
                    output != manifest_path
                    and output not in covered_files
                    and not directory_covered
                ):
                    raise ValueError(
                        f"{stage['stage_id']}: adopted output is not sealed by manifest"
                    )
        self._event(
            "manifest_verified",
            manifest_path=manifest_path.as_posix(),
            manifest_sha256=audit["manifest_sha256"],
            replay_equal=audit["replay_equal"],
        )
        for stage in self.stages:
            stage_id = stage["stage_id"]
            records = self._records(stage)
            state["stages"][stage_id] = {
                "status": "complete",
                "completion_mode": "adopted_sealed_manifest",
                "outputs": records,
            }
        self._save_state(state)
        return True

    def _verify_recovery(self, stage: Mapping, saved: Mapping) -> None:
        actual = self._records(stage)
        if actual != saved.get("outputs"):
            raise ValueError(
                f"{stage['stage_id']}: completed outputs differ from saved state"
            )

    def _run_job(self, stage_id: str, job: Mapping) -> dict:
        job_id = str(job["job_id"])
        argv = list(job["argv"])
        with self._event_lock:
            key = (stage_id, job_id)
            attempt = self._job_attempts.get(key, 0) + 1
            self._job_attempts[key] = attempt
        suffix = "" if attempt == 1 else f"__attempt_{attempt:03d}"
        log_path = self.logs_dir / f"{stage_id}__{job_id}{suffix}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        environment = os.environ.copy()
        environment.update(job.get("env", {}))
        started = time.monotonic()
        self._event(
            "job_started",
            stage_id=stage_id,
            job_id=job_id,
            attempt=attempt,
            command_sha256=_command_sha256(argv),
            log_path=log_path.as_posix(),
        )
        with log_path.open("wb") as stream:
            completed = subprocess.run(
                argv,
                cwd=self.workspace,
                env=environment,
                stdout=stream,
                stderr=subprocess.STDOUT,
                check=False,
            )
        duration = time.monotonic() - started
        result = {
            "job_id": job_id,
            "attempt": attempt,
            "returncode": completed.returncode,
            "duration_seconds": round(duration, 6),
            "log_path": log_path.as_posix(),
            "log_sha256": file_sha256(log_path),
        }
        self._event("job_finished", stage_id=stage_id, **result)
        return result

    def run(self) -> dict:
        state = self._load_state()
        prior_events = (
            [
                json.loads(line)
                for line in self.events_path.read_text(encoding="utf-8").splitlines()
                if line
            ]
            if self.events_path.exists()
            else []
        )
        self._event_head = _validate_event_chain(
            prior_events,
            cycle_id=self.config["cycle_id"],
            config_hash=self.config_hash,
        )
        for event in prior_events:
            if event.get("event") != "job_started":
                continue
            key = (str(event.get("stage_id")), str(event.get("job_id")))
            attempt = int(event.get("attempt", 1))
            self._job_attempts[key] = max(self._job_attempts.get(key, 0), attempt)
        state_head = state.get("event_head_sha256")
        known_heads = {None} | {
            str(event["event_sha256"]) for event in prior_events
        }
        if state_head not in known_heads:
            raise ValueError("executor state event head is not in the event log chain")
        self._sequence = len(prior_events)
        self._event("run_started", state_status=state["status"])
        try:
            state["status"] = "running"
            state.pop("error", None)
            self._adopt(state)
            completed_ids: set[str] = set()
            for stage in self.stages:
                stage_id = str(stage["stage_id"])
                if not set(stage.get("depends_on", ())).issubset(completed_ids):
                    raise RuntimeError(f"{stage_id}: dependencies are not complete")
                saved = state["stages"].get(stage_id)
                if saved:
                    if saved.get("status") != "complete":
                        raise RuntimeError(f"{stage_id}: saved stage is incomplete")
                    self._verify_recovery(stage, saved)
                    self._event(
                        "stage_recovered",
                        stage_id=stage_id,
                        completion_mode=saved.get("completion_mode", "executed"),
                        output_count=len(saved["outputs"]),
                    )
                    completed_ids.add(stage_id)
                    continue
                self._event("stage_started", stage_id=stage_id)
                jobs = tuple(stage.get("jobs", ()))
                results = []
                with ThreadPoolExecutor(
                    max_workers=min(self.max_parallel, max(1, len(jobs)))
                ) as pool:
                    futures = {
                        pool.submit(self._run_job, stage_id, job): job for job in jobs
                    }
                    for future in as_completed(futures):
                        results.append(future.result())
                failures = [item for item in results if item["returncode"] != 0]
                if failures:
                    raise RuntimeError(
                        f"{stage_id}: jobs failed: {[item['job_id'] for item in failures]}"
                    )
                records = self._records(stage)
                state["stages"][stage_id] = {
                    "status": "complete",
                    "completion_mode": "executed",
                    "outputs": records,
                    "jobs": sorted(results, key=lambda item: item["job_id"]),
                }
                self._save_state(state)
                self._event(
                    "stage_completed",
                    stage_id=stage_id,
                    completion_mode="executed",
                    output_count=len(records),
                )
                completed_ids.add(stage_id)
            state["status"] = "complete"
            self._save_state(state)
            state["event_head_sha256"] = self._event(
                "run_completed", stage_count=len(self.stages)
            )
            self._save_state(state)
            return state
        except Exception as exc:
            state["status"] = "failed"
            state["error"] = f"{type(exc).__name__}: {exc}"
            state["event_head_sha256"] = self._event(
                "run_failed", error=state["error"]
            )
            self._save_state(state)
            raise


def run_cycle_executor(config_path: str | Path, *, state_dir: str | Path) -> dict:
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    return CycleExecutor(config, state_dir=state_dir).run()


def audit_cycle_executor_state(
    config_path: str | Path, *, state_dir: str | Path
) -> dict:
    """Audit immutable configuration, stage outputs, job logs, and event order."""

    config_path = Path(config_path)
    state_dir = Path(state_dir)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    stages = _validate_config(config)
    config_hash = _canonical_sha256(config)
    workspace = Path(str(config.get("workspace", ".")))
    state_path = state_dir / "state.json"
    events_path = state_dir / "events.jsonl"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("status") != "complete":
        raise ValueError("cycle executor state is not complete")
    if state.get("cycle_id") != config.get("cycle_id") or state.get(
        "config_sha256"
    ) != config_hash:
        raise ValueError("cycle executor state config identity mismatch")
    if set(state.get("stages", {})) != {
        str(stage["stage_id"]) for stage in stages
    }:
        raise ValueError("cycle executor state stage set mismatch")
    adopted_count = 0
    executed_count = 0
    job_count = 0
    for stage in stages:
        saved = state["stages"][stage["stage_id"]]
        if saved.get("status") != "complete":
            raise ValueError(f"{stage['stage_id']}: state is incomplete")
        actual = [
            _artifact_record(_workspace_path(workspace, str(path)))
            for path in stage["outputs"]
        ]
        if actual != saved.get("outputs"):
            raise ValueError(f"{stage['stage_id']}: output hash mismatch")
        mode = saved.get("completion_mode")
        if mode == "adopted_sealed_manifest":
            adopted_count += 1
            if saved.get("jobs"):
                raise ValueError(f"{stage['stage_id']}: adopted stage contains jobs")
        elif mode == "executed":
            executed_count += 1
            jobs = saved.get("jobs", ())
            if {item.get("job_id") for item in jobs} != {
                item.get("job_id") for item in stage.get("jobs", ())
            }:
                raise ValueError(f"{stage['stage_id']}: job set mismatch")
            for job in jobs:
                log_path = Path(str(job.get("log_path", "")))
                if job.get("returncode") != 0 or not log_path.is_file():
                    raise ValueError(f"{stage['stage_id']}: unsuccessful job record")
                if file_sha256(log_path) != job.get("log_sha256"):
                    raise ValueError(f"{stage['stage_id']}: job log hash mismatch")
            job_count += len(jobs)
        else:
            raise ValueError(f"{stage['stage_id']}: unknown completion mode")

    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    event_head = _validate_event_chain(
        events, cycle_id=config["cycle_id"], config_hash=config_hash
    )
    if state.get("event_head_sha256") != event_head:
        raise ValueError("cycle executor state event head differs from event log")
    if not events or events[-1].get("event") != "run_completed":
        raise ValueError("cycle executor events lack a terminal completion")
    configured_jobs = {
        (str(stage["stage_id"]), str(job["job_id"])): job
        for stage in stages
        for job in stage.get("jobs", ())
    }
    started_events: dict[tuple[str, str], list[dict]] = {}
    finished_events: dict[tuple[str, str], list[dict]] = {}
    for event in events:
        key = (str(event.get("stage_id", "")), str(event.get("job_id", "")))
        if event.get("event") == "job_started":
            started_events.setdefault(key, []).append(event)
        elif event.get("event") == "job_finished":
            finished_events.setdefault(key, []).append(event)
    executed_jobs = {
        (str(stage["stage_id"]), str(job["job_id"])): job
        for stage in stages
        for job in state["stages"][stage["stage_id"]].get("jobs", ())
    }
    if set(started_events) != set(executed_jobs) or set(finished_events) != set(
        executed_jobs
    ):
        raise ValueError("cycle executor job event set differs from executed state")
    for key, saved_job in executed_jobs.items():
        if key not in configured_jobs:
            raise ValueError("cycle executor state contains an unconfigured job")
        starts = started_events[key]
        finishes = finished_events[key]
        if len(starts) != len(finishes):
            raise ValueError("cycle executor job start/finish counts differ")
        configured = configured_jobs[key]
        expected_attempts = list(range(1, len(starts) + 1))
        if [int(item.get("attempt", 1)) for item in starts] != expected_attempts:
            raise ValueError("cycle executor job start attempts are not contiguous")
        if [int(item.get("attempt", 1)) for item in finishes] != expected_attempts:
            raise ValueError("cycle executor job finish attempts are not contiguous")
        for start, finish in zip(starts, finishes):
            if start.get("command_sha256") != _command_sha256(configured["argv"]):
                raise ValueError("cycle executor job command hash mismatch")
            log_path = Path(str(finish.get("log_path", "")))
            if not log_path.is_file() or file_sha256(log_path) != finish.get(
                "log_sha256"
            ):
                raise ValueError("cycle executor historical job log hash mismatch")
        if finishes[-1].get("returncode") != 0:
            raise ValueError("cycle executor final job attempt did not succeed")
        for field in ("attempt", "returncode", "log_path", "log_sha256"):
            if finishes[-1].get(field, 1) != saved_job.get(field, 1):
                raise ValueError(f"cycle executor job finish {field} mismatch")
    manifest_replay = None
    if config.get("adopt_manifest"):
        manifest_path = _workspace_path(workspace, str(config["adopt_manifest"]))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_replay = audit_evolution_cycle_manifest(
            manifest, manifest_path=manifest_path
        )["replay_equal"]
    event_counts: dict[str, int] = {}
    for event in events:
        name = str(event["event"])
        event_counts[name] = event_counts.get(name, 0) + 1
    run_started = [event for event in events if event["event"] == "run_started"]
    resume_run_count = sum(
        event.get("state_status") == "complete" for event in run_started
    )
    return {
        "status": "passed",
        "cycle_id": config["cycle_id"],
        "config_path": config_path.as_posix(),
        "config_sha256": config_hash,
        "state_path": state_path.as_posix(),
        "state_sha256": file_sha256(state_path),
        "events_path": events_path.as_posix(),
        "events_sha256": file_sha256(events_path),
        "stage_count": len(stages),
        "executed_stage_count": executed_count,
        "adopted_stage_count": adopted_count,
        "resume_run_count": resume_run_count,
        "stage_recovery_event_count": event_counts.get("stage_recovered", 0),
        "job_count": job_count,
        "event_count": len(events),
        "event_head_sha256": event_head,
        "event_counts": dict(sorted(event_counts.items())),
        "manifest_replay_verified": manifest_replay,
    }
