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
    failures: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    def to_dict(self) -> dict[str, Any]:
        return {"case_id": self.case_id, "ok": self.ok, "failures": self.failures}


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


def check_case(case: Case, workspace: Path, debug_log: Path | None = None) -> CheckReport:
    report = CheckReport(case.id)
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

    if case.requires_debug_write and not _has_debug_write(debug_log):
        report.failures.append("missing repo-decisions write event in debug log")

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


def _has_debug_write(debug_log: Path | None) -> bool:
    if debug_log is None or not debug_log.exists():
        return False
    for line in debug_log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("component") == "repo-decisions" and event.get("event") == "write":
            return True
    return False
