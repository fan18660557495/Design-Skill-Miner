from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path


def publish_draft(
    draft_dir: Path,
    staging_root: Path,
    *,
    publish_name: str | None = None,
) -> dict[str, Path]:
    draft_dir = draft_dir.expanduser().resolve()
    staging_root = staging_root.expanduser().resolve()

    if not draft_dir.exists() or not draft_dir.is_dir():
        raise FileNotFoundError(f"Draft directory not found: {draft_dir}")

    manifest_path = draft_dir / "manifest.json"
    skill_name = publish_name or derive_publish_name(draft_dir, manifest_path)
    slug = slugify(skill_name)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    publish_dir = staging_root / slug / timestamp
    publish_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(draft_dir, publish_dir)

    metadata_path = publish_dir / "published.json"
    metadata_path.write_text(
        json.dumps(
            {
                "publish_name": skill_name,
                "published_at": timestamp,
                "source_draft_dir": str(draft_dir),
                "published_dir": str(publish_dir),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "publish_dir": publish_dir,
        "publish_root": staging_root,
        "metadata_path": metadata_path,
    }


def derive_publish_name(draft_dir: Path, manifest_path: Path) -> str:
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        skill_name = payload.get("skill_name")
        if isinstance(skill_name, str) and skill_name.strip():
            return skill_name.strip()
    return draft_dir.name


def slugify(value: str) -> str:
    cleaned = value.strip().lower().replace("_", "-").replace(" ", "-")
    allowed = []
    for char in cleaned:
        if char.isalnum() or char in {"-", "_"}:
            allowed.append(char)
    result = "".join(allowed).strip("-_")
    return result or "published-skill"
