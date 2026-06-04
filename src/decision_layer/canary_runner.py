from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from decision_layer.patch_verifier import PatchVerificationResult, verify_patch

DEFAULT_OPENCODE_MODEL = "llama.cpp/qwen36-35b-a3b-udiq3s"
BLOCKED_COMMANDS = (
    "apt",
    "apt-get",
    "brew",
    "curl",
    "npm",
    "pip",
    "pip3",
    "pipx",
    "pkexec",
    "sudo",
    "uv",
    "virtualenv",
)
PYTHON_COMMANDS = ("python", "python3", "python3.11", "python3.12", "python3.13", "python3.14")
BLOCKED_OUTPUT_RE = re.compile(
    r"blocked (?:git subcommand|command|python module)|permission requested|auto-rejecting",
    re.IGNORECASE,
)
FORBIDDEN_COMMAND_RE = re.compile(
    r"(?:^|[;&|]\s*)(?:\S*/)?git\b(?=[^;&|]*\b(?:log|show|blame)\b)"
    r"|(?:^|[;&|]\s*)(?:sudo\s+)?"
    r"(?:\S*/)?(?:apt|apt-get|brew|curl|npm|pip|pip3|pipx|pkexec|uv|virtualenv)\b"
    r"|(?:^|[;&|]\s*)(?:\S*/)?python(?:3(?:\.\d+)?)?\s+-m\s+"
    r"(?:ensurepip|pip|venv|virtualenv)\b",
    re.IGNORECASE,
)
SUBAGENT_EVENT_RE = re.compile(r'"(?:tool|name)"\s*:\s*"task"|"subagent"', re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class CanaryRunConfig:
    workspace: Path
    prompt_path: Path
    guard_bin: Path
    log_path: Path
    stderr_path: Path
    time_path: Path
    patch_path: Path
    model: str = DEFAULT_OPENCODE_MODEL
    timeout_seconds: float = 600.0
    opencode_bin: str = "opencode"
    verifier_json_path: Path | None = None
    audit_json_path: Path | None = None
    progress_path: Path | None = None
    required_terms: tuple[str, ...] = ()
    required_files: tuple[str, ...] = ()
    allowed_files: tuple[str, ...] = ()
    extra_env: dict[str, str] | None = None
    fail_on_dirty_audit: bool = False


@dataclass(frozen=True, slots=True)
class CanaryLogAudit:
    command_count: int
    forbidden_command_count: int
    forbidden_command_examples: tuple[str, ...]
    blocked_output_count: int
    blocked_output_examples: tuple[str, ...]
    error_count: int
    error_examples: tuple[str, ...]
    subagent_mentions: int
    malformed_log_lines: int

    @property
    def is_dirty(self) -> bool:
        return any(
            (
                self.forbidden_command_count,
                self.blocked_output_count,
                self.error_count,
                self.malformed_log_lines,
            )
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "is_dirty": self.is_dirty,
            "command_count": self.command_count,
            "forbidden_command_count": self.forbidden_command_count,
            "forbidden_command_examples": list(self.forbidden_command_examples),
            "blocked_output_count": self.blocked_output_count,
            "blocked_output_examples": list(self.blocked_output_examples),
            "error_count": self.error_count,
            "error_examples": list(self.error_examples),
            "subagent_mentions": self.subagent_mentions,
            "malformed_log_lines": self.malformed_log_lines,
        }


@dataclass(frozen=True, slots=True)
class CanaryRunResult:
    exit_status: str
    elapsed_seconds: float
    timed_out: bool
    log_lines: int
    stderr_bytes: int
    patch_chars: int
    verifier: PatchVerificationResult | None = None
    audit: CanaryLogAudit | None = None
    fail_on_dirty_audit: bool = False

    @property
    def ok(self) -> bool:
        if self.timed_out:
            return False
        if self.exit_status != "0":
            return False
        if self.fail_on_dirty_audit and self.audit is not None and self.audit.is_dirty:
            return False
        return self.verifier is None or self.verifier.ok

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "ok": self.ok,
            "exit_status": self.exit_status,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "timed_out": self.timed_out,
            "log_lines": self.log_lines,
            "stderr_bytes": self.stderr_bytes,
            "patch_chars": self.patch_chars,
            "fail_on_dirty_audit": self.fail_on_dirty_audit,
        }
        if self.verifier is not None:
            data["verifier"] = self.verifier.to_dict()
        if self.audit is not None:
            data["audit"] = self.audit.to_dict()
        return data


