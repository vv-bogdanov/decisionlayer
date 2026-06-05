from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from benchmarks.adr_agent.checks import DEFAULT_CASES, Case, check_case, load_cases
from repo_decisions.core import build_brief


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
DEFAULT_RESULTS = ROOT / "runs"
MODES = ("d0", "d1", "d2")
RUNTIME_ARTIFACT_DIRS = ("__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache")
RUNTIME_ARTIFACT_FILES = (".coverage",)
D2_TOOL_GUIDANCE = """\
# Repo Decisions Tool Requirement

Use the repo-decisions MCP tools for ADR operations:

- Inspect accepted requirements with `adr_build_brief` when needed.
- Add new ADRs with `adr_add_decision`.
- Change accepted ADRs only with `adr_supersede_decision`.
- Do not edit accepted ADR files directly.

If this runner does not expose MCP tools, use the CLI path from
`REPO_DECISIONS_CLI` instead:

- `$REPO_DECISIONS_CLI --root . brief`
- `$REPO_DECISIONS_CLI --root . add ...`
- `$REPO_DECISIONS_CLI --root . supersede ...`
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adr-agent-run-case")
    parser.add_argument("case_id")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--run-id")
    parser.add_argument("--mode", choices=MODES, default="d0")
    parser.add_argument(
        "--agent-command",
        help="Shell command. May use {workspace}, {prompt_file}, and {debug_log}.",
    )
    parser.add_argument("--run-verify", action="store_true")
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    if args.case_id not in cases:
        print(f"Unknown case: {args.case_id}", file=sys.stderr)
        return 2
    case = cases[args.case_id]
    result_dir = _new_result_dir(args.results_dir, case, args.mode, args.run_id)
    baseline = result_dir / "baseline"
    workspace = result_dir / "workspace"
    prompt_file = result_dir / "prompt.md"
    effective_prompt_file = result_dir / "effective-prompt.md"
    debug_log = result_dir / "repo-decisions-debug.jsonl"
    shutil.copytree(case.fixture_dir, baseline)
    shutil.copytree(case.fixture_dir, workspace)
    prompt_file.write_text(case.task, encoding="utf-8")
    initial_brief = build_brief(workspace)
    effective_prompt_file.write_text(
        compose_effective_prompt(case.task, initial_brief, args.mode),
        encoding="utf-8",
    )

    result: dict[str, Any] = {
        "case_id": case.id,
        "mode": args.mode,
        "workspace": str(workspace),
        "prompt_file": str(prompt_file),
        "effective_prompt_file": str(effective_prompt_file),
        "debug_log": str(debug_log),
        "initial_brief": initial_brief,
        "metrics": {
            "prompt_chars": len(effective_prompt_file.read_text(encoding="utf-8")),
            "initial_brief_chars": len(initial_brief),
        },
        "status": "prepared",
    }

    if args.agent_command:
        result.update(_run_agent(case, args.mode, args.agent_command, workspace, prompt_file, effective_prompt_file, debug_log))
        _clean_runtime_artifacts(workspace)
        result["final_brief"] = build_brief(workspace)
        result["diff"] = _run_diff(baseline, workspace)
        report = check_case(
            case,
            workspace,
            debug_log,
            baseline=baseline,
            mode=args.mode,
            agent_stdout=result["agent"]["stdout"],
        )
        result["checks"] = report.to_dict()
        result["metrics"].update(
            {
                "duration_sec": result["agent"]["duration_sec"],
                "diff_size": len(result["diff"]["stdout"]),
                "changed_files": len(report.changed_files),
                "changed_adr_files": len(report.changed_adr_files),
                "tool_calls": report.debug_events.get("mcp-tool-call", 0) + report.debug_events.get("cli-command", 0),
                "write_events": report.debug_events.get("write", 0),
            }
        )
        if report.ok and args.run_verify:
            result["verify"] = _run_verify(case, workspace)
        result["status"] = "passed" if _result_ok(result) else "failed"

    (result_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"workspace: {workspace}")
    print(f"prompt: {prompt_file}")
    print(f"result: {result_dir / 'result.json'}")
    return 0 if result["status"] in {"prepared", "passed"} else 1


def compose_effective_prompt(task: str, brief: str, mode: str) -> str:
    task = task.strip() + "\n"
    if mode == "d0" or not brief:
        return task
    parts = [brief.strip(), "# Task", task.strip()]
    if mode == "d2":
        parts.insert(1, D2_TOOL_GUIDANCE.strip())
    return "\n\n".join(parts).strip() + "\n"


def new_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _new_result_dir(results_dir: Path, case: Case, mode: str, run_id: str | None = None) -> Path:
    run_id = run_id or new_run_id()
    path = results_dir / run_id / case.id / mode
    path.mkdir(parents=True, exist_ok=False)
    return path


def _run_agent(
    case: Case,
    mode: str,
    command_template: str,
    workspace: Path,
    prompt_file: Path,
    effective_prompt_file: Path,
    debug_log: Path,
) -> dict[str, Any]:
    command = command_template.format(
        workspace=_shell_quote(workspace),
        prompt_file=_shell_quote(prompt_file),
        effective_prompt_file=_shell_quote(effective_prompt_file),
        debug_log=_shell_quote(debug_log),
        repo_root=_shell_quote(REPO_ROOT),
        mode=mode,
    )
    env = os.environ.copy()
    env["REPO_DECISIONS_DEBUG_LOG"] = str(debug_log)
    env["REPO_DECISIONS_RUN_ID"] = case.id
    env["REPO_DECISIONS_CLI"] = str(REPO_ROOT / "scripts/repo-decisions")
    env["ADR_AGENT_MODE"] = mode
    env["GIT_CEILING_DIRECTORIES"] = str(workspace.parent)
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=workspace,
        env=env,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=None,
        check=False,
    )
    return {
        "agent": {
            "command": command,
            "returncode": completed.returncode,
            "duration_sec": round(time.monotonic() - started, 3),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    }


def _run_verify(case: Case, workspace: Path) -> list[dict[str, Any]]:
    results = []
    for command in case.verify_commands:
        started = time.monotonic()
        completed = subprocess.run(
            command,
            cwd=workspace,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        results.append(
            {
                "command": command,
                "returncode": completed.returncode,
                "duration_sec": round(time.monotonic() - started, 3),
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
    return results


def _run_diff(baseline: Path, workspace: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["git", "diff", "--no-index", "--", str(baseline), str(workspace)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _clean_runtime_artifacts(root: Path) -> None:
    for dirname in RUNTIME_ARTIFACT_DIRS:
        for path in sorted(root.rglob(dirname), reverse=True):
            if path.is_dir():
                shutil.rmtree(path)
    for path in root.rglob("*.py[co]"):
        if path.is_file():
            path.unlink()
    for filename in RUNTIME_ARTIFACT_FILES:
        for path in root.rglob(filename):
            if path.is_file():
                path.unlink()


def _result_ok(result: dict[str, Any]) -> bool:
    agent = result.get("agent", {})
    checks = result.get("checks", {})
    verify = result.get("verify", [])
    return (
        agent.get("returncode") == 0
        and checks.get("ok") is True
        and all(item.get("returncode") == 0 for item in verify)
    )


def _shell_quote(path: Path) -> str:
    return "'" + str(path).replace("'", "'\"'\"'") + "'"


if __name__ == "__main__":
    raise SystemExit(main())
