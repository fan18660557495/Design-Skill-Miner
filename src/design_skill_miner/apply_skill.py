from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from .draft_skill import CATEGORY_FILES

MANAGED_START = "<!-- design-skill-miner:start -->"
MANAGED_END = "<!-- design-skill-miner:end -->"


def apply_draft_to_skill(
    draft_dir: Path,
    target_skill_dir: Path,
    *,
    section_name: str = "mined",
) -> dict[str, object]:
    draft_skill_path = draft_dir / "SKILL.md"
    draft_refs_dir = draft_dir / "references"
    manifest_path = draft_dir / "manifest.json"

    if not draft_skill_path.exists():
        raise FileNotFoundError(f"Draft SKILL.md not found: {draft_skill_path}")
    if not draft_refs_dir.exists():
        raise FileNotFoundError(f"Draft references directory not found: {draft_refs_dir}")
    if not manifest_path.exists():
        raise FileNotFoundError(f"Draft manifest.json not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    skill_name = manifest.get("skill_name", "generated-skill")
    categories: list[str] = list(manifest.get("categories", []))

    created = False
    if not target_skill_dir.exists():
        target_skill_dir.mkdir(parents=True, exist_ok=True)
        created = True

    backup_dir = backup_target_files(target_skill_dir)

    target_refs_dir = target_skill_dir / "references" / section_name
    target_refs_dir.mkdir(parents=True, exist_ok=True)

    copied_refs: list[Path] = []
    for category in categories:
        filename = CATEGORY_FILES.get(category)
        if not filename:
            continue
        source = draft_refs_dir / filename
        if not source.exists():
            continue
        destination = target_refs_dir / filename
        shutil.copy2(source, destination)
        copied_refs.append(destination)

    generated_dir = target_skill_dir / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    target_manifest_path = generated_dir / f"{skill_name}-manifest.json"
    shutil.copy2(manifest_path, target_manifest_path)

    target_skill_path = target_skill_dir / "SKILL.md"
    if target_skill_path.exists():
        original = target_skill_path.read_text(encoding="utf-8")
    else:
        original = render_stub_skill(skill_name)

    managed_block = render_managed_block(skill_name=skill_name, section_name=section_name, categories=categories)
    updated = replace_or_append_managed_block(original, managed_block)
    target_skill_path.write_text(updated, encoding="utf-8")

    return {
        "created_target": created,
        "backup_dir": backup_dir,
        "target_skill": target_skill_path,
        "target_manifest": target_manifest_path,
        "copied_references": copied_refs,
    }


def backup_target_files(target_skill_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = target_skill_dir / ".design-skill-miner-backups" / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    for relative in [Path("SKILL.md"), Path("references"), Path("generated")]:
        source = target_skill_dir / relative
        if not source.exists():
            continue
        destination = backup_dir / relative
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    return backup_dir


def render_managed_block(skill_name: str, section_name: str, categories: list[str]) -> str:
    labels = {
        "principles": "设计原则候选",
        "page-patterns": "页面模式候选",
        "interaction-patterns": "交互模式候选",
        "component-patterns": "组件模式候选",
        "style-system": "样式系统候选",
        "content-rules": "表达规范候选",
    }

    lines = [
        MANAGED_START,
        "## 自动沉淀候选",
        "",
        f"- 以下内容由 `design-skill-miner` 从历史对话提炼生成，对应草稿 skill：`{skill_name}`。",
        f"- 自动沉淀内容统一放在 `references/{section_name}/`，避免直接覆盖现有手写规范。",
        "- 人工确认后，再决定是否合并进正式 core 文档。",
        "",
        "### 读取路径",
        "",
    ]

    for category in categories:
        filename = CATEGORY_FILES.get(category)
        if not filename:
            continue
        lines.append(f"- 做{labels.get(category, category)}：读 `references/{section_name}/{filename}`")

    lines.extend(
        [
            "",
            "### 使用建议",
            "",
            "- 先把这里当成候选规则，不要自动当成正式规范。",
            "- 若和现有规范冲突，优先人工决策后再收口。",
            MANAGED_END,
        ]
    )
    return "\n".join(lines)


def replace_or_append_managed_block(original: str, managed_block: str) -> str:
    if MANAGED_START in original and MANAGED_END in original:
        start = original.index(MANAGED_START)
        end = original.index(MANAGED_END) + len(MANAGED_END)
        updated = original[:start].rstrip() + "\n\n" + managed_block + "\n"
        if end < len(original):
            tail = original[end:].lstrip("\n")
            if tail:
                updated += "\n" + tail
        return updated

    original = original.rstrip()
    if not original:
        return managed_block + "\n"
    return original + "\n\n" + managed_block + "\n"


def render_stub_skill(skill_name: str) -> str:
    return "\n".join(
        [
            "---",
            f"name: {skill_name}",
            "description: Auto-generated skill shell created before applying mined references.",
            "---",
            "",
            f"# {skill_name}",
            "",
            "这个 skill 目录原本没有入口文件，已由 design-skill-miner 创建最小壳。",
            "",
        ]
    )
