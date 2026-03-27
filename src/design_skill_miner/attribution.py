from __future__ import annotations

from pathlib import Path

from .models import ProjectAttribution, SessionRecord


def project_id_from_prefix(cwd_prefix: str) -> str:
    return _slugify(Path(cwd_prefix).name)


def attribute_project(session: SessionRecord, cwd_prefix: str | None = None) -> ProjectAttribution:
    signals: list[str] = []

    if cwd_prefix and session.cwd and session.cwd.startswith(cwd_prefix):
        project_id = project_id_from_prefix(cwd_prefix)
        signals.append(f"cwd-prefix:{cwd_prefix}")
        return ProjectAttribution(project_id=project_id, confidence=0.98, signals=signals)

    if session.cwd:
        project_name = Path(session.cwd).name
        if project_name:
            signals.append(f"cwd:{session.cwd}")
            return ProjectAttribution(
                project_id=_slugify(project_name),
                confidence=0.90,
                signals=signals,
            )

    for message in session.messages:
        for ref in message.file_refs:
            path = Path(ref)
            if path.parts:
                project_name = _guess_project_from_ref(path)
                if project_name:
                    signals.append(f"file-ref:{ref}")
                    return ProjectAttribution(
                        project_id=_slugify(project_name),
                        confidence=0.72,
                        signals=signals,
                    )

    return ProjectAttribution(project_id="unknown", confidence=0.2, signals=["no-strong-signal"])


def _guess_project_from_ref(path: Path) -> str | None:
    parts = [part for part in path.parts if part and part not in (".", "..")]
    if "code" in parts:
        idx = parts.index("code")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return parts[0] if parts else None


def _slugify(value: str) -> str:
    cleaned = value.strip().lower().replace(" ", "-").replace("_", "-")
    return "-".join(part for part in cleaned.split("-") if part)
