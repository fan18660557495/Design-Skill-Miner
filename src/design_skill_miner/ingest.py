from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import MessageRecord, SessionRecord


def find_jsonl_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.jsonl"))


def load_sessions(root: Path) -> list[SessionRecord]:
    sessions: list[SessionRecord] = []
    for path in find_jsonl_files(root):
        session = load_session(path)
        if session is not None:
            sessions.append(session)
    return sessions


def load_session(path: Path) -> SessionRecord | None:
    messages: list[MessageRecord] = []
    cwd: str | None = None
    date: str | None = None
    session_id = path.stem

    try:
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                event = _safe_load_json(line)
                if not isinstance(event, dict):
                    continue

                cwd = cwd or _extract_cwd(event)
                date = date or _extract_date(event)
                extracted = _extract_message(event)
                if extracted is not None:
                    messages.append(extracted)
    except UnicodeDecodeError:
        return None

    if not messages:
        return None

    return SessionRecord(
        session_id=session_id,
        source_path=str(path),
        date=date,
        cwd=cwd,
        messages=messages,
    )


def _safe_load_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _extract_cwd(event: dict[str, Any]) -> str | None:
    candidates = [
        event.get("cwd"),
        event.get("workdir"),
    ]
    payload = event.get("payload")
    if isinstance(payload, dict):
        candidates.extend([payload.get("cwd"), payload.get("workdir")])
    context = event.get("environment_context")
    if isinstance(context, dict):
        candidates.extend([context.get("cwd"), context.get("workdir")])

    for candidate in candidates:
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def _extract_date(event: dict[str, Any]) -> str | None:
    for key in ("date", "created_at", "timestamp", "time"):
        value = event.get(key)
        if isinstance(value, str) and value:
            return value[:10]
    payload = event.get("payload")
    if isinstance(payload, dict):
        for key in ("timestamp", "created_at", "time"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value[:10]
    return None


def _extract_message(event: dict[str, Any]) -> MessageRecord | None:
    role = event.get("role")
    text = _extract_text(event)
    if not isinstance(text, str) or not text.strip():
        return None

    if not isinstance(role, str):
        role = _extract_role(event)

    file_refs = _extract_file_refs(text)
    return MessageRecord(role=role or "unknown", text=text.strip(), file_refs=file_refs)


def _extract_text(event: dict[str, Any]) -> str | None:
    for key in ("text", "content", "message"):
        value = event.get(key)
        if isinstance(value, str):
            return value
    content = event.get("content")
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        if parts:
            return "\n".join(parts)

    payload = event.get("payload")
    if isinstance(payload, dict):
        for key in ("message", "text"):
            value = payload.get(key)
            if isinstance(value, str):
                return value

        payload_message = payload.get("message")
        if isinstance(payload_message, dict):
            role = payload_message.get("role")
            content = payload_message.get("content")
            text = _extract_text_from_content(content)
            if text:
                return text

        content = payload.get("content")
        text = _extract_text_from_content(content)
        if text:
            return text

    return None


def _extract_role(event: dict[str, Any]) -> str | None:
    payload = event.get("payload")
    if isinstance(payload, dict):
        payload_type = payload.get("type")
        if payload_type == "user_message":
            return "user"
        if payload_type == "agent_message":
            return "assistant"
        for key in ("role",):
            value = payload.get(key)
            if isinstance(value, str):
                return value
        payload_message = payload.get("message")
        if isinstance(payload_message, dict):
            value = payload_message.get("role")
            if isinstance(value, str):
                return value
    return None


def _extract_text_from_content(content: Any) -> str | None:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return None

    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str):
            parts.append(text)
    if parts:
        return "\n".join(parts)
    return None


def _extract_file_refs(text: str) -> list[str]:
    refs: list[str] = []
    for token in text.split():
        if "/" in token and "." in token:
            refs.append(token.strip("`()[],'\""))
    return refs
