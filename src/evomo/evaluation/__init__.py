"""Evaluation metrics and trajectory reporting."""

from evomo.evaluation.trajectory_log import (
    EpisodeMetrics,
    compute_episode_metrics,
    write_trajectory_logs,
)
from evomo.evaluation.multitask import (
    CANONICAL_TASK_TYPES,
    build_paired_success_analysis,
    build_cross_variant_comparison,
    ensure_run_config,
    load_completed_episode,
    merge_variant_summaries,
    persist_episode_artifacts,
    render_comparison_markdown,
    select_all_tasks_by_type,
    select_tasks_by_type,
    summarize_variant,
    write_json,
)
from evomo.evaluation.candidate_gate import (
    ExperienceSelection,
    audit_experience_candidate_decision,
    decide_experience_candidate,
    file_sha256,
    resolve_experience_selection,
)
from evomo.evaluation.evolution_cycle import (
    EVOLUTION_CYCLE_SCHEMA_VERSION,
    audit_evolution_cycle_manifest,
    build_evolution_cycle_manifest,
    directory_sha256,
)
from evomo.evaluation.cycle_executor import (
    CYCLE_EXECUTOR_SCHEMA_VERSION,
    CycleExecutor,
    audit_cycle_executor_state,
    run_cycle_executor,
)
from evomo.evaluation.qwen_cycle_plan import (
    QWEN_CYCLE_PLAN_SCHEMA_VERSION,
    TASK_TYPE_SHARDS,
    build_qwen_evolution_cycle_plan,
)
from evomo.evaluation.evaluation_ledger import (
    EVALUATION_LEDGER_SCHEMA_VERSION,
    audit_evaluation_ledger,
    register_audited_evaluation_report,
    register_completed_evaluation_cycle,
    reserve_alfworld_evaluation_tasks,
    task_ids_sha256,
)
from evomo.evaluation.experience_pool import (
    freeze_experience_pool,
    load_frozen_experience_pool,
    previously_run_task_ids,
    task_ids_sha256 as experience_pool_task_ids_sha256,
)

__all__ = [
    "CANONICAL_TASK_TYPES",
    "CYCLE_EXECUTOR_SCHEMA_VERSION",
    "CycleExecutor",
    "QWEN_CYCLE_PLAN_SCHEMA_VERSION",
    "TASK_TYPE_SHARDS",
    "EpisodeMetrics",
    "ExperienceSelection",
    "EVOLUTION_CYCLE_SCHEMA_VERSION",
    "EVALUATION_LEDGER_SCHEMA_VERSION",
    "build_cross_variant_comparison",
    "build_paired_success_analysis",
    "audit_experience_candidate_decision",
    "audit_cycle_executor_state",
    "audit_evolution_cycle_manifest",
    "audit_evaluation_ledger",
    "build_evolution_cycle_manifest",
    "build_qwen_evolution_cycle_plan",
    "compute_episode_metrics",
    "decide_experience_candidate",
    "directory_sha256",
    "ensure_run_config",
    "file_sha256",
    "resolve_experience_selection",
    "run_cycle_executor",
    "load_completed_episode",
    "merge_variant_summaries",
    "persist_episode_artifacts",
    "render_comparison_markdown",
    "register_completed_evaluation_cycle",
    "register_audited_evaluation_report",
    "reserve_alfworld_evaluation_tasks",
    "select_all_tasks_by_type",
    "select_tasks_by_type",
    "summarize_variant",
    "task_ids_sha256",
    "write_json",
    "write_trajectory_logs",
    "freeze_experience_pool",
    "load_frozen_experience_pool",
    "previously_run_task_ids",
    "experience_pool_task_ids_sha256",
]
