from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class ProjectMemoryProfile:
    project_id: str
    suggested_min_frequency: int | None
    preferred_skill_id: str | None
    blocked_titles: list[str]
    recent_reason_counts: dict[str, int]
    total_runs: int

    def to_dict(self) -> dict:
        return asdict(self)


class AgentMemoryStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path.expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def load_project_profile(self, project_id: str) -> ProjectMemoryProfile:
        with self._connect() as conn:
            hint_row = conn.execute(
                """
                SELECT preferred_skill_id, suggested_min_frequency
                FROM project_hints
                WHERE project_id = ?
                """,
                (project_id,),
            ).fetchone()
            run_rows = conn.execute(
                """
                SELECT skill_id, review_score, min_frequency, reason_codes
                FROM run_history
                WHERE project_id = ?
                ORDER BY id DESC
                LIMIT 40
                """,
                (project_id,),
            ).fetchall()
            blocked_rows = conn.execute(
                """
                SELECT title
                FROM rejected_titles
                WHERE project_id = ?
                ORDER BY count DESC, updated_at DESC
                LIMIT 12
                """,
                (project_id,),
            ).fetchall()
            total_runs = conn.execute(
                "SELECT COUNT(*) FROM run_history WHERE project_id = ?",
                (project_id,),
            ).fetchone()[0]

        reason_counts = Counter()
        low_evidence_frequencies: list[int] = []
        skill_scores: dict[str, list[float]] = defaultdict(list)
        for row in run_rows:
            reason_codes = _parse_reason_codes(row[3])
            reason_counts.update(reason_codes)
            if "insufficient_evidence" in reason_codes and row[2]:
                low_evidence_frequencies.append(int(row[2]))
            if row[0]:
                skill_scores[str(row[0])].append(float(row[1]))

        suggested = hint_row[1] if hint_row and hint_row[1] else None
        if low_evidence_frequencies:
            suggested_from_history = max(low_evidence_frequencies)
            if suggested is None:
                suggested = suggested_from_history
            else:
                suggested = max(int(suggested), int(suggested_from_history))

        preferred_skill = hint_row[0] if hint_row and hint_row[0] else None
        if not preferred_skill and skill_scores:
            preferred_skill = max(
                skill_scores.items(),
                key=lambda item: (sum(item[1]) / len(item[1]), len(item[1]), item[0]),
            )[0]

        blocked_titles = [str(row[0]) for row in blocked_rows]
        return ProjectMemoryProfile(
            project_id=project_id,
            suggested_min_frequency=int(suggested) if suggested else None,
            preferred_skill_id=str(preferred_skill) if preferred_skill else None,
            blocked_titles=blocked_titles,
            recent_reason_counts=dict(reason_counts),
            total_runs=int(total_runs),
        )

    def record_run(
        self,
        *,
        project_id: str,
        goal: str,
        skill_id: str | None,
        review_score: float,
        min_frequency: int,
        reason_codes: list[str],
        approved_titles: list[str],
        rejected_titles: list[str],
    ) -> None:
        now = _now()
        reason_codes_json = json.dumps(sorted(set(reason_codes)), ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO run_history (
                    ts, project_id, goal, skill_id, review_score, min_frequency,
                    reason_codes, approved_count, rejected_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    project_id,
                    goal,
                    skill_id,
                    float(review_score),
                    int(min_frequency),
                    reason_codes_json,
                    len(approved_titles),
                    len(rejected_titles),
                ),
            )

            for title in rejected_titles:
                conn.execute(
                    """
                    INSERT INTO rejected_titles (project_id, title, count, updated_at)
                    VALUES (?, ?, 1, ?)
                    ON CONFLICT(project_id, title)
                    DO UPDATE SET count = rejected_titles.count + 1, updated_at = excluded.updated_at
                    """,
                    (project_id, title, now),
                )

            existing_hint = conn.execute(
                """
                SELECT preferred_skill_id, suggested_min_frequency
                FROM project_hints
                WHERE project_id = ?
                """,
                (project_id,),
            ).fetchone()
            preferred_skill_id = existing_hint[0] if existing_hint else None
            suggested_min_frequency = int(existing_hint[1]) if existing_hint and existing_hint[1] else None

            if skill_id and review_score >= 0.75:
                preferred_skill_id = skill_id
            if "insufficient_evidence" in reason_codes:
                needed_frequency = max(2, min_frequency + 1)
                suggested_min_frequency = (
                    needed_frequency
                    if suggested_min_frequency is None
                    else max(suggested_min_frequency, needed_frequency)
                )

            conn.execute(
                """
                INSERT INTO project_hints (project_id, preferred_skill_id, suggested_min_frequency, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(project_id)
                DO UPDATE SET
                    preferred_skill_id = excluded.preferred_skill_id,
                    suggested_min_frequency = excluded.suggested_min_frequency,
                    updated_at = excluded.updated_at
                """,
                (project_id, preferred_skill_id, suggested_min_frequency, now),
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS run_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    skill_id TEXT,
                    review_score REAL NOT NULL,
                    min_frequency INTEGER NOT NULL,
                    reason_codes TEXT NOT NULL,
                    approved_count INTEGER NOT NULL,
                    rejected_count INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rejected_titles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL,
                    UNIQUE(project_id, title)
                );

                CREATE TABLE IF NOT EXISTS project_hints (
                    project_id TEXT PRIMARY KEY,
                    preferred_skill_id TEXT,
                    suggested_min_frequency INTEGER,
                    updated_at TEXT NOT NULL
                );
                """
            )


def _parse_reason_codes(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
