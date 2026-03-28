from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import tempfile

from .draft_skill import write_skill_draft
from .llm import LLMClient, LLMConfig, LLMError
from .pipeline import generate_insights
from .report import write_reports
from .review import ReviewReport, prune_low_signal_insights, review_insights


@dataclass
class AgentSettings:
    review_min_score: float = 0.6
    review_min_confidence: float = 0.62
    review_min_evidence: int = 2
    auto_prune: bool = True


@dataclass
class AgentStep:
    name: str
    status: str
    details: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AgentRunResult:
    draft_dir: Path
    report_dir: Path
    stats: dict[str, int]
    review: ReviewReport
    plan: list[AgentStep] = field(default_factory=list)
    llm_enabled: bool = False
    llm_status: str = "disabled"
    llm_error: str | None = None
    files: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "draft_dir": str(self.draft_dir),
            "report_dir": str(self.report_dir),
            "stats": self.stats,
            "review": self.review.to_dict(),
            "plan": [step.to_dict() for step in self.plan],
            "llm_enabled": self.llm_enabled,
            "llm_status": self.llm_status,
            "llm_error": self.llm_error,
            "files": self.files,
        }


def run_agent_mine(
    sessions_root: Path,
    *,
    cwd_prefix: str | None = None,
    min_frequency: int = 2,
    out_dir: Path | None = None,
    skill_name: str = "design-skill-draft",
    description: str | None = None,
    agent_settings: AgentSettings | None = None,
    llm_config: LLMConfig | None = None,
) -> AgentRunResult:
    settings = agent_settings or AgentSettings()
    llm = LLMClient(llm_config or LLMConfig())
    plan: list[AgentStep] = []
    effective_min_frequency = min_frequency
    baseline_insights = []
    baseline_stats: dict[str, int] = {}
    baseline_review: ReviewReport | None = None

    plan.append(AgentStep("collect_insights", "in_progress", f"min_frequency={effective_min_frequency}"))
    insights, stats = generate_insights(
        sessions_root,
        cwd_prefix=cwd_prefix,
        min_frequency=effective_min_frequency,
    )
    baseline_insights = list(insights)
    baseline_stats = dict(stats)
    plan[-1].status = "completed"
    plan[-1].details = f"generated={len(insights)}"

    plan.append(AgentStep("review_insights", "in_progress", "run deterministic quality checks"))
    review = review_insights(
        insights,
        min_confidence=settings.review_min_confidence,
        min_evidence=settings.review_min_evidence,
    )
    baseline_review = review
    plan[-1].status = "completed"
    plan[-1].details = f"score={review.score}"

    if review.score < settings.review_min_score and effective_min_frequency < settings.review_min_evidence:
        effective_min_frequency = settings.review_min_evidence
        plan.append(
            AgentStep(
                "replan_threshold",
                "completed",
                f"review score below threshold, rerun with min_frequency={effective_min_frequency}",
            )
        )
        plan.append(AgentStep("collect_insights", "in_progress", f"min_frequency={effective_min_frequency}"))
        insights, stats = generate_insights(
            sessions_root,
            cwd_prefix=cwd_prefix,
            min_frequency=effective_min_frequency,
        )
        plan[-1].status = "completed"
        plan[-1].details = f"generated={len(insights)}"

        plan.append(AgentStep("review_insights", "in_progress", "re-run quality checks after replanning"))
        review = review_insights(
            insights,
            min_confidence=settings.review_min_confidence,
            min_evidence=settings.review_min_evidence,
        )
        plan[-1].status = "completed"
        plan[-1].details = f"score={review.score}"

        if not insights and baseline_insights:
            insights = baseline_insights
            stats = baseline_stats
            review = baseline_review
            plan.append(
                AgentStep(
                    "rollback_replan",
                    "completed",
                    "stricter threshold removed all insights, reverted to baseline result",
                )
            )

    if settings.auto_prune and insights:
        plan.append(AgentStep("auto_prune", "in_progress", "drop low-signal insights and dedupe rules"))
        original_insights = list(insights)
        pruned_insights, actions = prune_low_signal_insights(
            insights,
            review,
            min_confidence=settings.review_min_confidence,
            min_evidence=settings.review_min_evidence,
        )
        if pruned_insights:
            insights = pruned_insights
            review = review_insights(
                insights,
                min_confidence=settings.review_min_confidence,
                min_evidence=settings.review_min_evidence,
            )
        else:
            insights = original_insights
            actions.append("keep_original:no_survivors_after_prune")
        review = review_insights(
            insights,
            min_confidence=settings.review_min_confidence,
            min_evidence=settings.review_min_evidence,
        )
        plan[-1].status = "completed"
        plan[-1].details = ", ".join(actions) if actions else "no changes"

    llm_enabled = bool(llm_config and llm_config.enabled)
    llm_status = "disabled"
    llm_error: str | None = None
    if llm_config and llm_config.is_ready() and insights:
        plan.append(AgentStep("llm_enhance", "in_progress", f"model={llm_config.model}"))
        try:
            insights, partial_failures = llm.enhance_insights(insights)
            review = review_insights(
                insights,
                min_confidence=settings.review_min_confidence,
                min_evidence=settings.review_min_evidence,
            )
            llm_status = "completed_with_fallbacks" if partial_failures else "completed"
            llm_error = f"{partial_failures} insight requests timed out or failed; kept deterministic version." if partial_failures else None
            plan[-1].status = "completed"
            plan[-1].details = f"enhanced={len(insights)}, partial_failures={partial_failures}"
        except LLMError as exc:
            llm_status = "failed"
            llm_error = str(exc)
            plan[-1].status = "completed"
            plan[-1].details = "fallback to deterministic insights"
    elif llm_enabled:
        llm_status = "not_ready"

    base_out = out_dir or Path(tempfile.mkdtemp(prefix="design-skill-miner-agent-"))
    report_dir = base_out / "reports"
    draft_dir = base_out / "draft"
    report_dir.mkdir(parents=True, exist_ok=True)
    draft_dir.mkdir(parents=True, exist_ok=True)

    json_path, md_path = write_reports(insights, report_dir)
    review_path = report_dir / "review.json"
    review_path.write_text(json.dumps(review.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    outputs = write_skill_draft(
        insights,
        draft_dir,
        skill_name=skill_name,
        description=description,
    )

    result = AgentRunResult(
        draft_dir=draft_dir,
        report_dir=report_dir,
        stats=stats,
        review=review,
        plan=plan,
        llm_enabled=llm_enabled,
        llm_status=llm_status,
        llm_error=llm_error,
        files={
            "insights_json": str(json_path),
            "insights_md": str(md_path),
            "review_json": str(review_path),
            "skill_path": str(outputs["skill"]),
            "manifest_path": str(outputs["manifest"]),
        },
    )

    run_path = base_out / "agent-run.json"
    run_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    result.files["run_json"] = str(run_path)
    return result
