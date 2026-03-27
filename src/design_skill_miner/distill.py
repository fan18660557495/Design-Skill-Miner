from __future__ import annotations

from .models import CandidateMessage, Evidence, Insight


def distill_cluster(topic_key: str, category: str, items: list[CandidateMessage]) -> Insight:
    deduped_items = dedupe_candidate_messages(items)
    frequency = len({item.session_id for item in deduped_items})
    evidence = build_evidence(deduped_items)
    scope = "project_specific_skill"
    decision = "candidate_for_skill" if frequency >= 2 else "not_worthy_yet"
    stability = "stable" if frequency >= 3 else "emerging"
    confidence = min(0.55 + frequency * 0.08, 0.92)

    return Insight(
        title=build_title(topic_key, category),
        summary=f"围绕“{topic_key}”的设计讨论重复出现 {frequency} 次，适合人工审核后决定是否沉淀。",
        category=category,  # type: ignore[arg-type]
        granularity=default_granularity(category),
        frequency=frequency,
        decision=decision,  # type: ignore[arg-type]
        scope=scope,  # type: ignore[arg-type]
        stability=stability,  # type: ignore[arg-type]
        confidence=confidence,
        why_it_repeats=[f"同类设计判断围绕“{topic_key}”被反复讨论。"],
        proposed_rules=build_rules(topic_key, category, frequency),
        normalized_rules=synthesize_rules(topic_key, category, deduped_items),
        evidence=evidence,
    )


def build_title(topic_key: str, category: str) -> str:
    label = {
        "principles": "设计原则",
        "page-patterns": "页面模式",
        "interaction-patterns": "交互模式",
        "component-patterns": "组件模式",
        "style-system": "样式系统",
        "content-rules": "表达规范",
    }.get(category, "设计主题")
    return f"{label}：{topic_key}"


def default_granularity(category: str) -> str:
    mapping = {
        "principles": "principle",
        "page-patterns": "page",
        "interaction-patterns": "interaction",
        "component-patterns": "component",
        "style-system": "token",
        "content-rules": "content",
    }
    return mapping.get(category, "pattern")


def build_rules(topic_key: str, category: str, frequency: int) -> list[str]:
    base = [f"围绕“{topic_key}”建立统一默认做法。"]
    if category == "component-patterns":
        base.append("同类组件优先抽成稳定模式，再在页面层做少量差异化。")
    elif category == "interaction-patterns":
        base.append("先统一状态、反馈和收口规则，再优化局部表现。")
    elif category == "style-system":
        base.append("优先沉淀成语义 token，而不是直接复用原始色值。")
    elif category == "content-rules":
        base.append("把重复修正过的表达收敛成统一文案口径。")
    elif category == "page-patterns":
        base.append("把反复出现的页面结构收敛成可复用页面模式。")
    elif category == "principles":
        base.append("将跨页面稳定成立的判断提炼成总原则。")

    if frequency >= 4:
        base.append("重复次数已经较高，优先考虑进入 skill 候选稿。")
    return base


def summarize_text(text: str, limit: int = 64) -> str:
    compact = " ".join(text.split())
    return compact[:limit] + ("..." if len(compact) > limit else "")


