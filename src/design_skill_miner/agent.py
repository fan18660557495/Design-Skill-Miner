from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import tempfile
from typing import Callable

from .attribution import project_id_from_prefix
from .draft_skill import write_skill_draft
from .llm import LLMClient, LLMConfig, LLMError
from .memory import AgentMemoryStore, ProjectMemoryProfile, resolve_memory_db_path
from .models import Insight
from .pipeline import generate_insights
from .report import write_reports
from .review import ReviewReport, prune_low_signal_insights, review_insights
from .skill_executor import apply_skill_strategy
from .skill_router import SkillSelection, choose_skill_for_insights
from .tool_policy import decide_next_action


@dataclass(frozen=True)
class AgentGoal:
    title: str
    success_criteria: list[str]
    max_cycles: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AgentSettings:
    review_min_score: float = 0.6
    review_min_confidence: float = 0.62
    review_min_evidence: int = 2
    auto_prune: bool = True
    max_cycles: int = 3
    memory_db_path: str | None = None


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
    goal: AgentGoal
    cycles_used: int
    final_decision: str
    memory_profile: dict | None = None
    plan: list[AgentStep] = field(default_factory=list)
    selected_skill: dict | None = None
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
            "goal": self.goal.to_dict(),
            "cycles_used": self.cycles_used,
            "final_decision": self.final_decision,
            "memory_profile": self.memory_profile,
            "plan": [step.to_dict() for step in self.plan],
            "selected_skill": self.selected_skill,
            "llm_enabled": self.llm_enabled,
            "llm_status": self.llm_status,
            "llm_error": self.llm_error,
            "files": self.files,
        }


@dataclass
class _CycleSnapshot:
    insights: list[Insight]
    stats: dict[str, int]
    review: ReviewReport
    skill_selection: SkillSelection
    min_frequency: int
    min_score: float
    min_confidence: float
    min_evidence: int


