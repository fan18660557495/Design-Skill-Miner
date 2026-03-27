from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .apply_skill import apply_draft_to_skill
from .config import MinerConfig, load_config
from .draft_skill import load_insights, write_skill_draft
from .indexer import build_index, summarize_projects, write_index
from .pipeline import generate_insights
from .report import write_reports
from .web import serve


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args, config)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="design-skill-miner",
        description="Mine repeated design conversations from local Codex session exports.",
    )
    parser.add_argument("--config", type=Path, default=None, help="Optional TOML config path.")
    subparsers = parser.add_subparsers(dest="command")

    scan = subparsers.add_parser("scan", help="Scan sessions and generate insight reports.")
    scan.add_argument("sessions_root", type=Path)
    scan.add_argument("--out", type=Path, default=None)
    scan.add_argument("--cwd-prefix", default=None)
    scan.add_argument("--min-frequency", type=int, default=None)
    scan.set_defaults(func=run_scan)

    index = subparsers.add_parser("index", help="Build a session index with project attribution.")
    index.add_argument("sessions_root", type=Path)
    index.add_argument("--out", type=Path, default=None)
    index.add_argument("--cwd-prefix", default=None)
    index.set_defaults(func=run_index)

    projects = subparsers.add_parser("projects", help="Summarize discovered projects from sessions.")
    projects.add_argument("sessions_root", type=Path)
    projects.add_argument("--cwd-prefix", default=None)
    projects.set_defaults(func=run_projects)

    draft = subparsers.add_parser("draft-skill", help="Generate a skill draft from insights.json.")
    draft.add_argument("insights_json", type=Path)
    draft.add_argument("--out", type=Path, default=Path("./skill-draft"))
    draft.add_argument("--skill-name", default="design-skill-draft")
    draft.add_argument("--description", default=None)
    draft.set_defaults(func=run_draft_skill)

    mine = subparsers.add_parser("mine-skill", help="Generate a skill draft directly from sessions.")
    mine.add_argument("sessions_root", type=Path)
    mine.add_argument("--cwd-prefix", default=None)
    mine.add_argument("--min-frequency", type=int, default=None)
    mine.add_argument("--out", type=Path, default=Path("./mined-skill"))
    mine.add_argument("--skill-name", default="design-skill-draft")
    mine.add_argument("--description", default=None)
    mine.set_defaults(func=run_mine_skill)

    apply = subparsers.add_parser("apply-to-skill", help="Apply a generated draft into an existing skill directory.")
    apply.add_argument("draft_dir", type=Path)
    apply.add_argument("target_skill_dir", type=Path)
    apply.add_argument("--section-name", default="mined")
    apply.set_defaults(func=run_apply_to_skill)

    web = subparsers.add_parser("serve", help="Run the local web UI for designers.")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8765)
    web.set_defaults(func=run_serve)

    return parser


def run_scan(args: argparse.Namespace, config: MinerConfig) -> int:
    sessions_root = _resolve_path(args.sessions_root, config.sessions_root)
    out = args.out or _default_out(config, Path("./out"))
    cwd_prefix = args.cwd_prefix or config.cwd_prefix
    min_frequency = args.min_frequency or config.min_frequency

    insights, stats = generate_insights(sessions_root, cwd_prefix=cwd_prefix, min_frequency=min_frequency)
    json_path, md_path = write_reports(insights, out)
    print_stats(stats)
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    return 0


def run_index(args: argparse.Namespace, config: MinerConfig) -> int:
    sessions_root = _resolve_path(args.sessions_root, config.sessions_root)
    out = args.out or _default_out(config, Path("./out/index.json"))
    cwd_prefix = args.cwd_prefix or config.cwd_prefix
    indexed = build_index(sessions_root, cwd_prefix=cwd_prefix)
    out_path = out if out.suffix else out / "index.json"
    write_index(indexed, out_path)
    print(f"Sessions indexed: {len(indexed)}")
    print(f"Index written: {out_path}")
    return 0


def run_projects(args: argparse.Namespace, config: MinerConfig) -> int:
    sessions_root = _resolve_path(args.sessions_root, config.sessions_root)
    cwd_prefix = args.cwd_prefix or config.cwd_prefix
    indexed = build_index(sessions_root, cwd_prefix=cwd_prefix)
    summary = summarize_projects(indexed)
    print("Projects:")
    for project_id, count in summary:
        print(f"- {project_id}: {count}")
    return 0


def run_draft_skill(args: argparse.Namespace, _config: MinerConfig) -> int:
    insights = load_insights(args.insights_json)
    outputs = write_skill_draft(insights, args.out, skill_name=args.skill_name, description=args.description)
    print(f"Skill draft written: {outputs['skill']}")
    print(f"Manifest written: {outputs['manifest']}")
    print(f"Reference files: {sum(1 for key in outputs if key not in ('skill', 'manifest'))}")
    return 0


def run_mine_skill(args: argparse.Namespace, config: MinerConfig) -> int:
    sessions_root = _resolve_path(args.sessions_root, config.sessions_root)
    cwd_prefix = args.cwd_prefix or config.cwd_prefix
    min_frequency = args.min_frequency or config.min_frequency
    insights, stats = generate_insights(sessions_root, cwd_prefix=cwd_prefix, min_frequency=min_frequency)
    outputs = write_skill_draft(insights, args.out, skill_name=args.skill_name, description=args.description)
    print_stats(stats)
    print(f"Skill draft written: {outputs['skill']}")
    print(f"Manifest written: {outputs['manifest']}")
    return 0


def run_apply_to_skill(args: argparse.Namespace, _config: MinerConfig) -> int:
    outputs = apply_draft_to_skill(args.draft_dir, args.target_skill_dir, section_name=args.section_name)
    print(f"Applied draft to: {outputs['target_skill']}")
    print(f"Backup created at: {outputs['backup_dir']}")
    print(f"Manifest copied to: {outputs['target_manifest']}")
    print(f"References copied: {len(outputs['copied_references'])}")
    return 0


def run_serve(args: argparse.Namespace, _config: MinerConfig) -> int:
    serve(host=args.host, port=args.port)
    return 0


def _resolve_path(explicit: Path, configured: str | None) -> Path:
    if explicit:
        return explicit
    if configured:
        return Path(configured)
    raise SystemExit("sessions_root is required")


def _default_out(config: MinerConfig, fallback: Path) -> Path:
    if config.output_dir:
        return Path(config.output_dir)
    return fallback


def print_stats(stats: dict[str, int]) -> None:
    print(f"Sessions scanned: {stats['sessions_scanned']}")
    print(f"Candidate messages: {stats['candidate_messages']}")
    print(f"Insights written: {stats['insights_written']}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
