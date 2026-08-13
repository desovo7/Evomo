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

__all__ = [
    "CANONICAL_TASK_TYPES",
    "EpisodeMetrics",
    "ExperienceSelection",
    "EVOLUTION_CYCLE_SCHEMA_VERSION",
    "build_cross_variant_comparison",
    "build_paired_success_analysis",
    "audit_experience_candidate_decision",
    "audit_evolution_cycle_manifest",
    "build_evolution_cycle_manifest",
    "compute_episode_metrics",
    "decide_experience_candidate",
    "directory_sha256",
    "ensure_run_config",
    "file_sha256",
    "resolve_experience_selection",
    "load_completed_episode",
    "merge_variant_summaries",
    "persist_episode_artifacts",
    "render_comparison_markdown",
    "select_all_tasks_by_type",
    "select_tasks_by_type",
    "summarize_variant",
    "write_json",
    "write_trajectory_logs",
]