def run_agent_mine(
    sessions_root: Path,
    *,
    cwd_prefix: str | None = None,
    min_frequency: int = 2,
    out_dir: Path | None = None,
    skill_name: str = "design-skill-draft",
    description: str | None = None,
    goal: str | None = None,
    skill_id: str | None = None,
    agent_settings: AgentSettings | None = None,
    llm_config: LLMConfig | None = None,
    progress_callback: Callable[[dict], None] | None = None,
) -> AgentRunResult:
    settings = agent_settings or AgentSettings()
    llm = LLMClient(llm_config or LLMConfig())
    plan: list[AgentStep] = []
    current_min_frequency = max(min_frequency, 1)
    current_skill_override = skill_id
    final_decision = "finish"
    cycles_used = 0

    resolved_goal = AgentGoal(
        title=goal or _default_goal(cwd_prefix),
        success_criteria=[
            f"审校分不低于 {settings.review_min_score:.2f}",
            "输出至少 1 个可编辑草稿文件",
            "低质量候选在进入草稿前被识别并处理",
        ],
        max_cycles=max(settings.max_cycles, 1),
    )
    plan.append(AgentStep("goal_init", "completed", resolved_goal.title))
    memory_profile_payload: dict | None = None
    _emit_progress(
        progress_callback,
        plan=plan,
        goal=resolved_goal,
        cycles_used=cycles_used,
        final_decision=final_decision,
        memory_profile=memory_profile_payload,
    )

    project_id = project_id_from_prefix(cwd_prefix) if cwd_prefix else "global"
    memory_store: AgentMemoryStore | None = None
    memory_profile: ProjectMemoryProfile | None = None
    try:
        memory_store = AgentMemoryStore(resolve_memory_db_path(settings.memory_db_path))
        memory_profile = memory_store.load_project_profile(project_id)
        memory_profile_payload = memory_profile.to_dict()
        plan.append(
            AgentStep(
                "load_memory",
                "completed",
                (
                    f"project={project_id}, runs={memory_profile.total_runs}, "
                    f"preferred_skill={memory_profile.preferred_skill_id or 'none'}"
                ),
            )
        )
    except Exception as exc:  # noqa: BLE001
        plan.append(AgentStep("load_memory", "completed", f"memory unavailable: {exc}"))
    _emit_progress(
        progress_callback,
        plan=plan,
        goal=resolved_goal,
        cycles_used=cycles_used,
        final_decision=final_decision,
        memory_profile=memory_profile_payload,
    )

    if memory_profile:
        if memory_profile.suggested_min_frequency and current_min_frequency < memory_profile.suggested_min_frequency:
            current_min_frequency = memory_profile.suggested_min_frequency
            plan.append(
                AgentStep(
                    "apply_memory_hint",
                    "completed",
                    f"min_frequency adjusted to {current_min_frequency}",
                )
            )
        if not skill_id and memory_profile.preferred_skill_id:
            current_skill_override = memory_profile.preferred_skill_id
            plan.append(
                AgentStep(
                    "apply_memory_hint",
                    "completed",
                    f"skill switched to {current_skill_override} from memory",
                )
            )
        if memory_profile.draft_feedback_tags:
            top_tags = sorted(
                memory_profile.draft_feedback_tags.items(),
                key=lambda item: (-item[1], item[0]),
            )[:3]
            plan.append(
                AgentStep(
                    "apply_memory_hint",
                    "completed",
                    "draft feedback hints: " + ", ".join(f"{name}({count})" for name, count in top_tags),
                )
            )
    _emit_progress(
        progress_callback,
        plan=plan,
        goal=resolved_goal,
        cycles_used=cycles_used,
        final_decision=final_decision,
        memory_profile=memory_profile_payload,
    )

    blocked_titles = set(memory_profile.blocked_titles) if memory_profile else set()
    best_snapshot: _CycleSnapshot | None = None
    last_snapshot: _CycleSnapshot | None = None

    for cycle_index in range(resolved_goal.max_cycles):
        cycles_used = cycle_index + 1
        plan.append(
            AgentStep(
                "cycle_start",
                "completed",
                f"cycle={cycles_used}/{resolved_goal.max_cycles}, min_frequency={current_min_frequency}",
            )
        )
        _emit_progress(
            progress_callback,
            plan=plan,
            goal=resolved_goal,
            cycles_used=cycles_used,
            final_decision=final_decision,
            memory_profile=memory_profile_payload,
        )

        plan.append(AgentStep("collect_insights", "in_progress", f"min_frequency={current_min_frequency}"))
        _emit_progress(
            progress_callback,
            plan=plan,
            goal=resolved_goal,
            cycles_used=cycles_used,
            final_decision=final_decision,
            memory_profile=memory_profile_payload,
        )
        insights, stats = generate_insights(
            sessions_root,
            cwd_prefix=cwd_prefix,
            min_frequency=current_min_frequency,
        )
        plan[-1].status = "completed"
        plan[-1].details = f"generated={len(insights)}"
        _emit_progress(
            progress_callback,
            plan=plan,
            goal=resolved_goal,
            cycles_used=cycles_used,
            final_decision=final_decision,
            stats=stats,
            memory_profile=memory_profile_payload,
        )

        if blocked_titles and insights:
            before = len(insights)
            insights = [item for item in insights if item.title not in blocked_titles]
            if len(insights) != before:
                stats = dict(stats)
                stats["insights_written"] = len(insights)
                plan.append(
                    AgentStep(
                        "memory_filter",
                        "completed",
                        f"dropped={before - len(insights)} previously rejected titles",
                    )
                )
                _emit_progress(
                    progress_callback,
                    plan=plan,
                    goal=resolved_goal,
                    cycles_used=cycles_used,
                    final_decision=final_decision,
                    stats=stats,
                    memory_profile=memory_profile_payload,
                )

        plan.append(AgentStep("choose_skill", "in_progress", "select the most suitable skill strategy"))
        _emit_progress(
            progress_callback,
            plan=plan,
            goal=resolved_goal,
            cycles_used=cycles_used,
            final_decision=final_decision,
            stats=stats,
            memory_profile=memory_profile_payload,
        )
        skill_selection = choose_skill_for_insights(insights, explicit_skill_id=current_skill_override)
        plan[-1].status = "completed"
        plan[-1].details = f"{skill_selection.skill.skill_id} - {skill_selection.reason}"
        selected_skill_payload = skill_selection.to_dict()
        _emit_progress(
            progress_callback,
            plan=plan,
            goal=resolved_goal,
            cycles_used=cycles_used,
            final_decision=final_decision,
            stats=stats,
            selected_skill=selected_skill_payload,
            memory_profile=memory_profile_payload,
        )

        effective_min_score = skill_selection.skill.review_min_score or settings.review_min_score
        effective_min_confidence = skill_selection.skill.review_min_confidence or settings.review_min_confidence
        effective_min_evidence = skill_selection.skill.review_min_evidence or settings.review_min_evidence

        if not insights:
            review = ReviewReport(
                score=0.0,
                findings=[],
                approved_titles=[],
                rejected_titles=[],
                recommendations=["当前没有候选规则，建议扩大样本或提高重复信号。"],
                auto_actions=["collect_more_evidence"],
                reason_counts={"insufficient_evidence": 1},
                primary_reason="insufficient_evidence",
            )
        else:
            plan.append(AgentStep("review_insights", "in_progress", "run deterministic quality checks"))
            _emit_progress(
                progress_callback,
                plan=plan,
                goal=resolved_goal,
                cycles_used=cycles_used,
                final_decision=final_decision,
                stats=stats,
                selected_skill=selected_skill_payload,
                memory_profile=memory_profile_payload,
            )
            review = review_insights(
                insights,
                min_confidence=effective_min_confidence,
                min_evidence=effective_min_evidence,
            )
            plan[-1].status = "completed"
            plan[-1].details = f"score={review.score}, primary_reason={review.primary_reason or 'none'}"
            _emit_progress(
                progress_callback,
                plan=plan,
                goal=resolved_goal,
                cycles_used=cycles_used,
                final_decision=final_decision,
                stats=stats,
                review=review.to_dict(),
                selected_skill=selected_skill_payload,
                memory_profile=memory_profile_payload,
            )

            if settings.auto_prune:
                plan.append(AgentStep("auto_prune", "in_progress", "drop low-signal insights and dedupe rules"))
                _emit_progress(
                    progress_callback,
                    plan=plan,
                    goal=resolved_goal,
                    cycles_used=cycles_used,
                    final_decision=final_decision,
                    stats=stats,
                    review=review.to_dict(),
                    selected_skill=selected_skill_payload,
                    memory_profile=memory_profile_payload,
                )
                original_insights = list(insights)
                pruned_insights, actions = prune_low_signal_insights(
                    insights,
                    review,
                    min_confidence=effective_min_confidence,
                    min_evidence=effective_min_evidence,
                )
                if pruned_insights:
                    insights = pruned_insights
                else:
                    insights = original_insights
                    actions.append("keep_original:no_survivors_after_prune")
                review = review_insights(
                    insights,
                    min_confidence=effective_min_confidence,
                    min_evidence=effective_min_evidence,
                )
                plan[-1].status = "completed"
                plan[-1].details = ", ".join(actions) if actions else "no changes"
                _emit_progress(
                    progress_callback,
                    plan=plan,
                    goal=resolved_goal,
                    cycles_used=cycles_used,
                    final_decision=final_decision,
                    stats=stats,
                    review=review.to_dict(),
                    selected_skill=selected_skill_payload,
                    memory_profile=memory_profile_payload,
                )

        snapshot = _CycleSnapshot(
            insights=_clone_insights(insights),
            stats=dict(stats),
            review=review,
            skill_selection=skill_selection,
            min_frequency=current_min_frequency,
            min_score=effective_min_score,
            min_confidence=effective_min_confidence,
            min_evidence=effective_min_evidence,
        )
        last_snapshot = snapshot
        if best_snapshot is None or snapshot.review.score > best_snapshot.review.score:
            best_snapshot = snapshot

        decision = decide_next_action(
            cycle_index=cycle_index,
            max_cycles=resolved_goal.max_cycles,
            review=review,
            has_insights=bool(insights),
            min_score=effective_min_score,
            current_min_frequency=current_min_frequency,
            current_skill_id=skill_selection.skill.skill_id,
            category_scores=skill_selection.category_scores,
            explicit_skill_id=skill_id,
        )
        final_decision = decision.action
        plan.append(AgentStep("tool_policy", "completed", f"{decision.action}: {decision.reason}"))
        _emit_progress(
            progress_callback,
            plan=plan,
            goal=resolved_goal,
            cycles_used=cycles_used,
            final_decision=final_decision,
            stats=stats,
            review=review.to_dict(),
            selected_skill=selected_skill_payload,
            memory_profile=memory_profile_payload,
        )

        if decision.action == "collect_more_evidence":
            current_min_frequency = decision.next_min_frequency or (current_min_frequency + 1)
            continue
        if decision.action == "switch_skill":
            current_skill_override = decision.next_skill_id or current_skill_override
            continue
        break

    final_snapshot = last_snapshot or best_snapshot
    if final_snapshot is None:
        final_snapshot = _CycleSnapshot(
            insights=[],
            stats={"sessions_scanned": 0, "candidate_messages": 0, "insights_written": 0},
            review=ReviewReport(
                score=0.0,
                findings=[],
                approved_titles=[],
                rejected_titles=[],
                recommendations=["当前没有候选规则。"],
                auto_actions=[],
                reason_counts={"insufficient_evidence": 1},
                primary_reason="insufficient_evidence",
            ),
            skill_selection=choose_skill_for_insights([], explicit_skill_id=current_skill_override),
            min_frequency=current_min_frequency,
            min_score=settings.review_min_score,
            min_confidence=settings.review_min_confidence,
            min_evidence=settings.review_min_evidence,
        )

    if not final_snapshot.insights and best_snapshot and best_snapshot.insights:
        final_snapshot = best_snapshot
        plan.append(
            AgentStep(
                "rollback_best_cycle",
                "completed",
                "latest cycle has no surviving insights, fallback to best previous cycle.",
            )
        )
        _emit_progress(
            progress_callback,
            plan=plan,
            goal=resolved_goal,
            cycles_used=cycles_used,
            final_decision=final_decision,
            stats=final_snapshot.stats,
            review=final_snapshot.review.to_dict(),
            selected_skill=final_snapshot.skill_selection.to_dict(),
            memory_profile=memory_profile_payload,
        )

    plan.append(AgentStep("apply_skill_strategy", "in_progress", "reorder insights and shape draft focus"))
    _emit_progress(
        progress_callback,
        plan=plan,
        goal=resolved_goal,
        cycles_used=cycles_used,
        final_decision=final_decision,
        stats=final_snapshot.stats,
        review=final_snapshot.review.to_dict(),
        selected_skill=final_snapshot.skill_selection.to_dict(),
        memory_profile=memory_profile_payload,
    )
    skill_execution = apply_skill_strategy(
        final_snapshot.insights,
        final_snapshot.skill_selection,
        skill_name=skill_name,
        description=description,
    )
    insights = skill_execution.insights
    description = skill_execution.generated_description
    description = _append_feedback_hints_to_description(description, memory_profile)
    review = review_insights(
        insights,
        min_confidence=final_snapshot.min_confidence,
        min_evidence=final_snapshot.min_evidence,
    ) if insights else final_snapshot.review
    plan[-1].status = "completed"
    plan[-1].details = f"focus={','.join(skill_execution.available_categories) or 'general'}"
    _emit_progress(
        progress_callback,
        plan=plan,
        goal=resolved_goal,
        cycles_used=cycles_used,
        final_decision=final_decision,
        stats=final_snapshot.stats,
        review=review.to_dict(),
        selected_skill=final_snapshot.skill_selection.to_dict(),
        memory_profile=memory_profile_payload,
    )

    llm_enabled = bool(llm_config and llm_config.enabled)
    llm_status = "disabled"
    llm_error: str | None = None
    if llm_config and llm_config.is_ready() and insights:
        plan.append(AgentStep("llm_enhance", "in_progress", f"model={llm_config.model}"))
        _emit_progress(
            progress_callback,
            plan=plan,
            goal=resolved_goal,
            cycles_used=cycles_used,
            final_decision=final_decision,
            stats=final_snapshot.stats,
            review=review.to_dict(),
            selected_skill=final_snapshot.skill_selection.to_dict(),
            memory_profile=memory_profile_payload,
        )
        try:
            insights, partial_failures = llm.enhance_insights(insights)
            review = review_insights(
                insights,
                min_confidence=final_snapshot.min_confidence,
                min_evidence=final_snapshot.min_evidence,
            )
            llm_status = "completed_with_fallbacks" if partial_failures else "completed"
            llm_error = (
                f"{partial_failures} insight requests timed out or failed; kept deterministic version."
                if partial_failures
                else None
            )
            plan[-1].status = "completed"
            plan[-1].details = f"enhanced={len(insights)}, partial_failures={partial_failures}"
        except LLMError as exc:
            llm_status = "failed"
            llm_error = str(exc)
            plan[-1].status = "completed"
            plan[-1].details = "fallback to deterministic insights"
        _emit_progress(
            progress_callback,
            plan=plan,
            goal=resolved_goal,
            cycles_used=cycles_used,
            final_decision=final_decision,
            stats=final_snapshot.stats,
            review=review.to_dict(),
            selected_skill=final_snapshot.skill_selection.to_dict(),
            memory_profile=memory_profile_payload,
        )
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
        applied_skill=final_snapshot.skill_selection.skill,
        ordered_categories=skill_execution.available_categories,
    )

    if memory_store:
        try:
            memory_store.record_run(
                project_id=project_id,
                goal=resolved_goal.title,
                skill_id=final_snapshot.skill_selection.skill.skill_id,
                review_score=review.score,
                min_frequency=final_snapshot.min_frequency,
                reason_codes=list(review.reason_counts.keys()),
                approved_titles=review.approved_titles,
                rejected_titles=review.rejected_titles,
            )
            memory_profile = memory_store.load_project_profile(project_id)
            memory_profile_payload = memory_profile.to_dict()
            plan.append(
                AgentStep(
                    "write_memory",
                    "completed",
                    f"stored run history, total_runs={memory_profile.total_runs}",
                )
            )
        except Exception as exc:  # noqa: BLE001
            plan.append(AgentStep("write_memory", "completed", f"memory write skipped: {exc}"))
        _emit_progress(
            progress_callback,
            plan=plan,
            goal=resolved_goal,
            cycles_used=cycles_used,
            final_decision=final_decision,
            stats=final_snapshot.stats,
            review=review.to_dict(),
            selected_skill=final_snapshot.skill_selection.to_dict(),
            memory_profile=memory_profile_payload,
        )

    result = AgentRunResult(
        draft_dir=draft_dir,
        report_dir=report_dir,
        stats=final_snapshot.stats,
        review=review,
        goal=resolved_goal,
        cycles_used=cycles_used,
        final_decision=final_decision,
        memory_profile=memory_profile_payload,
        plan=plan,
        selected_skill=final_snapshot.skill_selection.to_dict(),
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


def _clone_insights(insights: list[Insight]) -> list[Insight]:
    return [Insight.from_dict(item.to_dict()) for item in insights]


def _default_goal(cwd_prefix: str | None) -> str:
    if not cwd_prefix:
        return "从历史会话中沉淀可复用的设计规则草稿。"
    project = Path(cwd_prefix).name or cwd_prefix
    return f"为项目 {project} 沉淀可复用且可发布前复核的设计规则草稿。"


def _emit_progress(
    callback: Callable[[dict], None] | None,
    *,
    plan: list[AgentStep],
    goal: AgentGoal,
    cycles_used: int,
    final_decision: str,
    stats: dict[str, int] | None = None,
    review: dict | None = None,
    selected_skill: dict | None = None,
    memory_profile: dict | None = None,
) -> None:
    if callback is None:
        return
    callback(
        {
            "goal": goal.to_dict(),
            "cycles_used": cycles_used,
            "final_decision": final_decision,
            "stats": stats,
            "review": review,
            "selected_skill": selected_skill,
            "memory_profile": memory_profile,
            "plan": [step.to_dict() for step in plan],
        }
    )


def _append_feedback_hints_to_description(description: str | None, memory_profile: ProjectMemoryProfile | None) -> str | None:
    if not description or not memory_profile or not memory_profile.draft_feedback_tags:
        return description
    ranked = sorted(memory_profile.draft_feedback_tags.items(), key=lambda item: (-item[1], item[0]))[:3]
    hints = [_feedback_tag_label(name) for name, _ in ranked if _feedback_tag_label(name)]
    if not hints:
        return description
    suffix = "项目历史编辑偏好：" + "；".join(hints) + "。"
    if suffix in description:
        return description
    return f"{description} {suffix}"


def _feedback_tag_label(tag: str) -> str:
    labels = {
        "prefer_examples": "增加可复用示例和典型场景",
        "prefer_actionable_rules": "规则尽量写成可执行约束",
        "prefer_scope_boundaries": "明确适用范围和例外边界",
        "prefer_consistency": "强调跨页面风格与口径一致",
        "prefer_brevity": "减少冗余表述，保持精简",
        "general_edit_preference": "保留人工编辑后的表达风格",
    }
    return labels.get(tag, "")
