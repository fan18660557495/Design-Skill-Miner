from __future__ import annotations

from pathlib import Path

from .attribution import attribute_project, project_id_from_prefix
from .cluster import cluster_candidates
from .distill import distill_cluster
from .filter import extract_design_candidates
from .ingest import load_sessions
from .models import Insight


def generate_insights(
    sessions_root: Path,
    cwd_prefix: str | None = None,
    min_frequency: int = 2,
) -> tuple[list[Insight], dict[str, int]]:
    sessions = load_sessions(sessions_root)
    candidates = []
    target_project_id = project_id_from_prefix(cwd_prefix) if cwd_prefix else None

    for session in sessions:
        attribution = attribute_project(session, cwd_prefix=cwd_prefix)
        if target_project_id and attribution.project_id != target_project_id:
            continue
        candidates.extend(extract_design_candidates(session, attribution))

    grouped = cluster_candidates(candidates)
    insights: list[Insight] = []
    for (topic_key, category), items in grouped.items():
        unique_sessions = len({item.session_id for item in items})
        if unique_sessions < min_frequency:
            continue
        insights.append(distill_cluster(topic_key, category, items))

    insights.sort(key=lambda item: (-item.frequency, item.category, item.title))
    stats = {
        "sessions_scanned": len(sessions),
        "candidate_messages": len(candidates),
        "insights_written": len(insights),
    }
    return insights, stats
