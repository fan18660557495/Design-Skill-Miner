from __future__ import annotations

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import MinerConfig
from .web_support import (
    api_apply_skill,
    api_agent_mine,
    api_get_agent_run,
    api_list_directories,
    api_mine_skill,
    api_pick_directory,
    api_publish_draft,
    api_projects,
    api_save_draft_file,
    api_scan,
    api_start_agent_run,
    api_test_llm_connection,
)


WEB_ROOT = Path(__file__).resolve().parents[2] / "web"


class WebHandler(SimpleHTTPRequestHandler):
    app_config = MinerConfig()

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
            if parsed.path == "/api/agent-run":
                query = parse_qs(parsed.query)
                run_id = _optional_value(query, "run_id")
                if not run_id:
                    raise ValueError("Missing required query parameter: run_id")
                return self._write_json(api_get_agent_run(run_id))

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

            if parsed.path == "/api/agent-mine":
                config = self.app_config
                sessions_root = Path(_required_str(payload, "sessions_root"))
                cwd_prefix = _optional_str(payload, "cwd_prefix")
                min_frequency = int(payload.get("min_frequency", 2) or 2)
                out_dir = payload.get("out_dir")
                skill_name = payload.get("skill_name") or "design-skill-draft"
                description = payload.get("description")
                goal = _optional_str(payload, "goal")
                skill_id = _optional_str(payload, "skill_id")
                review_min_score = _payload_float(payload, "review_min_score", config.agent_review_min_score)
                auto_prune = _payload_bool(payload, "auto_prune", config.agent_auto_prune)
                max_cycles = _payload_int(payload, "max_cycles", config.agent_max_cycles)
                memory_db_path = _optional_str(payload, "memory_db_path") or config.agent_memory_db_path
                enable_llm = _payload_bool(payload, "enable_llm", config.llm_enabled)
                llm_provider = _optional_str(payload, "llm_provider") or config.llm_provider
                llm_base_url = _optional_str(payload, "llm_base_url") or config.llm_base_url
                llm_model = _optional_str(payload, "llm_model") or config.llm_model
                llm_api_key_env = _optional_str(payload, "llm_api_key_env") or config.llm_api_key_env
                llm_api_key = _optional_str(payload, "llm_api_key")
                llm_json_mode = _payload_bool(payload, "llm_json_mode", config.llm_json_mode)
                llm_allow_insecure_tls = _payload_bool(payload, "llm_allow_insecure_tls", config.llm_allow_insecure_tls)
                llm_timeout_seconds = _payload_int(payload, "llm_timeout_seconds", config.llm_timeout_seconds)
                result = api_agent_mine(
                    sessions_root,
                    cwd_prefix=cwd_prefix,
                    min_frequency=min_frequency,
                    out_dir=Path(out_dir) if isinstance(out_dir, str) and out_dir else None,
                    skill_name=skill_name,
                    description=description if isinstance(description, str) else None,
                    goal=goal,
                    skill_id=skill_id,
                    review_min_score=review_min_score,
                    auto_prune=auto_prune,
                    max_cycles=max_cycles,
                    memory_db_path=memory_db_path,
                    enable_llm=enable_llm,
                    llm_provider=llm_provider,
                    llm_base_url=llm_base_url,
                    llm_model=llm_model,
                    llm_api_key_env=llm_api_key_env,
                    llm_api_key=llm_api_key,
                    llm_json_mode=llm_json_mode,
                    llm_allow_insecure_tls=llm_allow_insecure_tls,
                    llm_timeout_seconds=llm_timeout_seconds,
                )
                return self._write_json(result)

            if parsed.path == "/api/agent-run/start":
                config = self.app_config
                sessions_root = Path(_required_str(payload, "sessions_root"))
                cwd_prefix = _optional_str(payload, "cwd_prefix")
                min_frequency = int(payload.get("min_frequency", 2) or 2)
                out_dir = payload.get("out_dir")
                skill_name = payload.get("skill_name") or "design-skill-draft"
                description = payload.get("description")
                goal = _optional_str(payload, "goal")
                skill_id = _optional_str(payload, "skill_id")
                review_min_score = _payload_float(payload, "review_min_score", config.agent_review_min_score)
                auto_prune = _payload_bool(payload, "auto_prune", config.agent_auto_prune)
                max_cycles = _payload_int(payload, "max_cycles", config.agent_max_cycles)
                memory_db_path = _optional_str(payload, "memory_db_path") or config.agent_memory_db_path
                enable_llm = _payload_bool(payload, "enable_llm", config.llm_enabled)
                llm_provider = _optional_str(payload, "llm_provider") or config.llm_provider
                llm_base_url = _optional_str(payload, "llm_base_url") or config.llm_base_url
                llm_model = _optional_str(payload, "llm_model") or config.llm_model
                llm_api_key_env = _optional_str(payload, "llm_api_key_env") or config.llm_api_key_env
                llm_api_key = _optional_str(payload, "llm_api_key")
                llm_json_mode = _payload_bool(payload, "llm_json_mode", config.llm_json_mode)
                llm_allow_insecure_tls = _payload_bool(payload, "llm_allow_insecure_tls", config.llm_allow_insecure_tls)
                llm_timeout_seconds = _payload_int(payload, "llm_timeout_seconds", config.llm_timeout_seconds)
                run_target = _optional_str(payload, "run_target") or "draft"
                approve_publish = _payload_bool(payload, "approve_publish", False)
                publish_requires_approval = _payload_bool(
                    payload,
                    "publish_requires_approval",
                    config.agent_publish_requires_approval,
                )
                publish_root = _optional_str(payload, "publish_root")
                publish_name = _optional_str(payload, "publish_name")
                result = api_start_agent_run(
                    sessions_root,
                    cwd_prefix=cwd_prefix,
                    min_frequency=min_frequency,
                    out_dir=Path(out_dir) if isinstance(out_dir, str) and out_dir else None,
                    skill_name=skill_name,
                    description=description if isinstance(description, str) else None,
                    goal=goal,
                    skill_id=skill_id,
                    review_min_score=review_min_score,
                    auto_prune=auto_prune,
                    max_cycles=max_cycles,
                    memory_db_path=memory_db_path,
                    enable_llm=enable_llm,
                    llm_provider=llm_provider,
                    llm_base_url=llm_base_url,
                    llm_model=llm_model,
                    llm_api_key_env=llm_api_key_env,
                    llm_api_key=llm_api_key,
                    llm_json_mode=llm_json_mode,
                    llm_allow_insecure_tls=llm_allow_insecure_tls,
                    llm_timeout_seconds=llm_timeout_seconds,
                    run_target=run_target,
                    approve_publish=approve_publish,
                    publish_requires_approval=publish_requires_approval,
                    publish_root=Path(publish_root) if publish_root else None,
                    publish_name=publish_name,
                )
                return self._write_json(result)

            if parsed.path == "/api/llm/test":
                config = self.app_config
                llm_provider = _optional_str(payload, "llm_provider") or config.llm_provider
                llm_base_url = _optional_str(payload, "llm_base_url") or config.llm_base_url
                llm_model = _optional_str(payload, "llm_model") or config.llm_model
                llm_api_key_env = _optional_str(payload, "llm_api_key_env") or config.llm_api_key_env
                llm_api_key = _optional_str(payload, "llm_api_key")
                llm_allow_insecure_tls = _payload_bool(payload, "llm_allow_insecure_tls", config.llm_allow_insecure_tls)
                llm_timeout_seconds = _payload_int(payload, "llm_timeout_seconds", min(config.llm_timeout_seconds, 30))
                result = api_test_llm_connection(
                    llm_provider=llm_provider,
                    llm_base_url=llm_base_url,
                    llm_model=llm_model,
                    llm_api_key_env=llm_api_key_env,
                    llm_api_key=llm_api_key,
                    llm_allow_insecure_tls=llm_allow_insecure_tls,
                    llm_timeout_seconds=llm_timeout_seconds,
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


def serve(host: str = "127.0.0.1", port: int = 8765, config: MinerConfig | None = None) -> None:
    WebHandler.app_config = config or MinerConfig()
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


def _payload_bool(payload: dict, key: str, default: bool) -> bool:
    if key not in payload:
        return default
    return bool(payload.get(key))


def _payload_int(payload: dict, key: str, default: int) -> int:
    if key not in payload:
        return default
    value = payload.get(key)
    return int(value or default)


def _payload_float(payload: dict, key: str, default: float) -> float:
    if key not in payload:
        return default
    value = payload.get(key)
    return float(value or default)
