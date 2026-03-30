from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Literal

from .models import Insight


ReviewSeverity = Literal["info", "warning", "error"]

GENERIC_RULE_MARKERS = (
    "统一默认做法",
    "沉淀统一",
    "统一状态变化",
    "候选规范",
)


@dataclass
class ReviewFinding:
    code: str
    severity: ReviewSeverity
    insight_title: str
    message: str
    suggestion: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReviewReport:
    score: float
    findings: list[ReviewFinding] = field(default_factory=list)
    approved_titles: list[str] = field(default_factory=list)
    rejected_titles: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    auto_actions: list[str] = field(default_factory=list)
    reason_counts: dict[str, int] = field(default_factory=dict)
    primary_reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "findings": [finding.to_dict() for finding in self.findings],
            "approved_titles": self.approved_titles,
            "rejected_titles": self.rejected_titles,
            "recommendations": self.recommendations,
            "auto_actions": self.auto_actions,
            "reason_counts": self.reason_counts,
            "primary_reason": self.primary_reason,
        }


def review_insights(
    insights: list[Insight],
    *,
    min_confidence: float = 0.62,
    min_evidence: int = 2,
) -> ReviewReport:
    findings: list[ReviewFinding] = []
    duplicate_rule_titles = find_duplicate_rules(insights)
    approved_titles: list[str] = []
    rejected_titles: list[str] = []

    for insight in insights:
        insight_findings = review_single_insight(
            insight,
            min_confidence=min_confidence,
            min_evidence=min_evidence,
            duplicate_rule_titles=duplicate_rule_titles.get(insight.title, []),
        )
        findings.extend(insight_findings)

        has_error = any(item.severity == "error" for item in insight_findings)
        if has_error:
            rejected_titles.append(insight.title)
        else:
            approved_titles.append(insight.title)

    score = compute_review_score(findings)
    reason_counts, primary_reason = summarize_reason_codes(findings)
    recommendations = build_recommendations(findings, score, primary_reason=primary_reason)
    auto_actions = build_auto_actions(findings)
    return ReviewReport(
        score=score,
        findings=findings,
        approved_titles=approved_titles,
        rejected_titles=rejected_titles,
        recommendations=recommendations,
        auto_actions=auto_actions,
        reason_counts=reason_counts,
        primary_reason=primary_reason,
    )


