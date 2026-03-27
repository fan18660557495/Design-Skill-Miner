from __future__ import annotations

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .web_support import (
    api_apply_skill,
    api_list_directories,
    api_mine_skill,
    api_pick_directory,
    api_publish_draft,
    api_projects,
    api_save_draft_file,
    api_scan,
)


WEB_ROOT = Path(__file__).resolve().parents[2] / "web"


class WebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/api/projects":
                query = parse_qs(parsed.query)
                sessions_root = _required_path(query, "sessions_root")
                cwd_prefix = _optional_value(query, "cwd_prefix")
                return self._write_json(api_projects(sessions_root, cwd_prefix=cwd_prefix))
            if parsed.path == "/api/scan":
                query = parse_qs(parsed.query)
                sessions_root = _required_path(query, "sessions_root")
                cwd_prefix = _optional_value(query, "cwd_prefix")
                min_frequency = _optional_int(query, "min_frequency", 2)
                return self._write_json(api_scan(sessions_root, cwd_prefix=cwd_prefix, min_frequency=min_frequency))
            if parsed.path == "/api/fs/list":
                query = parse_qs(parsed.query)
                path = _optional_value(query, "path")
                return self._write_json(api_list_directories(Path(path) if path else None))

            if parsed.path in {"/", "/index.html"}:
                self.path = "/index.html"
            return super().do_GET()
        except Exception as exc:  # noqa: BLE001
            return self._write_json({"error": str(exc)}, status=400)

    def do_POST(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            payload = self._read_json()

            if parsed.path == "/api/mine-skill":
                sessions_root = Path(_required_str(payload, "sessions_root"))
                cwd_prefix = _optional_str(payload, "cwd_prefix")
                min_frequency = int(payload.get("min_frequency", 2) or 2)
                out_dir = payload.get("out_dir")
                skill_name = payload.get("skill_name") or "design-skill-draft"
                description = payload.get("description")
                result = api_mine_skill(
                    sessions_root,
                    cwd_prefix=cwd_prefix,
                    min_frequency=min_frequency,
                    out_dir=Path(out_dir) if isinstance(out_dir, str) and out_dir else None,
                    skill_name=skill_name,
                    description=description if isinstance(description, str) else None,
                )
                return self._write_json(result)

            if parsed.path == "/api/apply-skill":
                draft_dir = Path(_required_str(payload, "draft_dir"))
                target_skill_dir = Path(_required_str(payload, "target_skill_dir"))
                section_name = payload.get("section_name") or "mined"
                result = api_apply_skill(draft_dir, target_skill_dir, section_name=section_name)
                return self._write_json(result)
            if parsed.path == "/api/fs/pick-directory":
                title = _optional_str(payload, "title") or "选择目录"
                start_path = _optional_str(payload, "start_path")
                result = api_pick_directory(title=title, start_path=Path(start_path) if start_path else None)
                return self._write_json(result)
            if parsed.path == "/api/save-draft-file":
                file_path = Path(_required_str(payload, "file_path"))
                content = _required_str(payload, "content", allow_empty=True)
                result = api_save_draft_file(file_path, content)
                return self._write_json(result)
            if parsed.path == "/api/publish-draft":
                draft_dir = Path(_required_str(payload, "draft_dir"))
                publish_root = Path(_required_str(payload, "publish_root"))
                publish_name = _optional_str(payload, "publish_name")
                result = api_publish_draft(draft_dir, publish_root, publish_name=publish_name)
                return self._write_json(result)

            self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
        except Exception as exc:  # noqa: BLE001
            return self._write_json({"error": str(exc)}, status=400)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _write_json(self, payload: dict, status: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), WebHandler)
    print(f"Design Skill Miner Web UI running at http://{host}:{port}")
    print(f"Serving static files from {WEB_ROOT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _required_path(query: dict[str, list[str]], key: str) -> Path:
    value = _optional_value(query, key)
    if not value:
        raise ValueError(f"Missing required query parameter: {key}")
    return Path(value)


def _optional_value(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key) or []
    return values[0] if values else None


def _optional_int(query: dict[str, list[str]], key: str, default: int) -> int:
    value = _optional_value(query, key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _required_str(payload: dict, key: str, *, allow_empty: bool = False) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or (not allow_empty and not value):
        raise ValueError(f"Missing required field: {key}")
    return value


def _optional_str(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) and value else None
