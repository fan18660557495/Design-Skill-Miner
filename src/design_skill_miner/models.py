from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal


InsightCategory = Literal[
    "principles",
    "page-patterns",
    "interaction-patterns",
    "component-patterns",
    "style-system",
    "content-rules",
]

InsightDecision = Literal[
    "candidate_for_skill",
    "candidate_for_docs",
    "not_worthy_yet",
]

InsightScope = Literal[
    "general_design_skill",
    "project_specific_skill",
    "product_doc",
    "temporary_issue",
]

InsightStability = Literal["emerging", "stable", "disputed"]


@dataclass
class MessageRecord:
    role: str
    text: str
    file_refs: list[str] = field(default_factory=list)


@dataclass
class SessionRecord:
    session_id: str
    source_path: str
    date: str | None = None
    cwd: str | None = None
    messages: list[MessageRecord] = field(default_factory=list)

    @property
    def path(self) -> Path:
        return Path(self.source_path)


@dataclass
class ProjectAttribution:
    project_id: str
    confidence: float
    signals: list[str] = field(default_factory=list)


@dataclass
class CandidateMessage:
    session_id: str
    source_path: str
    date: str | None
    role: str
    text: str
    project_id: str
    category: InsightCategory


@dataclass
class Evidence:
    source: str
    date: str | None = None
    quote_summary: str = ""


@dataclass
class Insight:
    title: str
    summary: str
    category: InsightCategory
    granularity: str
    frequency: int
    decision: InsightDecision
    scope: InsightScope
    stability: InsightStability
    confidence: float
    why_it_repeats: list[str] = field(default_factory=list)
    proposed_rules: list[str] = field(default_factory=list)
    normalized_rules: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict) -> "Insight":
        evidence = [Evidence(**item) for item in value.get("evidence", [])]
        payload = dict(value)
        payload["evidence"] = evidence
        return cls(**payload)


@dataclass
class IndexedSession:
    session_id: str
    source_path: str
    date: str | None
    cwd: str | None
    project_id: str
    project_confidence: float
    signals: list[str] = field(default_factory=list)
    message_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)
