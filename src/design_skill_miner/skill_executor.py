from __future__ import annotations

from dataclasses import dataclass

from .models import Insight
from .skill_registry import SkillDefinition
from .skill_router import SkillSelection


@dataclass(frozen=True)
class SkillExecution:
    skill: SkillDefinition
    insights: list[Insight]
    available_categories: list[str]
    generated_description: str


def apply_skill_strategy(
    insights: list[Insight],
    selection: SkillSelection,
    *,
    skill_name: str,
    description: str | None = None,
) -> SkillExecution:
    skill = selection.skill
    priority = {
        category: index for index, category in enumerate(skill.preferred_output_categories + skill.focus_categories)
    }
    ordered = sorted(
        insights,
        key=lambda item: (
            priority.get(item.category, 999),
            -item.frequency,
            item.title,
        ),
    )
    available_categories = []
    for insight in ordered:
        if insight.category not in available_categories:
            available_categories.append(insight.category)

    generated_description = description or (
        f"Use when the task is about {skill.name.lower()} and needs the repeated design rules distilled "
        f"from historical conversations into the {skill_name} draft."
    )
    return SkillExecution(
        skill=skill,
        insights=ordered,
        available_categories=available_categories,
        generated_description=generated_description,
    )
