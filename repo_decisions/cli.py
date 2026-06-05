from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from .core import (
    add_decision,
    build_brief,
    list_decisions,
    locate_adrs,
    supersede_decision,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="repo-decisions")
    parser.add_argument("--root", default=".", help="Repository root or subdirectory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    locate_parser = subparsers.add_parser("locate", help="Locate ADR directory and format")
    locate_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    list_parser = subparsers.add_parser("list", help="List ADR decisions")
    list_parser.add_argument("--active-only", action="store_true", help="Only list accepted ADRs")
    list_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    brief_parser = subparsers.add_parser("brief", help="Build compact accepted-ADR prompt block")
    brief_parser.add_argument("--max-chars", type=int, default=None)

    add_parser = subparsers.add_parser("add", help="Add a new ADR")
    _decision_args(add_parser)
    add_parser.add_argument("--status", default="accepted")

    supersede_parser = subparsers.add_parser("supersede", help="Supersede an accepted ADR")
    supersede_parser.add_argument("target", help="ADR number, id, stem, or filename")
    _decision_args(supersede_parser)

    config_parser = subparsers.add_parser("config", help="Read or write repo-decisions config")
    config_parser.add_argument("--scope", choices=("local", "global"), default="local")
    config_parser.add_argument("--set", dest="set_values", action="append", default=[])

    codex_parser = subparsers.add_parser("codex", help="Run Codex with ADR brief prepended")
    codex_parser.add_argument("--print-prompt", action="store_true", help="Print enriched prompt and exit")
    codex_parser.add_argument("--codex-bin", default=os.environ.get("REPO_DECISIONS_CODEX_BIN", "codex"))
    codex_parser.add_argument(
        "--codex-arg",
        action="append",
        default=[],
        help="Argument passed to `codex exec`. Repeat for multiple args.",
    )
    codex_parser.add_argument("prompt", nargs=argparse.REMAINDER)

    args = parser.parse_args(argv)
    root = Path(args.root)

    if args.command == "locate":
        return _locate(root, args.json)
    if args.command == "list":
        return _list(root, include_inactive=not args.active_only, as_json=args.json)
    if args.command == "brief":
        print(build_brief(root, max_chars=args.max_chars), end="")
        return 0
    if args.command == "add":
        path = add_decision(
            root,
            title=args.title,
            context=args.context,
            decision=args.decision,
            consequences=args.consequence,
            options=args.option,
            status=args.status,
        )
        print(path)
        return 0
    if args.command == "supersede":
        old_path, new_path = supersede_decision(
            root,
            args.target,
            title=args.title,
            context=args.context,
            decision=args.decision,
            consequences=args.consequence,
            options=args.option,
        )
        print(f"superseded {old_path}")
        print(f"created {new_path}")
        return 0
    if args.command == "config":
        return _config(root, args.scope, args.set_values)
    if args.command == "codex":
        return _codex(root, args)
    return 2


def _decision_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--title", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--decision", required=True)
    parser.add_argument(
        "--consequence",
        action="append",
        default=[],
        help="Consequence line. Repeat for multiple consequences.",
    )
    parser.add_argument("--option", action="append", default=[], help="Considered option")


def _locate(root: Path, as_json: bool) -> int:
    location = locate_adrs(root)
    if as_json:
        print(
            json.dumps(
                {
                    "root": str(location.root),
                    "adr_dir": str(location.adr_dir),
                    "source": location.source,
                    "records": len(location.records),
                    "template": str(location.profile.template_path) if location.profile.template_path else None,
                    "profile": {
                        "number_width": location.profile.number_width,
                        "filename_style": location.profile.filename_style,
                        "status_style": location.profile.status_style,
                        "date_style": location.profile.date_style,
                        "section_headings": list(location.profile.section_headings),
                    },
                },
                indent=2,
            )
        )
        return 0
    print(f"root: {location.root}")
    print(f"adr_dir: {location.adr_dir}")
    print(f"source: {location.source}")
    print(f"records: {len(location.records)}")
    if location.profile.template_path:
        print(f"template: {location.profile.template_path}")
    return 0


def _list(root: Path, include_inactive: bool, as_json: bool) -> int:
    records = list_decisions(root, include_inactive=include_inactive)
    if as_json:
        print(
            json.dumps(
                [
                    {
                        "id": record.id,
                        "number": record.number,
                        "title": record.title,
                        "status": record.status,
                        "path": str(record.path),
                        "date": record.date,
                    }
                    for record in records
                ],
                indent=2,
            )
        )
        return 0
    for record in records:
        print(f"{record.id}\t{record.status}\t{record.title}\t{record.path}")
    return 0


def _config(root: Path, scope: str, set_values: list[str]) -> int:
    path = _config_path(root, scope)
    if not set_values:
        if path.exists():
            print(path.read_text(encoding="utf-8"), end="")
        else:
            print(f"{path} does not exist")
        return 0

    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = [line for line in existing.splitlines() if line.strip()]
    values = dict(_split_assignment(item) for item in set_values)
    kept = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else None
        if key and key in values:
            continue
        kept.append(line)
    for key, value in values.items():
        kept.append(f'{key} = "{value}"')
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    print(path)
    return 0


def _config_path(root: Path, scope: str) -> Path:
    if scope == "local":
        return root / ".codex/repo-decisions.toml"
    override = os.environ.get("REPO_DECISIONS_GLOBAL_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path("~/.codex/repo-decisions/config.toml").expanduser()


def _split_assignment(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(f"Expected key=value: {value}")
    key, raw = value.split("=", 1)
    return key.strip(), raw.strip().strip('"').strip("'")


def _codex(root: Path, args: argparse.Namespace) -> int:
    prompt_parts = list(args.prompt)
    if prompt_parts and prompt_parts[0] == "--":
        prompt_parts = prompt_parts[1:]
    user_prompt = " ".join(prompt_parts).strip()
    if not user_prompt and not sys.stdin.isatty():
        user_prompt = sys.stdin.read().strip()
    if not user_prompt:
        print("repo-decisions codex requires a prompt or stdin", file=sys.stderr)
        return 2

    enriched = compose_codex_prompt(root, user_prompt)
    if args.print_prompt:
        print(enriched)
        return 0

    codex_args = list(args.codex_arg)
    if "--cd" not in codex_args and "-C" not in codex_args:
        codex_args.extend(["--cd", str(root)])
    command = [args.codex_bin, "exec", *codex_args, enriched]
    return subprocess.call(command)


def compose_codex_prompt(root: Path, user_prompt: str) -> str:
    brief = build_brief(root).strip()
    if not brief:
        return user_prompt
    return f"{brief}\n\n---\n\n{user_prompt}"
