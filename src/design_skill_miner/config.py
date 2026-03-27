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


def load_config(config_path: Path | None) -> MinerConfig:
    path = resolve_config_path(config_path)
    if path is None or not path.exists():
        return MinerConfig()

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    miner = data.get("miner", {})
    if not isinstance(miner, dict):
        return MinerConfig()

    return MinerConfig(
        sessions_root=_as_str(miner.get("sessions_root")),
        cwd_prefix=_as_str(miner.get("cwd_prefix")),
        min_frequency=_as_int(miner.get("min_frequency"), default=2),
        output_dir=_as_str(miner.get("output_dir")),
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

