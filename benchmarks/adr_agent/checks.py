from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_CASES = ROOT / "cases.toml"


@dataclass(frozen=True)
class Case:
    id: str
    fixture: str
    task: str
    required_globs: tuple[str, ...] = ()
    required_patterns: tuple[str, ...] = ()
    forbidden_patterns: tuple[str, ...] = ()
    verify_commands: tuple[str, ...] = ()
    requires_debug_write: bool = False

    @property
    def fixture_dir(self) -> Path:
        return ROOT / "fixtures" / self.fixture


@dataclass
class CheckReport:
    case_id: str
    mode: str
    failures: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    changed_adr_files: list[str] = field(default_factory=list)
    debug_events: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.failures

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "mode": self.mode,
            "ok": self.ok,
            "failures": self.failures,
            "changed_files": self.changed_files,
            "changed_adr_files": self.changed_adr_files,
            "debug_events": self.debug_events,
        }


def load_cases(path: Path = DEFAULT_CASES) -> dict[str, Case]:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    cases = {}
    for item in data.get("cases", []):
        case = Case(
            id=str(item["id"]),
            fixture=str(item["fixture"]),
            task=str(item["task"]).strip() + "\n",
            required_globs=tuple(item.get("required_globs", [])),
            required_patterns=tuple(item.get("required_patterns", [])),
            forbidden_patterns=tuple(item.get("forbidden_patterns", [])),
            verify_commands=tuple(item.get("verify_commands", [])),
            requires_debug_write=bool(item.get("requires_debug_write", False)),
        )
        cases[case.id] = case
    return cases


def check_case(
    case: Case,
    workspace: Path,
    debug_log: Path | None = None,
    *,
    baseline: Path | None = None,
    mode: str = "d0",
) -> CheckReport:
    debug_events = _debug_event_counts(debug_log)
    changed_files = _changed_files(baseline, workspace) if baseline else []
    changed_adr_files = _changed_adr_files(workspace, changed_files)
    report = CheckReport(case.id, mode, [], changed_files, changed_adr_files, debug_events)
    for pattern in case.required_globs:
        if not list(workspace.glob(pattern)):
            report.failures.append(f"missing required glob: {pattern}")

    for spec in case.required_patterns:
        glob, regex = _split_pattern_spec(spec)
        if not _any_match(workspace, glob, regex):
            report.failures.append(f"missing required pattern: {spec}")

    for spec in case.forbidden_patterns:
        glob, regex = _split_pattern_spec(spec)
        if _any_match(workspace, glob, regex):
            report.failures.append(f"forbidden pattern matched: {spec}")

    if case.requires_debug_write and changed_adr_files and debug_events.get("write", 0) == 0:
        report.failures.append("missing repo-decisions write event in debug log")
    if mode == "d2" and changed_adr_files and debug_events.get("mcp-tool-call", 0) == 0:
        report.failures.append("missing repo-decisions mcp-tool-call event in debug log")

    return report


def _split_pattern_spec(spec: str) -> tuple[str, str]:
    if "::" not in spec:
        raise ValueError(f"Expected '<glob>::<regex>': {spec}")
    glob, regex = spec.split("::", 1)
    return glob, regex


def _any_match(workspace: Path, glob: str, regex: str) -> bool:
    compiled = re.compile(regex, re.MULTILINE | re.DOTALL)
    for path in workspace.glob(glob):
        if path.is_file() and compiled.search(path.read_text(encoding="utf-8")):
            return True
    return False


def _debug_event_counts(debug_log: Path | None) -> dict[str, int]:
    counts: dict[str, int] = {}
    if debug_log is None or not debug_log.exists():
        return counts
    for line in debug_log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("component") != "repo-decisions":
            continue
        event_name = str(event.get("event") or "")
        counts[event_name] = counts.get(event_name, 0) + 1
    return counts


def _changed_files(baseline: Path | None, workspace: Path) -> list[str]:
    if baseline is None:
        return []
    baseline_files = _file_map(baseline)
    workspace_files = _file_map(workspace)
    changed = []
    for rel_path in sorted(set(baseline_files) | set(workspace_files)):
        if baseline_files.get(rel_path) != workspace_files.get(rel_path):
            changed.append(rel_path)
    return changed


def _file_map(root: Path) -> dict[str, bytes]:
    files = {}
    for path in root.rglob("*"):
        if path.is_file():
            files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files


def _changed_adr_files(workspace: Path, changed_files: list[str]) -> list[str]:
    adr_dirs = []
    for path in workspace.rglob("*.md"):
        rel_parts = path.relative_to(workspace).parts
        if any(part.lower() in {"adr", "adrs", "decisions"} for part in rel_parts[:-1]):
            adr_dirs.append(path.parent.relative_to(workspace).as_posix())
    return [
        rel_path
        for rel_path in changed_files
        if rel_path.endswith(".md")
        and (
            any(part.lower() in {"adr", "adrs", "decisions"} for part in Path(rel_path).parts[:-1])
            or any(rel_path == adr_dir or rel_path.startswith(f"{adr_dir}/") for adr_dir in adr_dirs)
        )
    ]
