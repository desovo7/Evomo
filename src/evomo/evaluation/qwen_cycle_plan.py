"""Plan a complete three-GPU Qwen experience-evolution cycle."""

from __future__ import annotations

import sys
from pathlib import Path

from .multitask import CANONICAL_TASK_TYPES

QWEN_CYCLE_PLAN_SCHEMA_VERSION = 1
TASK_TYPE_SHARDS = tuple(
    tuple(CANONICAL_TASK_TYPES[index : index + 2]) for index in range(0, 6, 2)
)


def _job(job_id: str, argv: list[str], *, gpu: str | None = None) -> dict:
    environment = {"PYTHONPATH": "src"}
    if gpu is not None:
        environment["CUDA_VISIBLE_DEVICES"] = gpu
    return {"job_id": job_id, "argv": argv, "env": environment}


def build_qwen_evolution_cycle_plan(
    *,
    cycle_id: str,
    report_root: str | Path,
    incumbent_experience: str | Path,
    candidate_version: str,
    data_root: str | Path,
    model_path: str | Path,
    evaluation_ledger: str | Path,
    python_executable: str | Path = sys.executable,
    gpus: tuple[str, str, str] = ("0", "1", "2"),
    development_offset: int = 2,
    seed: int = 42,
    max_steps: int = 30,
    max_new_tokens: int = 96,
    max_history_items: int = 6,
) -> dict:
    """Return an executor config from rollout through manifest audit."""

    if not cycle_id.strip() or not candidate_version.strip():
        raise ValueError("cycle_id and candidate_version must be non-empty")
    if len(gpus) != 3 or len(set(gpus)) != 3 or any(not gpu.strip() for gpu in gpus):
        raise ValueError("exactly three unique non-empty GPU IDs are required")
    if development_offset < 0:
        raise ValueError("development_offset must be non-negative")
    for name, value in (
        ("seed", seed),
        ("max_steps", max_steps),
        ("max_new_tokens", max_new_tokens),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if max_history_items < 0:
        raise ValueError("max_history_items must be non-negative")

    root = Path(report_root).as_posix()
    incumbent = Path(incumbent_experience).as_posix()
    data = Path(data_root).as_posix()
    model = Path(model_path).as_posix()
    ledger = Path(evaluation_ledger).as_posix()
    python = Path(python_executable).as_posix()
    development = f"{root}/development"
    validation = f"{root}/validation"
    candidate = f"{root}/candidate.json"
    evolution_audit = f"{root}/evolution_audit.json"
    development_audit = f"{development}/audit.json"
    comparison = f"{validation}/comparison.json"
    validation_audit = f"{validation}/audit.json"
    decision = f"{root}/decision.json"
    manifest = f"{root}/cycle_manifest.json"
    manifest_audit = f"{root}/cycle_manifest_audit.json"
    reservation = f"{root}/evaluation_reservation.json"
    registration = f"{root}/evaluation_registration.json"

    common = [
        "--data-root", data,
        "--model-path", model,
        "--device", "cuda:0",
        "--seed", str(seed),
        "--max-steps", str(max_steps),
        "--max-new-tokens", str(max_new_tokens),
        "--max-history-items", str(max_history_items),
    ]

    def rollout_jobs(
        *,
        job_prefix: str,
        split: str,
        variant: str,
        experience: str,
        output: str,
        all_tasks: bool,
    ) -> list[dict]:
        jobs = []
        for index, (gpu, task_types) in enumerate(zip(gpus, TASK_TYPE_SHARDS)):
            selection = ["--all-tasks"] if all_tasks else [
                "--per-type", "1", "--task-offset", str(development_offset)
            ]
            argv = [
                python,
                "scripts/run_qwen_multitask_variant.py",
                *common,
                "--split", split,
                *selection,
                "--task-types", *task_types,
                "--variant", variant,
                "--experience-file", experience,
                "--output-dir", f"{output}/{variant}/shard_{index}",
            ]
            jobs.append(
                _job(
                    f"{job_prefix}-{variant.lower()}-gpu-{gpu}-shard-{index}",
                    argv,
                    gpu=gpu,
                )
            )
        return jobs

    development_jobs = rollout_jobs(
        job_prefix="development",
        split="valid_train",
        variant="I",
        experience=incumbent,
        output=development,
        all_tasks=False,
    )
    incumbent_jobs = rollout_jobs(
        job_prefix="validation-incumbent",
        split="valid_unseen",
        variant="I",
        experience=incumbent,
        output=validation,
        all_tasks=True,
    )
    candidate_jobs = rollout_jobs(
        job_prefix="validation-candidate",
        split="valid_unseen",
        variant="K",
        experience=candidate,
        output=validation,
        all_tasks=True,
    )

    stages = [
        {
            "stage_id": "development_rollout",
            "depends_on": [],
            "outputs": [f"{development}/I/shard_{index}" for index in range(3)],
            "jobs": development_jobs,
        },
        {
            "stage_id": "development_merge",
            "depends_on": ["development_rollout"],
            "outputs": [f"{development}/I/summary.json"],
            "jobs": [_job("merge-development", [python, "scripts/merge_qwen_multitask_shards.py", "--shard-root", f"{development}/I", "--output", f"{development}/I/summary.json"])],
        },
        {
            "stage_id": "development_audit",
            "depends_on": ["development_merge"],
            "outputs": [development_audit],
            "jobs": [_job("audit-development", [python, "scripts/audit_multitask_report.py", "--report-dir", development, "--variants", "I", "--variant-experience", f"I={incumbent}", "--protocol-role", "development", "--output", development_audit])],
        },
        {
            "stage_id": "experience_evolution",
            "depends_on": ["development_audit"],
            "outputs": [candidate],
            "jobs": [_job("evolve-candidate", [python, "scripts/evolve_failure_experiences.py", "--base", incumbent, "--episodes-root", f"{development}/I", "--source-split", "valid_train", "--version", candidate_version, "--enable-progress-rules", "--output", candidate])],
        },
        {
            "stage_id": "evolution_audit",
            "depends_on": ["experience_evolution"],
            "outputs": [evolution_audit],
            "jobs": [_job("audit-evolution", [python, "scripts/audit_experience_evolution.py", "--base", incumbent, "--child", candidate, "--episodes-root", f"{development}/I", "--source-split", "valid_train", "--output", evolution_audit])],
        },
        {
            "stage_id": "evaluation_reservation",
            "depends_on": ["evolution_audit"],
            "outputs": [reservation],
            "jobs": [_job("reserve-evaluation", [python, "scripts/reserve_alfworld_evaluation.py", "--ledger", ledger, "--receipt", reservation, "--cycle-id", cycle_id, "--data-root", data, "--split", "valid_unseen", "--task-types", *CANONICAL_TASK_TYPES])],
        },
        {
            "stage_id": "incumbent_validation_rollout",
            "depends_on": ["evaluation_reservation"],
            "outputs": [f"{validation}/I/shard_{index}" for index in range(3)],
            "jobs": incumbent_jobs,
        },
        {
            "stage_id": "incumbent_validation_merge",
            "depends_on": ["incumbent_validation_rollout"],
            "outputs": [f"{validation}/I/summary.json"],
            "jobs": [_job("merge-incumbent-validation", [python, "scripts/merge_qwen_multitask_shards.py", "--shard-root", f"{validation}/I", "--output", f"{validation}/I/summary.json"])],
        },
        {
            "stage_id": "candidate_validation_rollout",
            "depends_on": ["incumbent_validation_merge"],
            "outputs": [f"{validation}/K/shard_{index}" for index in range(3)],
            "jobs": candidate_jobs,
        },
        {
            "stage_id": "candidate_validation_merge",
            "depends_on": ["candidate_validation_rollout"],
            "outputs": [f"{validation}/K/summary.json"],
            "jobs": [_job("merge-candidate-validation", [python, "scripts/merge_qwen_multitask_shards.py", "--shard-root", f"{validation}/K", "--output", f"{validation}/K/summary.json"])],
        },
        {
            "stage_id": "validation_postprocess",
            "depends_on": ["candidate_validation_merge"],
            "outputs": [comparison, validation_audit],
            "jobs": [
                _job("build-comparison", [python, "scripts/summarize_qwen_multitask.py", "--input-dir", validation, "--split", "valid_unseen", "--all-tasks", "--variants", "I", "K"]),
                _job("audit-validation", [python, "scripts/audit_multitask_report.py", "--report-dir", validation, "--variants", "I", "K", "--variant-experience", f"I={incumbent}", "--variant-experience", f"K={candidate}", "--data-root", data, "--protocol-role", "evaluation", "--exclude-episodes-root", f"{development}/I", "--output", validation_audit]),
            ],
        },
        {
            "stage_id": "candidate_gate",
            "depends_on": ["validation_postprocess"],
            "outputs": [decision],
            "jobs": [_job("gate-candidate", [python, "scripts/gate_experience_candidate.py", "--comparison", comparison, "--validation-audit", validation_audit, "--evolution-audit", evolution_audit, "--incumbent", incumbent, "--candidate", candidate, "--output", decision])],
        },
        {
            "stage_id": "cycle_manifest",
            "depends_on": ["candidate_gate"],
            "outputs": [manifest],
            "jobs": [_job("build-manifest", [python, "scripts/build_evolution_cycle_manifest.py", "--cycle-id", cycle_id, "--incumbent-experience", incumbent, "--development-trajectories", f"{development}/I", "--development-summary", f"{development}/I/summary.json", "--development-audit", development_audit, "--candidate-experience", candidate, "--evolution-audit", evolution_audit, "--validation-trajectories", validation, "--validation-incumbent-summary", f"{validation}/I/summary.json", "--validation-candidate-summary", f"{validation}/K/summary.json", "--comparison", comparison, "--validation-audit", validation_audit, "--decision", decision, "--output", manifest])],
        },
        {
            "stage_id": "manifest_audit",
            "depends_on": ["cycle_manifest"],
            "outputs": [manifest_audit],
            "jobs": [_job("audit-manifest", [python, "scripts/audit_evolution_cycle_manifest.py", "--manifest", manifest, "--output", manifest_audit])],
        },
    ]
    return {
        "schema_version": QWEN_CYCLE_PLAN_SCHEMA_VERSION,
        "cycle_id": cycle_id,
        "workspace": ".",
        "max_parallel": 3,
        "state_dir": f"{root}/executor",
        "evaluation_registration": {
            "ledger_path": ledger,
            "receipt_path": registration,
            "manifest_path": manifest,
            "validation_summary_path": f"{validation}/I/summary.json",
            "executor_state_dir": f"{root}/executor",
        },
        "stages": stages,
    }
