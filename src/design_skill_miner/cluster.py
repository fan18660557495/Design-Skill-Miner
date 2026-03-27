from __future__ import annotations

import re
from collections import defaultdict

from .models import CandidateMessage, InsightCategory


TOPIC_PATTERNS: dict[InsightCategory, list[tuple[str, tuple[str, ...]]]] = {
    "principles": [
        ("一致性", ("一致性", "统一", "口径", "规范")),
        ("组件复用", ("复用", "组件结构", "组件体系", "组件整理")),
        ("设计系统", ("设计系统", "tokens", "token", "语义层")),
        ("信息层级", ("信息层级", "层级", "信息架构")),
    ],
    "page-patterns": [
        ("页面结构", ("页面结构", "页面布局", "界面结构")),
        ("信息层级", ("信息层级", "层级", "信息架构")),
        ("二级页面", ("二级页面", "消息列表页", "详情页")),
        ("工作台", ("工作台", "首页", "欢迎区")),
        ("表单页", ("表单页", "表单", "输入区")),
    ],
    "interaction-patterns": [
        ("语音交互", ("录音", "语音", "语音部分", "实时字幕", "回填")),
        ("状态反馈", ("错误态", "loading", "empty", "retry", "反馈", "处理中")),
        ("聚焦反馈", ("聚焦", "高亮效果", "描边", "聚焦描边")),
        ("发送流程", ("发送按钮", "发送", "发送流程")),
        ("权限", ("权限", "授权")),
    ],
    "component-patterns": [
        ("卡片", ("卡片", "欢迎卡片", "紫卡")),
        ("按钮", ("按钮", "发送按钮", "主按钮")),
        ("输入框", ("输入框", "输入区", "文本框")),
        ("图标", ("图标", "# 图标", "箭头")),
        ("导航", ("导航", "返回按钮", "顶部栏", "菜单")),
        ("组件体系", ("组件", "组件结构", "组件整理")),
        ("底部操作区", ("吸底栏", "底部栏", "操作栏")),
    ],
    "style-system": [
        ("颜色", ("颜色", "主题色", "渐变色")),
        ("圆角", ("圆角", "弧度", "胶囊", "凹槽")),
        ("间距对齐", ("间距", "对齐", "偏移", "留白")),
        ("字体排版", ("字体", "排版", "行间距")),
        ("尺寸比例", ("缩小", "尺寸", "高度", "宽度")),
        ("设计 token", ("token", "tokens", "语义层")),
    ],
    "content-rules": [
        ("文案", ("文案", "解释文案", "页面文案")),
        ("命名", ("命名", "称呼", "标题")),
        ("品牌表达", ("FanFan", "nova", "品牌名")),
    ],
}


def cluster_candidates(candidates: list[CandidateMessage]) -> dict[tuple[str, InsightCategory], list[CandidateMessage]]:
    grouped: dict[tuple[str, InsightCategory], list[CandidateMessage]] = defaultdict(list)
    for candidate in candidates:
        topic_key = infer_topic_key(candidate.text, candidate.category)
        if not topic_key:
            continue
        grouped[(topic_key, candidate.category)].append(candidate)
    return dict(grouped)


def infer_topic_key(text: str, category: InsightCategory) -> str | None:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    for topic, keywords in TOPIC_PATTERNS.get(category, []):
        if any(keyword.lower() in normalized for keyword in keywords):
            return topic

    # Drop raw sentence fragments. For this product, it is better to skip
    # low-confidence clusters than to promote user prompts into fake rules.
    if looks_like_instruction_sentence(normalized):
        return None
    return None


def looks_like_instruction_sentence(text: str) -> bool:
    noise_markers = (
        "可以",
        "执行吧",
        "帮我",
        "希望你",
        "为什么",
        "如何",
        "这个",
        "现在",
        "请",
    )
    return len(text) > 12 and any(marker in text for marker in noise_markers)
