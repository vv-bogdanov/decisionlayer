from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from decision_layer.canary_runner import (
    CanaryRunConfig,
    ensure_canary_guard_bin,
    run_opencode_canary,
)
from decision_layer.cli import main


def test_guard_blocks_git_history_after_options(tmp_path: Path) -> None:
    workspace = init_git_workspace(tmp_path / "workspace")
    guard_bin = tmp_path / "guard-bin"
    ensure_canary_guard_bin(guard_bin)

    env = os.environ.copy()
    env["PATH"] = str(guard_bin) + os.pathsep + env["PATH"]
    result = subprocess.run(
        ["git", "-C", str(workspace), "log"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 127
    assert "blocked git subcommand: log" in result.stderr


def test_guard_blocks_python_venv_and_pip_modules(tmp_path: Path) -> None:
    guard_bin = tmp_path / "guard-bin"
    ensure_canary_guard_bin(guard_bin)
    env = os.environ.copy()
    env["PATH"] = str(guard_bin) + os.pathsep + env["PATH"]

    for module in ("venv", "pip"):
        result = subprocess.run(
            ["python3", "-m", module],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 127
        assert f"blocked python module: {module}" in result.stderr


def test_guard_generation_ignores_existing_guard_path(
    tmp_path: Path,
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    guard_bin = tmp_path / "guard-bin"
    ensure_canary_guard_bin(guard_bin)
    monkeypatch.setenv("PATH", str(guard_bin) + os.pathsep + os.environ["PATH"])

    ensure_canary_guard_bin(guard_bin)
    result = subprocess.run(
        ["python3", "-c", "print('ok')"],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "ok"


def test_run_opencode_canary_writes_artifacts_and_uses_dir(tmp_path: Path) -> None:
    workspace = init_git_workspace(tmp_path / "workspace")
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("Fix the file.", encoding="utf-8")
    args_path = tmp_path / "opencode.args"
    fake_opencode = write_fake_opencode(tmp_path / "opencode", args_path)

    result = run_opencode_canary(
        CanaryRunConfig(
            workspace=workspace,
            prompt_path=prompt_path,
            guard_bin=tmp_path / "guard-bin",
            log_path=tmp_path / "logs" / "run.jsonl",
            stderr_path=tmp_path / "logs" / "run.stderr",
            time_path=tmp_path / "logs" / "run.time",
            patch_path=tmp_path / "patches" / "run.patch",
            verifier_json_path=tmp_path / "logs" / "verifier.json",
            audit_json_path=tmp_path / "logs" / "audit.json",
            progress_path=tmp_path / "logs" / "progress.jsonl",
            opencode_bin=str(fake_opencode),
            timeout_seconds=5,
            required_terms=("changed",),
            required_files=("target.txt",),
            allowed_files=("target.txt",),
        )
    )

    assert result.ok is True
    args = args_path.read_text(encoding="utf-8")
    assert f"--dir\n{workspace.resolve()}" in args
    assert "--dangerously-skip-permissions" in args
    assert json.loads((tmp_path / "logs" / "verifier.json").read_text(encoding="utf-8"))["ok"]
    audit = json.loads((tmp_path / "logs" / "audit.json").read_text(encoding="utf-8"))
    assert audit["forbidden_command_count"] == 1
    assert audit["blocked_output_count"] == 1
    progress = (tmp_path / "logs" / "progress.jsonl").read_text(encoding="utf-8")
    assert '"event": "started"' in progress
    assert '"event": "finished"' in progress
    assert result.audit is not None
    assert result.audit.forbidden_command_count == 1
    assert "changed" in (tmp_path / "patches" / "run.patch").read_text(encoding="utf-8")
    assert "exit_status=0" in (tmp_path / "logs" / "run.time").read_text(encoding="utf-8")


def test_run_opencode_canary_can_fail_on_dirty_audit(tmp_path: Path) -> None:
    workspace = init_git_workspace(tmp_path / "workspace")
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("Fix the file.", encoding="utf-8")
    fake_opencode = write_fake_opencode(tmp_path / "opencode", tmp_path / "opencode.args")

    result = run_opencode_canary(
        CanaryRunConfig(
            workspace=workspace,
            prompt_path=prompt_path,
            guard_bin=tmp_path / "guard-bin",
            log_path=tmp_path / "logs" / "run.jsonl",
            stderr_path=tmp_path / "logs" / "run.stderr",
            time_path=tmp_path / "logs" / "run.time",
            patch_path=tmp_path / "patches" / "run.patch",
            opencode_bin=str(fake_opencode),
            timeout_seconds=5,
            fail_on_dirty_audit=True,
        )
    )

    assert result.audit is not None
    assert result.audit.is_dirty is True
    assert result.ok is False


def test_run_opencode_canary_writes_soft_verifier_json(tmp_path: Path) -> None:
    workspace = init_git_workspace(tmp_path / "workspace")
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("Fix the file.", encoding="utf-8")
    fake_opencode = write_fake_opencode(tmp_path / "opencode", tmp_path / "opencode.args")

    result = run_opencode_canary(
        CanaryRunConfig(
            workspace=workspace,
            prompt_path=prompt_path,
            guard_bin=tmp_path / "guard-bin",
            log_path=tmp_path / "logs" / "run.jsonl",
            stderr_path=tmp_path / "logs" / "run.stderr",
            time_path=tmp_path / "logs" / "run.time",
            patch_path=tmp_path / "patches" / "run.patch",
            verifier_json_path=tmp_path / "logs" / "verifier.json",
            opencode_bin=str(fake_opencode),
            timeout_seconds=5,
        )
    )

    verifier = json.loads((tmp_path / "logs" / "verifier.json").read_text(encoding="utf-8"))
    assert result.verifier is not None
    assert verifier["ok"] is True
    assert verifier["touched_files"] == ["target.txt"]


def test_run_opencode_canary_writes_timeout_marker(tmp_path: Path) -> None:
    workspace = init_git_workspace(tmp_path / "workspace")
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("Fix the file.", encoding="utf-8")
    fake_opencode = tmp_path / "opencode"
    fake_opencode.write_text(
        f"#!{sys.executable}\nimport time\ntime.sleep(2)\n",
        encoding="utf-8",
    )
    fake_opencode.chmod(0o755)

    result = run_opencode_canary(
        CanaryRunConfig(
            workspace=workspace,
            prompt_path=prompt_path,
            guard_bin=tmp_path / "guard-bin",
            log_path=tmp_path / "logs" / "run.jsonl",
            stderr_path=tmp_path / "logs" / "run.stderr",
            time_path=tmp_path / "logs" / "run.time",
            patch_path=tmp_path / "patches" / "run.patch",
            opencode_bin=str(fake_opencode),
            timeout_seconds=0.1,
        )
    )

    assert result.timed_out is True
    assert result.ok is False
    assert "exit_status=timeout" in (tmp_path / "logs" / "run.time").read_text(encoding="utf-8")


def test_cli_run_opencode_canary_returns_nonzero_on_verifier_fail(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    workspace = init_git_workspace(tmp_path / "workspace")
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("Fix the file.", encoding="utf-8")
    fake_opencode = write_fake_opencode(tmp_path / "opencode", tmp_path / "opencode.args")

    exit_code = main(
        [
            "run-opencode-canary",
            "--workspace",
            str(workspace),
            "--prompt",
            str(prompt_path),
            "--guard-bin",
            str(tmp_path / "guard-bin"),
            "--log",
            str(tmp_path / "logs" / "run.jsonl"),
            "--stderr",
            str(tmp_path / "logs" / "run.stderr"),
            "--time",
            str(tmp_path / "logs" / "run.time"),
            "--patch",
            str(tmp_path / "patches" / "run.patch"),
            "--opencode-bin",
            str(fake_opencode),
            "--require-term",
            "missing-term",
            "--allow-file",
            "target.txt",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert output["ok"] is False
    assert output["verifier"]["missing_required_terms"] == ["missing-term"]


def init_git_workspace(path: Path) -> Path:
    path.mkdir()
    subprocess.run(["git", "-C", str(path), "init"], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test User"], check=True)
    (path / "target.txt").write_text("original\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", "initial"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return path


def write_fake_opencode(path: Path, args_path: Path) -> Path:
    path.write_text(
        f"#!{sys.executable}\n"
        "from pathlib import Path\n"
        "import json\n"
        "import sys\n"
        f"Path({str(args_path)!r}).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')\n"
        "workspace = Path(sys.argv[sys.argv.index('--dir') + 1])\n"
        "(workspace / 'target.txt').write_text('changed\\n', encoding='utf-8')\n"
        "print(json.dumps({'type': 'text', 'part': {'text': 'done'}}))\n"
        "print(json.dumps({'type': 'tool', 'part': {'state': {'input': "
        "{'command': 'python3 -m pip install pytest'}, "
        "'output': 'blocked python module: pip'}}}))\n",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path
