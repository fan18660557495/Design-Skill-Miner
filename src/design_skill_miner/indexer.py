from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .attribution import attribute_project
from .ingest import load_sessions
from .models import IndexedSession


def build_index(sessions_root: Path, cwd_prefix: str | None = None) -> list[IndexedSession]:
    sessions = load_sessions(sessions_root)
    indexed: list[IndexedSession] = []
    for session in sessions:
        attribution = attribute_project(session, cwd_prefix=cwd_prefix)
        indexed.append(
            IndexedSession(
                session_id=session.session_id,
                source_path=session.source_path,
                date=session.date,
                cwd=session.cwd,
                project_id=attribution.project_id,
                project_confidence=attribution.confidence,
                signals=attribution.signals,
                message_count=len(session.messages),
            )
        )
    return indexed


def write_index(indexed_sessions: list[IndexedSession], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([item.to_dict() for item in indexed_sessions], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path


def summarize_projects(indexed_sessions: list[IndexedSession]) -> list[tuple[str, int]]:
    counts = Counter(item.project_id for item in indexed_sessions)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))

