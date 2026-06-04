from __future__ import annotations

import os
import shutil
import subprocess
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
    required_terms: tuple[str, ...] = ()
    required_files: tuple[str, ...] = ()
    allowed_files: tuple[str, ...] = ()
    extra_env: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class CanaryRunResult:
    exit_status: str
    elapsed_seconds: float
    timed_out: bool
    log_lines: int
    stderr_bytes: int
    patch_chars: int
    verifier: PatchVerificationResult | None = None

    @property
    def ok(self) -> bool:
        if self.timed_out:
            return False
        if self.exit_status != "0":
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
        }
        if self.verifier is not None:
            data["verifier"] = self.verifier.to_dict()
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

    patch_text = read_workspace_diff(workspace, env)
    config.patch_path.write_text(patch_text, encoding="utf-8")
    verifier = maybe_verify_patch(config, patch_text)
    config.time_path.write_text(
        f"elapsed_seconds={elapsed_seconds:.2f}\nexit_status={exit_status}\n",
        encoding="utf-8",
    )
    return CanaryRunResult(
        exit_status=exit_status,
        elapsed_seconds=elapsed_seconds,
        timed_out=timed_out,
        log_lines=count_lines(config.log_path),
        stderr_bytes=config.stderr_path.stat().st_size if config.stderr_path.exists() else 0,
        patch_chars=len(patch_text),
        verifier=verifier,
    )


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
        import json

        config.verifier_json_path.write_text(
            json.dumps(verifier.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return verifier


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as file:
        return sum(1 for _ in file)
