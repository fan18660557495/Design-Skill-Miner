from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from .apply_skill import apply_draft_to_skill
from .attribution import project_id_from_prefix
from .draft_skill import CATEGORY_FILES, write_skill_draft
from .indexer import build_index, summarize_projects
from .pipeline import generate_insights
from .publish_skill import publish_draft


def api_pick_directory(title: str = "选择目录", start_path: Path | None = None) -> dict:
    default_path = (start_path or Path.home()).expanduser()
    if default_path.is_file():
        default_path = default_path.parent
    if not default_path.exists():
        default_path = Path.home()

    script = [
        "on run argv",
        "set promptText to item 1 of argv",
        "set defaultPath to item 2 of argv",
        'tell application "System Events" to activate',
        "set chosenFolder to choose folder with prompt promptText default location (POSIX file defaultPath)",
        "return POSIX path of chosenFolder",
        "end run",
    ]
    cmd = ["osascript"]
    for line in script:
        cmd.extend(["-e", line])
    cmd.extend([title, str(default_path)])

    try:
        completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        if "-128" in stderr:
            return {"canceled": True, "path": None}
        raise RuntimeError(stderr or "Failed to pick directory") from exc

    chosen = completed.stdout.strip()
    return {"canceled": False, "path": chosen}


def api_list_directories(path: Path | None = None) -> dict:
    if path is None:
        roots = []
        for candidate in [Path.home(), Path.home() / "code", Path.home() / ".codex", Path("/tmp")]:
            resolved = candidate.expanduser()
            if resolved.exists():
                roots.append(
                    {
                        "name": resolved.name or str(resolved),
                        "path": str(resolved),
                    }
                )
        return {
            "current_path": None,
            "parent_path": None,
            "directories": roots,
        }

    current = path.expanduser().resolve()
    if not current.exists():
        raise ValueError(f"Path does not exist: {current}")
    if not current.is_dir():
        raise ValueError(f"Path is not a directory: {current}")

    directories = []
    for child in sorted(current.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        if not child.is_dir():
            continue
        directories.append({"name": child.name, "path": str(child)})

    parent = current.parent if current.parent != current else None
    return {
        "current_path": str(current),
        "parent_path": str(parent) if parent else None,
        "directories": directories,
    }


def api_projects(sessions_root: Path, cwd_prefix: str | None = None) -> dict:
    indexed = build_index(sessions_root, cwd_prefix=cwd_prefix)
    if cwd_prefix:
        target_project = project_id_from_prefix(cwd_prefix)
        indexed = [item for item in indexed if item.project_id == target_project]
    counts = summarize_projects(indexed)
    projects = []
    for project_id, count in counts:
        matching = [item for item in indexed if item.project_id == project_id]
        sample_cwd = next((item.cwd for item in matching if item.cwd), None)
        projects.append(
            {
                "project_id": project_id,
                "session_count": count,
                "sample_cwd": sample_cwd,
            }
        )
    return {"projects": projects, "session_count": len(indexed)}


def api_scan(sessions_root: Path, cwd_prefix: str | None = None, min_frequency: int = 2) -> dict:
    insights, stats = generate_insights(sessions_root, cwd_prefix=cwd_prefix, min_frequency=min_frequency)
    return {
        "stats": stats,
        "insights": [insight.to_dict() for insight in insights],
    }


def api_mine_skill(
    sessions_root: Path,
    cwd_prefix: str | None = None,
    min_frequency: int = 2,
    out_dir: Path | None = None,
    skill_name: str = "design-skill-draft",
    description: str | None = None,
) -> dict:
    insights, stats = generate_insights(sessions_root, cwd_prefix=cwd_prefix, min_frequency=min_frequency)
    if out_dir is None:
        out_dir = Path(tempfile.mkdtemp(prefix="design-skill-miner-"))
    outputs = write_skill_draft(insights, out_dir, skill_name=skill_name, description=description)
    return {
        "stats": stats,
        "draft_dir": str(out_dir),
        "files": preview_draft(out_dir),
        "manifest_path": str(outputs["manifest"]),
        "skill_path": str(outputs["skill"]),
    }


def api_apply_skill(draft_dir: Path, target_skill_dir: Path, section_name: str = "mined") -> dict:
    outputs = apply_draft_to_skill(draft_dir, target_skill_dir, section_name=section_name)
    return {
        "target_skill": str(outputs["target_skill"]),
        "backup_dir": str(outputs["backup_dir"]),
        "target_manifest": str(outputs["target_manifest"]),
        "copied_references": [str(path) for path in outputs["copied_references"]],
    }


def api_publish_draft(draft_dir: Path, publish_root: Path, publish_name: str | None = None) -> dict:
    outputs = publish_draft(draft_dir, publish_root, publish_name=publish_name)
    return {
        "publish_dir": str(outputs["publish_dir"]),
        "publish_root": str(outputs["publish_root"]),
        "metadata_path": str(outputs["metadata_path"]),
    }


def api_save_draft_file(file_path: Path, content: str) -> dict:
    requested = file_path.expanduser()
    target = requested.resolve()
    if not target.exists():
        raise FileNotFoundError(f"Draft file not found: {target}")
    if not target.is_file():
        raise ValueError(f"Draft path is not a file: {target}")
    if target.suffix not in {".md", ".json"}:
        raise ValueError(f"Unsupported draft file type: {target.suffix}")

    target.write_text(content, encoding="utf-8")
    display_root = requested.parent.parent if requested.parent.name == "references" else requested.parent
    return {
        "saved": True,
        "file": {
            "name": requested.name,
            "path": str(requested),
            "relative_path": str(requested.relative_to(display_root)),
            "content": content,
        },
    }


def preview_draft(draft_dir: Path) -> list[dict]:
    result: list[dict] = []
    skill_path = draft_dir / "SKILL.md"
    if skill_path.exists():
        result.append(_file_payload(skill_path, draft_dir))

    refs_dir = draft_dir / "references"
    if refs_dir.exists():
        for path in sorted(refs_dir.glob("*.md")):
            result.append(_file_payload(path, draft_dir))

    manifest_path = draft_dir / "manifest.json"
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        result.append(
            {
                "name": "manifest.json",
                "path": str(manifest_path),
                "relative_path": "manifest.json",
                "content": json.dumps(payload, ensure_ascii=False, indent=2),
            }
        )
    return result


def _file_payload(path: Path, root: Path) -> dict:
    return {
        "name": path.name,
        "path": str(path),
        "relative_path": str(path.relative_to(root)),
        "content": path.read_text(encoding="utf-8"),
    }