def review_single_insight(
    insight: Insight,
    *,
    min_confidence: float,
    min_evidence: int,
    duplicate_rule_titles: list[str],
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []

    if len(insight.evidence) < min_evidence or insight.frequency < min_evidence:
        findings.append(
            ReviewFinding(
                code="insufficient_evidence",
                severity="error",
                insight_title=insight.title,
                message="跨会话证据不足，当前候选更像一次性讨论而不是稳定规则。",
                suggestion="提高 min_frequency，或者继续积累更多会话后再沉淀。",
            )
        )

    if not insight.normalized_rules:
        findings.append(
            ReviewFinding(
                code="missing_rules",
                severity="error",
                insight_title=insight.title,
                message="该候选没有生成可执行规则，无法进入技能草稿。",
                suggestion="补充至少 2 条可执行规则，或者丢弃该主题。",
            )
        )

    if insight.confidence < min_confidence:
        findings.append(
            ReviewFinding(
                code="low_confidence",
                severity="warning",
                insight_title=insight.title,
                message=f"当前置信度 {insight.confidence:.2f} 低于建议阈值 {min_confidence:.2f}。",
                suggestion="优先人工复核分类和聚类是否准确。",
            )
        )

    if any(marker in rule for marker in GENERIC_RULE_MARKERS for rule in insight.normalized_rules):
        findings.append(
            ReviewFinding(
                code="generic_rule",
                severity="warning",
                insight_title=insight.title,
                message="规则表达偏空，像原则口号，不够可执行。",
                suggestion="改写成具体约束，例如结构、状态、间距、命名等动作性规则。",
            )
        )

    if duplicate_rule_titles:
        findings.append(
            ReviewFinding(
                code="duplicate_rules",
                severity="warning",
                insight_title=insight.title,
                message=f"有规则与其他候选重复：{', '.join(sorted(duplicate_rule_titles))}。",
                suggestion="合并相近主题，避免一个规则在多个分类重复出现。",
            )
        )

    return findings


def find_duplicate_rules(insights: list[Insight]) -> dict[str, list[str]]:
    rule_to_titles: dict[str, set[str]] = defaultdict(set)
    for insight in insights:
        for rule in insight.normalized_rules:
            rule_to_titles[rule].add(insight.title)

    duplicates: dict[str, list[str]] = {}
    for titles in rule_to_titles.values():
        if len(titles) < 2:
            continue
        for title in titles:
            duplicates.setdefault(title, [])
            duplicates[title].extend(other for other in titles if other != title)

    return {title: sorted(set(items)) for title, items in duplicates.items()}


def compute_review_score(findings: list[ReviewFinding]) -> float:
    score = 1.0
    for finding in findings:
        if finding.severity == "error":
            score -= 0.28
        elif finding.severity == "warning":
            score -= 0.08
        else:
            score -= 0.02
    return round(max(score, 0.0), 2)


def build_recommendations(findings: list[ReviewFinding], score: float, *, primary_reason: str | None = None) -> list[str]:
    recommendations: list[str] = []
    codes = {finding.code for finding in findings}

    if primary_reason:
        recommendations.append(f"当前主要风险：{reason_label(primary_reason)}。")
    if "insufficient_evidence" in codes:
        recommendations.append("先提升重复阈值或补充更多会话，再决定是否发布。")
    if "generic_rule" in codes:
        recommendations.append("把抽象规则改写成可执行约束，再进入人工审核。")
    if "duplicate_rules" in codes:
        recommendations.append("合并重复主题，避免草稿里的分类边界模糊。")
    if score >= 0.75 and not findings:
        recommendations.append("当前结果质量较高，可以直接进入草稿编辑和发布前复核。")
    elif score >= 0.75:
        recommendations.append("当前结果基本可用，但建议先处理 warning 再发布。")
    else:
        recommendations.append("当前结果不宜直接发布，建议先经过自动裁剪或人工复核。")
    return recommendations


def build_auto_actions(findings: list[ReviewFinding]) -> list[str]:
    actions: list[str] = []
    codes = {finding.code for finding in findings}
    if "insufficient_evidence" in codes:
        actions.append("prune_low_signal_insights")
    if "duplicate_rules" in codes:
        actions.append("deduplicate_rules")
    return actions


def summarize_reason_codes(findings: list[ReviewFinding]) -> tuple[dict[str, int], str | None]:
    counts: dict[str, int] = defaultdict(int)
    weighted: dict[str, int] = defaultdict(int)
    severity_weight = {"error": 3, "warning": 2, "info": 1}
    for finding in findings:
        counts[finding.code] += 1
        weighted[finding.code] += severity_weight.get(finding.severity, 1)
    if not weighted:
        return {}, None
    primary = sorted(
        weighted.items(),
        key=lambda item: (item[1], counts[item[0]], item[0]),
        reverse=True,
    )[0][0]
    return dict(counts), primary


def reason_label(code: str) -> str:
    return {
        "insufficient_evidence": "跨会话证据不足",
        "missing_rules": "可执行规则缺失",
        "low_confidence": "聚类置信度偏低",
        "generic_rule": "规则表述过于抽象",
        "duplicate_rules": "规则重复度过高",
    }.get(code, code)


def prune_low_signal_insights(
    insights: list[Insight],
    report: ReviewReport,
    *,
    min_confidence: float = 0.62,
    min_evidence: int = 2,
) -> tuple[list[Insight], list[str]]:
    rejected = set(report.rejected_titles)
    pruned: list[Insight] = []
    actions: list[str] = []

    for insight in insights:
        if insight.title in rejected:
            actions.append(f"drop:{insight.title}")
            continue
        if insight.confidence < min_confidence and insight.frequency < min_evidence:
            actions.append(f"drop:{insight.title}")
            continue
        pruned.append(remove_duplicate_rules(insight))

    return pruned, actions


def remove_duplicate_rules(insight: Insight) -> Insight:
    deduped: list[str] = []
    seen: set[str] = set()
    for rule in insight.normalized_rules:
        if rule in seen:
            continue
        seen.add(rule)
        deduped.append(rule)

    insight.normalized_rules = deduped
    return insight
