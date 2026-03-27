from __future__ import annotations

import json
from pathlib import Path

from .models import Insight


def write_reports(insights: list[Insight], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "insights.json"
    md_path = out_dir / "insights.md"

    json_path.write_text(
        json.dumps([insight.to_dict() for insight in insights], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(insights), encoding="utf-8")
    return json_path, md_path


def render_markdown(insights: list[Insight]) -> str:
    lines = ["# Design Skill Miner Report", ""]
    if not insights:
        lines.extend(["没有发现可归纳的重复设计话题。", ""])
        return "\n".join(lines)

    for insight in insights:
        lines.extend(
            [
                f"## {insight.title}",
                "",
                f"- Category: `{insight.category}`",
                f"- Frequency: `{insight.frequency}`",
                f"- Decision: `{insight.decision}`",
                f"- Scope: `{insight.scope}`",
                f"- Stability: `{insight.stability}`",
                f"- Confidence: `{insight.confidence:.2f}`",
                "",
                "### Proposed Rules",
            ]
        )
        for rule in insight.normalized_rules:
            lines.append(f"- {rule}")
        lines.extend(["", "### Distillation Notes"])
        for rule in insight.proposed_rules:
            lines.append(f"- {rule}")
        lines.extend(["", "### Evidence"])
        for item in insight.evidence:
            date = item.date or "unknown-date"
            lines.append(f"- `{date}` [{item.source}] - {item.quote_summary}")
        lines.append("")

    return "\n".join(lines)
