from __future__ import annotations

from .models import CandidateMessage, InsightCategory, ProjectAttribution, SessionRecord

ALLOWED_ROLES = {"user"}

EXCLUDED_KEYWORDS = (
    "作品集",
    "简历",
    "交接包",
    "导出接口",
    "数据库",
    "mysql",
    "部署",
    "后端",
    "pr",
    "ci",
    "commit",
)

DESIGN_CATEGORY_KEYWORDS: dict[InsightCategory, tuple[str, ...]] = {
    "principles": ("一致性", "规范", "规则", "原则", "层级", "信息架构"),
    "page-patterns": ("列表页", "详情页", "表单页", "页面结构", "信息层级", "工作台"),
    "interaction-patterns": ("交互", "反馈", "错误态", "loading", "empty", "retry", "录音", "权限"),
    "component-patterns": ("按钮", "组件", "卡片", "表单项", "吸底栏", "empty state", "tag"),
    "style-system": ("token", "颜色", "圆角", "间距", "样式", "主题", "语义层"),
    "content-rules": ("文案", "命名", "按钮文案", "错误提示", "口吻", "标签"),
}


def extract_design_candidates(
    session: SessionRecord,
    attribution: ProjectAttribution,
) -> list[CandidateMessage]:
    candidates: list[CandidateMessage] = []
    for message in session.messages:
        if message.role not in ALLOWED_ROLES:
            continue
        if is_excluded_message(message.text):
            continue
        category = classify_message(message.text)
        if category is None:
            continue
        candidates.append(
            CandidateMessage(
                session_id=session.session_id,
                source_path=session.source_path,
                date=session.date,
                role=message.role,
                text=message.text,
                project_id=attribution.project_id,
                category=category,
            )
        )
    return candidates


def classify_message(text: str) -> InsightCategory | None:
    normalized = text.lower()
    best_category: InsightCategory | None = None
    best_score = 0

    for category, keywords in DESIGN_CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword.lower() in normalized)
        if score > best_score:
            best_score = score
            best_category = category

    return best_category if best_score > 0 else None


def is_excluded_message(text: str) -> bool:
    normalized = text.lower()
    return any(keyword.lower() in normalized for keyword in EXCLUDED_KEYWORDS)
