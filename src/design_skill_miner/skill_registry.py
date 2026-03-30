from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from importlib import resources

from .models import InsightCategory


@dataclass(frozen=True)
class SkillDefinition:
    skill_id: str
    name: str
    description: str
    when_to_use: list[str]
    focus_categories: list[InsightCategory]
    preferred_output_categories: list[InsightCategory]
    review_min_score: float
    review_min_confidence: float
    review_min_evidence: int
    review_focus: list[str]
    draft_intro: str
    reading_guidance: list[str]
    usage_boundaries: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def list_skill_definitions() -> list[SkillDefinition]:
    skill_dir = resources.files("design_skill_miner").joinpath("skills")
    skills: list[SkillDefinition] = []
    for entry in sorted(skill_dir.iterdir(), key=lambda item: item.name):
        if entry.suffix != ".json":
            continue
        payload = json.loads(entry.read_text(encoding="utf-8"))
        skills.append(_skill_from_dict(payload))
    return skills


def get_skill_definition(skill_id: str) -> SkillDefinition:
    for skill in list_skill_definitions():
        if skill.skill_id == skill_id:
            return skill
    raise ValueError(f"Unknown skill: {skill_id}")


def _skill_from_dict(payload: dict) -> SkillDefinition:
    return SkillDefinition(
        skill_id=str(payload["skill_id"]),
        name=str(payload["name"]),
        description=str(payload["description"]),
        when_to_use=[str(item) for item in payload.get("when_to_use", [])],
        focus_categories=[str(item) for item in payload.get("focus_categories", [])],  # type: ignore[list-item]
        preferred_output_categories=[str(item) for item in payload.get("preferred_output_categories", [])],  # type: ignore[list-item]
        review_min_score=float(payload.get("review_min_score", 0.6)),
        review_min_confidence=float(payload.get("review_min_confidence", 0.62)),
        review_min_evidence=int(payload.get("review_min_evidence", 2)),
        review_focus=[str(item) for item in payload.get("review_focus", [])],
        draft_intro=str(payload.get("draft_intro", "")),
        reading_guidance=[str(item) for item in payload.get("reading_guidance", [])],
        usage_boundaries=[str(item) for item in payload.get("usage_boundaries", [])],
    )
