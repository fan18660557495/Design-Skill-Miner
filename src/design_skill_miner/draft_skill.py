from __future__ import annotations

import json
from pathlib import Path

from .models import Insight
from .skill_registry import SkillDefinition


CATEGORY_FILES = {
    "principles": "principles.md",
    "page-patterns": "page-patterns.md",
    "interaction-patterns": "interaction-patterns.md",
    "component-patterns": "component-patterns.md",
    "style-system": "style-system.md",
    "content-rules": "content-rules.md",
}


def load_insights(path: Path) -> list[Insight]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Insight.from_dict(item) for item in raw]


def write_skill_draft(
    insights: list[Insight],
    out_dir: Path,
    *,
    skill_name: str,
    description: str | None = None,
    applied_skill: SkillDefinition | None = None,
    ordered_categories: list[str] | None = None,
) -> dict[str, Path]:
    refs_dir = out_dir / "references"
    refs_dir.mkdir(parents=True, exist_ok=True)

    grouped: dict[str, list[Insight]] = {}
    for insight in insights:
        grouped.setdefault(insight.category, []).append(insight)

    outputs: dict[str, Path] = {}
    for category, filename in CATEGORY_FILES.items():
        bucket = grouped.get(category, [])
        if not bucket:
            continue
        path = refs_dir / filename
        path.write_text(render_category_doc(category, bucket), encoding="utf-8")
        outputs[category] = path

    skill_path = out_dir / "SKILL.md"
    category_order = ordered_categories or [category for category in CATEGORY_FILES if category in grouped]
    skill_path.write_text(
        render_skill_entry(
            skill_name=skill_name,
            description=description or default_description(skill_name),
            available_categories=category_order,
            applied_skill=applied_skill,
        ),
        encoding="utf-8",
    )
    outputs["skill"] = skill_path

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "skill_name": skill_name,
                "description": description or default_description(skill_name),
                "categories": category_order,
                "insight_count": len(insights),
                "applied_skill": applied_skill.to_dict() if applied_skill else None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    outputs["manifest"] = manifest_path
    return outputs


def default_description(skill_name: str) -> str:
    return (
        f"Use when the task matches the repeated design and interaction rules distilled into the "
        f"{skill_name} skill draft, including page patterns, interaction patterns, component patterns, "
        "style system rules, and content rules."
    )


def render_skill_entry(
    skill_name: str,
    description: str,
    available_categories: list[str],
    *,
    applied_skill: SkillDefinition | None = None,
) -> str:
    labels = {
        "principles": "整体设计原则",
        "page-patterns": "页面模式",
        "interaction-patterns": "交互模式",
        "component-patterns": "组件模式",
        "style-system": "样式系统",
        "content-rules": "表达规范",
    }

    lines = [
        "---",
        f"name: {skill_name}",
        f"description: {description}",
        "---",
        "",
        f"# {skill_name}",
        "",
        "这个 skill 草稿由历史设计对话自动提炼生成，适合先作为候选规范，再由人工审核后定稿。",
        "",
    ]

    if applied_skill:
        lines.extend(
            [
                "## 本次使用的沉淀 Skill",
                "",
                f"- 名称：{applied_skill.name}",
                f"- 作用：{applied_skill.description}",
            ]
        )
        for item in applied_skill.when_to_use:
            lines.append(f"- 适用场景：{item}")
        lines.extend(
            [
                "",
                applied_skill.draft_intro,
                "",
            ]
        )

    reading_guidance = applied_skill.reading_guidance if applied_skill and applied_skill.reading_guidance else [
        "先读与当前任务最接近的分类文件，不要一次性加载全部内容。",
        "先看规则总览，再看候选条目，最后按需查看证据附录。",
        "把这里的规则当成候选默认做法，人工确认后再进入正式 skill。",
    ]
    usage_boundaries = applied_skill.usage_boundaries if applied_skill and applied_skill.usage_boundaries else [
        "当前内容来自对话提炼，可能包含项目语境，需要人工复核。",
        "如果同一主题仍在争论，不要直接写入正式 skill。",
        "若某条规则只适用于单个项目，应移动到项目专属 skill，而不是通用 skill。",
    ]

    lines.extend(
        [
            "## 推荐读取顺序",
            "",
        ]
    )
    for item in reading_guidance:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## 读取路径",
            "",
        ]
    )

    for category in available_categories:
        filename = CATEGORY_FILES[category]
        lines.append(f"- 做{labels[category]}：读 `references/{filename}`")

    lines.extend(
        [
            "",
            "## 使用边界",
            "",
        ]
    )
    for item in usage_boundaries:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def render_category_doc(category: str, insights: list[Insight]) -> str:
    title = {
        "principles": "设计原则",
        "page-patterns": "页面模式",
        "interaction-patterns": "交互模式",
        "component-patterns": "组件模式",
        "style-system": "样式系统",
        "content-rules": "表达规范",
    }[category]

    lines = [
        f"# {title}",
        "",
        "以下内容由历史对话自动提炼，已整理为候选规则。建议人工复核后再进入正式规范。",
        "",
        "## 规则总览",
        "",
    ]

    consolidated_rules = collect_consolidated_rules(insights)
    for rule in consolidated_rules:
        lines.append(f"- {rule}")
    lines.append("")

    lines.extend(["## 候选条目", ""])

    for insight in insights:
        lines.extend(
            [
                f"### {insight.title}",
                "",
                insight.summary,
                "",
                "#### 沉淀信号",
                "",
                f"- 重复出现：{insight.frequency} 次",
                f"- 当前稳定性：{stability_label(insight.stability)}",
                f"- 作用范围：{scope_label(insight.scope)}",
                f"- 置信度：{int(round(insight.confidence * 100, 0))}%",
                "",
                "#### 建议规则",
            ]
        )
        for rule in insight.normalized_rules:
            lines.append(f"- {rule}")
        lines.append("")

    lines.extend(["## 证据附录", ""])
    for insight in insights:
        lines.extend(
            [
                f"### {insight.title}",
                "",
            ]
        )
        for evidence in insight.evidence:
            date = evidence.date or "unknown-date"
            lines.append(f"- `{date}` [{evidence.source}] - {evidence.quote_summary}")
        lines.append("")

    return "\n".join(lines)


def collect_consolidated_rules(insights: list[Insight]) -> list[str]:
    seen: set[str] = set()
    rules: list[str] = []
    for insight in insights:
        for rule in insight.normalized_rules:
            if rule in seen:
                continue
            seen.add(rule)
            rules.append(rule)
    return rules


def stability_label(value: str) -> str:
    return {
        "stable": "稳定",
        "emerging": "待收敛",
        "disputed": "仍有争议",
    }.get(value, value)


def scope_label(value: str) -> str:
    return {
        "general_design_skill": "通用设计 skill",
        "project_specific_skill": "项目专属 skill",
        "product_doc": "产品文档",
        "temporary_issue": "临时问题",
    }.get(value, value)
