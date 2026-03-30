from __future__ import annotations

from dataclasses import dataclass

from .review import ReviewReport
from .skill_registry import list_skill_definitions


@dataclass(frozen=True)
class PolicyDecision:
    action: str
    reason: str
    next_min_frequency: int | None = None
    next_skill_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "reason": self.reason,
            "next_min_frequency": self.next_min_frequency,
            "next_skill_id": self.next_skill_id,
        }


def decide_next_action(
    *,
    cycle_index: int,
    max_cycles: int,
    review: ReviewReport,
    has_insights: bool,
    min_score: float,
    current_min_frequency: int,
    current_skill_id: str,
    category_scores: dict[str, int],
    explicit_skill_id: str | None = None,
) -> PolicyDecision:
    if cycle_index >= max_cycles - 1:
        return PolicyDecision("finish", "已达到最大循环次数，结束自动重规划。")

    reason_counts = review.reason_counts
    if not has_insights:
        return PolicyDecision(
            "collect_more_evidence",
            "当前没有可沉淀的候选，提升重复阈值后再扫描一轮。",
            next_min_frequency=current_min_frequency + 1,
        )

    if reason_counts.get("insufficient_evidence", 0) > 0:
        return PolicyDecision(
            "collect_more_evidence",
            "证据不足是主要风险，先提升重复阈值并补充扫描。",
            next_min_frequency=current_min_frequency + 1,
        )

    if reason_counts.get("duplicate_rules", 0) > 0 and not explicit_skill_id:
        next_skill = suggest_alternative_skill(current_skill_id, category_scores)
        if next_skill:
            return PolicyDecision(
                "switch_skill",
                f"重复规则较多，切换到 {next_skill} 重新聚焦分类边界。",
                next_skill_id=next_skill,
            )

    if review.score < min_score:
        return PolicyDecision(
            "collect_more_evidence",
            "总体分数仍低于目标分，继续补充扫描后再评估。",
            next_min_frequency=current_min_frequency + 1,
        )

    return PolicyDecision("finish", "当前质量达到目标分，进入草稿生成。")


def suggest_alternative_skill(current_skill_id: str, category_scores: dict[str, int]) -> str | None:
    skills = [skill for skill in list_skill_definitions() if skill.skill_id != current_skill_id]
    if not skills:
        return None
    ranked = sorted(
        skills,
        key=lambda skill: (
            sum(category_scores.get(category, 0) * 2 for category in skill.focus_categories)
            + sum(category_scores.get(category, 0) for category in skill.preferred_output_categories),
            skill.skill_id,
        ),
        reverse=True,
    )
    candidate = ranked[0]
    score = sum(category_scores.get(category, 0) for category in candidate.focus_categories)
    if score <= 0:
        return None
    return candidate.skill_id
