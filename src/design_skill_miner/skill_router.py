from __future__ import annotations

from dataclasses import asdict, dataclass

from .models import Insight
from .skill_registry import SkillDefinition, get_skill_definition, list_skill_definitions


@dataclass(frozen=True)
class SkillSelection:
    skill: SkillDefinition
    reason: str
    category_scores: dict[str, int]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["skill"] = self.skill.to_dict()
        return payload


def choose_skill_for_insights(insights: list[Insight], explicit_skill_id: str | None = None) -> SkillSelection:
    if explicit_skill_id:
        skill = get_skill_definition(explicit_skill_id)
        return SkillSelection(
            skill=skill,
            reason="显式指定该 skill，按指定 skill 执行。",
            category_scores=category_scores(insights),
        )

    scores = category_scores(insights)
    skills = list_skill_definitions()
    ranked = sorted(
        skills,
        key=lambda skill: (
            sum(scores.get(category, 0) * 2 for category in skill.focus_categories)
            + sum(scores.get(category, 0) for category in skill.preferred_output_categories),
            skill.skill_id,
        ),
        reverse=True,
    )
    selected = ranked[0] if ranked else get_skill_definition("page-pattern-skill")
    matched = [category for category in selected.focus_categories if scores.get(category, 0) > 0]
    if matched:
        reason = f"当前项目里最集中的主题是：{', '.join(matched)}，因此优先使用 {selected.name}。"
    else:
        reason = f"当前结果还不明显偏向某一类主题，先使用 {selected.name} 作为默认沉淀 skill。"
    return SkillSelection(skill=selected, reason=reason, category_scores=scores)


def category_scores(insights: list[Insight]) -> dict[str, int]:
    scores: dict[str, int] = {}
    for insight in insights:
        scores[insight.category] = scores.get(insight.category, 0) + insight.frequency
    return scores
