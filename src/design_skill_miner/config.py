from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass
class MinerConfig:
    sessions_root: str | None = None
    cwd_prefix: str | None = None
    min_frequency: int = 2
    output_dir: str | None = None
    agent_review_min_score: float = 0.6
    agent_auto_prune: bool = True
    agent_max_cycles: int = 3
    agent_memory_db_path: str | None = None
    agent_publish_requires_approval: bool = True
    llm_enabled: bool = False
    llm_provider: str = "openai-compatible"
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key_env: str = "OPENAI_API_KEY"
    llm_json_mode: bool = True
    llm_allow_insecure_tls: bool = False
    llm_timeout_seconds: int = 120


def load_config(config_path: Path | None) -> MinerConfig:
    path = resolve_config_path(config_path)
    if path is None or not path.exists():
        return MinerConfig()

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    miner = data.get("miner", {})
    agent = data.get("agent", {})
    llm = data.get("llm", {})
    if not isinstance(miner, dict):
        miner = {}
    if not isinstance(agent, dict):
        agent = {}
    if not isinstance(llm, dict):
        llm = {}

    return MinerConfig(
        sessions_root=_as_str(miner.get("sessions_root")),
        cwd_prefix=_as_str(miner.get("cwd_prefix")),
        min_frequency=_as_int(miner.get("min_frequency"), default=2),
        output_dir=_as_str(miner.get("output_dir")),
        agent_review_min_score=_as_float(agent.get("review_min_score"), default=0.6),
        agent_auto_prune=_as_bool(agent.get("auto_prune"), default=True),
        agent_max_cycles=_as_int(agent.get("max_cycles"), default=3),
        agent_memory_db_path=_as_str(agent.get("memory_db_path")),
        agent_publish_requires_approval=_as_bool(agent.get("publish_requires_approval"), default=True),
        llm_enabled=_as_bool(llm.get("enabled"), default=False),
        llm_provider=_as_str(llm.get("provider")) or "openai-compatible",
        llm_base_url=_as_str(llm.get("base_url")),
        llm_model=_as_str(llm.get("model")),
        llm_api_key_env=_as_str(llm.get("api_key_env")) or "OPENAI_API_KEY",
        llm_json_mode=_as_bool(llm.get("json_mode"), default=True),
        llm_allow_insecure_tls=_as_bool(llm.get("allow_insecure_tls"), default=False),
        llm_timeout_seconds=_as_int(llm.get("timeout_seconds"), default=120),
    )


def resolve_config_path(config_path: Path | None) -> Path | None:
    if config_path is not None:
        return config_path
    cwd_candidate = Path.cwd() / ".design-skill-miner.toml"
    if cwd_candidate.exists():
        return cwd_candidate
    home_candidate = Path.home() / ".config" / "design-skill-miner" / "config.toml"
    if home_candidate.exists():
        return home_candidate
    return None


def _as_str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _as_int(value: object, default: int) -> int:
    return value if isinstance(value, int) and value > 0 else default


def _as_float(value: object, default: float) -> float:
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    return default


def _as_bool(value: object, default: bool) -> bool:
    return value if isinstance(value, bool) else default