def run_opencode_canary(config: CanaryRunConfig) -> CanaryRunResult:
    workspace = config.workspace.resolve()
    prompt_path = config.prompt_path.resolve()
    ensure_canary_guard_bin(config.guard_bin)
    config.log_path.parent.mkdir(parents=True, exist_ok=True)
    config.stderr_path.parent.mkdir(parents=True, exist_ok=True)
    config.time_path.parent.mkdir(parents=True, exist_ok=True)
    config.patch_path.parent.mkdir(parents=True, exist_ok=True)
    if config.verifier_json_path is not None:
        config.verifier_json_path.parent.mkdir(parents=True, exist_ok=True)
    if config.audit_json_path is not None:
        config.audit_json_path.parent.mkdir(parents=True, exist_ok=True)
    reset_progress_log(config.progress_path)

    prompt = prompt_path.read_text(encoding="utf-8")
    env = build_guarded_env(config.guard_bin, config.extra_env)
    command = [
        config.opencode_bin,
        "run",
        "--dir",
        str(workspace),
        "--dangerously-skip-permissions",
        "--format",
        "json",
        "--model",
        config.model,
        prompt,
    ]

    emit_progress(
        config.progress_path,
        "started",
        workspace=str(workspace),
        prompt=str(prompt_path),
        log=str(config.log_path),
        stderr=str(config.stderr_path),
        model=config.model,
        timeout_seconds=config.timeout_seconds,
    )
    start = time.perf_counter()
    exit_status = "0"
    timed_out = False
    with (
        config.log_path.open("w", encoding="utf-8") as stdout,
        config.stderr_path.open("w", encoding="utf-8") as stderr,
    ):
        try:
            completed = subprocess.run(
                command,
                cwd=workspace,
                env=env,
                stdout=stdout,
                stderr=stderr,
                timeout=config.timeout_seconds,
                check=False,
            )
            exit_status = str(completed.returncode)
        except subprocess.TimeoutExpired:
            exit_status = "timeout"
            timed_out = True
    elapsed_seconds = time.perf_counter() - start
    emit_progress(
        config.progress_path,
        "opencode_finished",
        exit_status=exit_status,
        elapsed_seconds=round(elapsed_seconds, 2),
        timed_out=timed_out,
    )

    patch_text = read_workspace_diff(workspace, env)
    config.patch_path.write_text(patch_text, encoding="utf-8")
    emit_progress(
        config.progress_path,
        "patch_saved",
        patch=str(config.patch_path),
        patch_chars=len(patch_text),
    )
    verifier = maybe_verify_patch(config, patch_text)
    if verifier is not None:
        emit_progress(
            config.progress_path,
            "verifier_finished",
            verifier_ok=verifier.ok,
            verifier_json=str(config.verifier_json_path) if config.verifier_json_path else None,
        )
    audit = audit_opencode_log(config.log_path)
    if config.audit_json_path is not None:
        config.audit_json_path.write_text(
            json.dumps(audit.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    emit_progress(
        config.progress_path,
        "audit_finished",
        audit_json=str(config.audit_json_path) if config.audit_json_path else None,
        forbidden_command_count=audit.forbidden_command_count,
        blocked_output_count=audit.blocked_output_count,
        error_count=audit.error_count,
        subagent_mentions=audit.subagent_mentions,
    )
    config.time_path.write_text(
        f"elapsed_seconds={elapsed_seconds:.2f}\nexit_status={exit_status}\n",
        encoding="utf-8",
    )
    result = CanaryRunResult(
        exit_status=exit_status,
        elapsed_seconds=elapsed_seconds,
        timed_out=timed_out,
        log_lines=count_lines(config.log_path),
        stderr_bytes=config.stderr_path.stat().st_size if config.stderr_path.exists() else 0,
        patch_chars=len(patch_text),
        verifier=verifier,
        audit=audit,
        fail_on_dirty_audit=config.fail_on_dirty_audit,
    )
    emit_progress(
        config.progress_path,
        "finished",
        ok=result.ok,
        elapsed_seconds=round(result.elapsed_seconds, 2),
        patch_chars=result.patch_chars,
    )
    return result


def ensure_canary_guard_bin(guard_bin: Path) -> None:
    guard_bin.mkdir(parents=True, exist_ok=True)
    for command in BLOCKED_COMMANDS:
        write_blocked_command(guard_bin / command, command)
    search_path = path_without_guard_bin(guard_bin)
    git_path = shutil.which("git", path=search_path)
    if git_path is not None:
        write_git_guard(guard_bin / "git", git_path)
    for command in PYTHON_COMMANDS:
        command_path = shutil.which(command, path=search_path)
        if command_path is not None:
            write_python_guard(guard_bin / command, command_path)


def path_without_guard_bin(guard_bin: Path) -> str:
    guard = str(guard_bin.resolve())
    entries = [
        entry
        for entry in os.environ.get("PATH", "").split(os.pathsep)
        if entry and str(Path(entry).resolve()) != guard
    ]
    return os.pathsep.join(entries)


def write_blocked_command(path: Path, command: str) -> None:
    write_executable(
        path,
        f"""#!/usr/bin/env sh
echo "blocked command: {command}" >&2
exit 127
""",
    )


def write_git_guard(path: Path, git_path: str) -> None:
    write_executable(
        path,
        f"""#!/usr/bin/env sh
for arg in "$@"; do
  case "$arg" in
    log|show|blame)
      echo "blocked git subcommand: $arg" >&2
      exit 127
      ;;
  esac
done
exec {git_path} "$@"
""",
    )


def write_python_guard(path: Path, python_path: str) -> None:
    write_executable(
        path,
        f"""#!/usr/bin/env sh
previous=""
for arg in "$@"; do
  if [ "$previous" = "-m" ]; then
    case "$arg" in
      ensurepip|pip|venv|virtualenv)
        echo "blocked python module: $arg" >&2
        exit 127
        ;;
    esac
  fi
  previous="$arg"
done
exec {python_path} "$@"
""",
    )


def write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def build_guarded_env(guard_bin: Path, extra_env: dict[str, str] | None) -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = str(guard_bin.resolve()) + os.pathsep + env["PATH"]
    env["PIP_REQUIRE_VIRTUALENV"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    if extra_env:
        env.update(extra_env)
    return env


def read_workspace_diff(workspace: Path, env: dict[str, str]) -> str:
    completed = subprocess.run(
        ["git", "-C", str(workspace), "diff"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout


def maybe_verify_patch(config: CanaryRunConfig, patch_text: str) -> PatchVerificationResult | None:
    should_verify = bool(config.required_terms or config.required_files or config.allowed_files)
    if not should_verify:
        return None
    verifier = verify_patch(
        patch_text,
        required_terms=config.required_terms,
        required_files=config.required_files,
        allowed_files=config.allowed_files,
    )
    if config.verifier_json_path is not None:
        config.verifier_json_path.write_text(
            json.dumps(verifier.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return verifier


def audit_opencode_log(log_path: Path) -> CanaryLogAudit:
    command_count = 0
    forbidden_command_count = 0
    forbidden_command_examples: list[str] = []
    blocked_output_count = 0
    blocked_output_examples: list[str] = []
    error_count = 0
    error_examples: list[str] = []
    subagent_mentions = 0
    malformed_log_lines = 0

    if not log_path.exists():
        return CanaryLogAudit(0, 0, (), 0, (), 0, (), 0, 0)

    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            malformed_log_lines += 1
            if BLOCKED_OUTPUT_RE.search(line):
                blocked_output_count += 1
                append_example(blocked_output_examples, line)
            continue

        event_text = json.dumps(event, ensure_ascii=False)
        if SUBAGENT_EVENT_RE.search(event_text):
            subagent_mentions += 1

        state = event_state(event)
        command = event_command(state)
        if command is not None:
            command_count += 1
            if FORBIDDEN_COMMAND_RE.search(command):
                forbidden_command_count += 1
                append_example(forbidden_command_examples, command)

        output = state.get("output")
        if isinstance(output, str) and BLOCKED_OUTPUT_RE.search(output):
            blocked_output_count += 1
            append_example(blocked_output_examples, output)

        error = state.get("error")
        if isinstance(error, str) and error:
            error_count += 1
            append_example(error_examples, error)

    return CanaryLogAudit(
        command_count=command_count,
        forbidden_command_count=forbidden_command_count,
        forbidden_command_examples=tuple(forbidden_command_examples),
        blocked_output_count=blocked_output_count,
        blocked_output_examples=tuple(blocked_output_examples),
        error_count=error_count,
        error_examples=tuple(error_examples),
        subagent_mentions=subagent_mentions,
        malformed_log_lines=malformed_log_lines,
    )


def event_state(event: object) -> dict[str, object]:
    if not isinstance(event, dict):
        return {}
    part = event.get("part")
    if not isinstance(part, dict):
        return {}
    state = part.get("state")
    if not isinstance(state, dict):
        return {}
    return state


def event_command(state: dict[str, object]) -> str | None:
    raw_input = state.get("input")
    if not isinstance(raw_input, dict):
        return None
    command = raw_input.get("command") or raw_input.get("cmd")
    return command if isinstance(command, str) else None


def append_example(examples: list[str], value: str, *, limit: int = 8) -> None:
    if len(examples) >= limit:
        return
    normalized = " ".join(value.split())
    examples.append(normalized[:240])


def reset_progress_log(progress_path: Path | None) -> None:
    if progress_path is None:
        return
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text("", encoding="utf-8")


def emit_progress(progress_path: Path | None, event: str, **fields: object) -> None:
    payload: dict[str, object] = {
        "event": event,
        "time_unix": round(time.time(), 3),
    }
    payload.update({key: value for key, value in fields.items() if value is not None})
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    print(f"[canary] {line}", file=sys.stderr, flush=True)
    if progress_path is not None:
        with progress_path.open("a", encoding="utf-8") as file:
            file.write(line + "\n")


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as file:
        return sum(1 for _ in file)
