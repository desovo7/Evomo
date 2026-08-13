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
    select_tasks_by_type,
    summarize_variant,
    write_json,
)

__all__ = [
    "CANONICAL_TASK_TYPES",
    "EpisodeMetrics",
    "build_cross_variant_comparison",
    "build_paired_success_analysis",
    "compute_episode_metrics",
    "ensure_run_config",
    "load_completed_episode",
    "merge_variant_summaries",
    "persist_episode_artifacts",
    "render_comparison_markdown",
    "select_tasks_by_type",
    "summarize_variant",
    "write_json",
    "write_trajectory_logs",
]