def synthesize_rules(topic_key: str, category: str, items: list[CandidateMessage]) -> list[str]:
    combined = " ".join(item.text for item in items)
    rules: list[str] = []

    if category == "component-patterns":
        if topic_key == "按钮":
            rules.extend(
                [
                    "统一主按钮、次按钮和图标按钮的层级，不在同一页面并列多个视觉同级主操作。",
                    "按钮与导航、底部栏和相邻容器之间保持稳定间距，避免重叠或错位。",
                    "按钮的高亮、禁用、聚焦和点击反馈使用同一套状态规则。",
                ]
            )
        elif topic_key == "卡片":
            rules.extend(
                [
                    "统一卡片的圆角、阴影、边框和留白，不让同页卡片出现多套容器语言。",
                    "有层叠或重叠关系的卡片要先定义主次层级，再调整视觉细节。",
                    "卡片内部标题、内容、装饰元素和操作区的对齐关系保持稳定。",
                ]
            )
        elif topic_key == "输入框":
            rules.extend(
                [
                    "输入框的边框、聚焦描边、占位态和已输入态保持统一，不在不同页面各自变化。",
                    "输入框与发送按钮、语音按钮和辅助说明之间保持稳定关系，避免局部挤压导致错位。",
                ]
            )
        elif topic_key == "导航":
            rules.extend(
                [
                    "顶部导航里的返回、菜单和标题关系保持固定，不让二级页面每次重新定义头部结构。",
                    "导航按钮的尺寸、位置和图标风格统一，不在页面之间混用多套头部语言。",
                ]
            )
        elif topic_key == "图标":
            rules.extend(
                [
                    "图标容器的圆角、底板比例和箭头样式保持统一，不在不同模块各自调整一套细节。",
                    "图标尺寸变化只改尺寸体系，不顺带改圆角和容器结构。",
                ]
            )
        elif topic_key == "底部操作区":
            rules.extend(
                [
                    "底部操作区作为稳定组件处理，按钮、间距和安全区留白统一，不跟页面内容临时耦合。",
                    "底部操作区与主内容之间保留稳定过渡空间，避免视觉上像内容挤进固定栏。",
                ]
            )
        else:
            rules.extend(
                [
                    f"围绕“{topic_key}”沉淀统一组件外观、状态和间距规则。",
                    "同类组件优先收敛成少量稳定变体，不在页面层各自实现一套样式。",
                ]
            )

    elif category == "interaction-patterns":
        if topic_key == "语音交互":
            rules.extend(
                [
                    "统一语音入口的开始、结束、取消和处理中反馈，不同页面保持同一套交互节奏。",
                    "波形、提示文案、遮罩和实时文本区域的视觉表现保持一致，不在主页和表单页各自变化。",
                    "语音入口位置和结果回填区域要明确，避免用户不知道输入最终落在哪里。",
                ]
            )
        elif topic_key == "按钮":
            rules.extend(
                [
                    "主操作按钮的点击反馈、loading 和禁用状态在各页面保持一致。",
                    "按钮位置调整优先保证可达性和视觉层级，再处理局部动画或装饰。",
                ]
            )
        elif topic_key == "聚焦反馈":
            rules.extend(
                [
                    "聚焦态反馈优先通过一套稳定的描边、阴影或按钮高亮规则表达，不在单页临时拼效果。",
                    "聚焦反馈只强化当前操作上下文，不额外引入会干扰阅读的新视觉重心。",
                ]
            )
        elif topic_key == "状态反馈":
            rules.extend(
                [
                    "loading、错误、空态和处理中提示按同一套反馈体系组织，不在每个模块重新发明状态语言。",
                    "状态提示优先说明当前任务是否还能继续，而不是只显示抽象结果。",
                ]
            )
        elif topic_key == "文案":
            rules.extend(
                [
                    "状态反馈与解释文案分离，界面中只保留当前任务需要的短反馈。",
                    "交互动画和状态说明不要把技术实现细节直接写进界面文案。",
                ]
            )
        else:
            rules.extend(
                [
                    f"围绕“{topic_key}”统一状态变化、反馈方式和收口规则。",
                    "跨页面复用的交互优先形成固定流程，而不是按页面单独解释。",
                ]
            )

    elif category == "page-patterns":
        if topic_key == "表单页":
            rules.extend(
                [
                    "表单页里的输入框、辅助说明和交互浮层避免相互遮挡，优先保证当前任务可读可点。",
                    "表单页中的语音、按钮和输入区布局保持一致，不因页面内容上下浮动而失去统一性。",
                    "页面内的辅助说明和操作入口优先跟随字段任务，而不是漂浮成独立装饰块。",
                ]
            )
        elif topic_key == "页面结构":
            rules.extend(
                [
                    "页面先定义主区块顺序和层级，再细化装饰元素，不让视觉细节先行导致结构发散。",
                    "同类型页面复用统一骨架，避免每次改版都重写页面组织方式。",
                ]
            )
        elif topic_key == "信息层级":
            rules.extend(
                [
                    "信息层级先区分主任务、辅助说明和装饰内容，再分配视觉权重。",
                    "同页里同等级信息用同一层级表达，不靠局部补丁修正阅读顺序。",
                ]
            )
        else:
            rules.extend(
                [
                    f"围绕“{topic_key}”沉淀页面结构、信息层级和状态布局规则。",
                ]
            )

    elif category == "style-system":
        if topic_key == "颜色":
            rules.extend(
                [
                    "颜色先映射成语义层，再落到组件层，不直接在页面里反复手写原始色值。",
                    "同类状态的颜色深浅和对比关系保持稳定，避免同一页面出现多套颜色判断。",
                    "颜色调整优先检查文本可读性、层级区分和组件状态，而不是只看单点视觉。",
                ]
            )
        elif topic_key == "圆角":
            rules.extend(
                [
                    "圆角遵循统一半径体系，不因局部缩放或布局变窄就临时改变曲率逻辑。",
                    "带特殊切角、凹槽或胶囊结构的元素，先定义规则化半径关系，再做单点微调。",
                ]
            )
        elif topic_key == "间距对齐":
            rules.extend(
                [
                    "间距和对齐优先遵循统一 spacing 体系，不在每个模块靠目测补像素。",
                    "出现偏移时先回到容器、栅格和内边距关系，而不是只改单个元素位置。",
                ]
            )
        elif topic_key == "字体排版":
            rules.extend(
                [
                    "字体、行高和段间距按稳定排版层级组织，不在单页里混出多套阅读节奏。",
                    "品牌字样和正文排版分层处理，避免装饰字体侵入功能信息。",
                ]
            )
        elif topic_key == "尺寸比例":
            rules.extend(
                [
                    "尺寸调整只改变尺寸体系，不连带破坏圆角、留白和组件结构比例。",
                    "缩放图标或胶囊元素时，先保证整体比例，再处理局部修饰。",
                ]
            )
        elif topic_key == "设计 token":
            rules.extend(
                [
                    "把高频视觉决策沉淀为语义 token，而不是继续在页面里手工复制样式值。",
                    "token 先服务于颜色、圆角、间距和状态层级，再扩展到具体组件。",
                ]
            )
        else:
            rules.extend(
                [
                    f"围绕“{topic_key}”沉淀语义 token 和样式层级规则。",
                ]
            )

    elif category == "content-rules":
        if topic_key == "命名":
            rules.extend(
                [
                    "同一对象只保留一套命名口径，不在标题、按钮和说明文字里来回切换称呼。",
                    "命名优先服务识别和任务理解，不为追求口语化牺牲一致性。",
                ]
            )
        elif topic_key == "品牌表达":
            rules.extend(
                [
                    "品牌名、人物称呼和个性化表达要统一替换口径，避免页面不同位置各写一套。",
                    "品牌表达可以有情绪，但不能盖过核心任务信息。",
                ]
            )
        else:
            rules.extend(
                [
                    "界面文案优先短句和任务导向表达，避免解释过长导致主任务被冲淡。",
                    "品牌名、称呼和个性化文本需要统一替换口径，不在页面不同位置各写一套。",
                    "文案修改优先围绕可扫读性和一致性，而不是单句润色。",
                ]
            )

    elif category == "principles":
        rules.extend(
            [
                f"把围绕“{topic_key}”反复出现的判断上升为项目级设计原则，而不是只在单页修补。",
                "先确认该原则是否能跨多个页面成立，再决定是否进入通用 skill。",
            ]
        )

    if "重叠" in combined:
        rules.append("存在重叠风险的元素必须优先校验布局边界、点击区和层级关系。")
    if "对齐" in combined:
        rules.append("需要统一的组件在位置、高度、边界和内间距上保持对齐。")
    if "颜色" in combined and category != "style-system":
        rules.append("涉及颜色调整时，先回到统一的语义 token 和状态色规则。")
    if "文案太长" in combined or "太长" in combined:
        rules.append("解释型文本过长时，优先拆成短句或挪到次级层，不占用主任务区。")

    return _dedupe_preserve_order(rules)


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def build_evidence(items: list[CandidateMessage]) -> list[Evidence]:
    seen: set[tuple[str, str]] = set()
    evidence: list[Evidence] = []
    for item in items:
        summary = summarize_text(item.text)
        key = (item.source_path, summary)
        if key in seen:
            continue
        seen.add(key)
        evidence.append(
            Evidence(
                source=item.source_path,
                date=item.date,
                quote_summary=summary,
            )
        )
        if len(evidence) >= 5:
            break
    return evidence


def dedupe_candidate_messages(items: list[CandidateMessage]) -> list[CandidateMessage]:
    seen: set[tuple[str, str]] = set()
    result: list[CandidateMessage] = []
    for item in items:
        normalized = " ".join(item.text.split())
        key = (item.session_id, normalized)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
