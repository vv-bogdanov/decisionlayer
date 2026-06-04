from __future__ import annotations

import importlib.machinery
import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType, SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER = PROJECT_ROOT / "scripts" / "run-swe-contextbench-mini-slice"


def load_runner() -> ModuleType:
    loader = importlib.machinery.SourceFileLoader(
        "run_swe_contextbench_mini_slice",
        str(RUNNER),
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_d1ga_prompt_adds_application_guard(tmp_path: Path) -> None:
    runner = load_runner()
    pair = {
        "expected_reusable_decision": "Keep opclasses and suffixes separated by spaces.",
        "d1_applicability": "apply",
    }
    related = {
        "repo": "django/django",
        "problem_statement": "Descending opclass indexes render invalid SQL.",
        "hints_text": "",
    }

    guarded = runner.render_task_prompt(pair, related, tmp_path, "D1GA")
    plain = runner.render_task_prompt(pair, related, tmp_path, "D1G")

    assert "Decision application guard:" in guarded
    assert "concrete failing behavior and source area" in guarded
    assert "- Keep opclasses and suffixes separated by spaces." in guarded
    assert "Decision application guard:" not in plain


def test_d1ga_prompt_respects_applicability_gate(tmp_path: Path) -> None:
    runner = load_runner()
    pair = {
        "expected_reusable_decision": "Keep opclasses and suffixes separated by spaces.",
        "d1_applicability": "skip",
    }
    related = {
        "repo": "django/django",
        "problem_statement": "Different issue.",
        "hints_text": "",
    }

    prompt = runner.render_task_prompt(pair, related, tmp_path, "D1GA")

    assert "Decision application guard:" not in prompt
    assert "Decision Brief" not in prompt


def test_preflight_pull_checks_remote_even_when_image_is_local(monkeypatch) -> None:
    runner = load_runner()
    calls = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        if command[:3] == ["docker", "image", "inspect"]:
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[:2] == ["docker", "pull"]:
            return subprocess.CompletedProcess(command, 0, "pulled", "")
        raise AssertionError(command)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    result = runner.check_hardened_image(
        "jiayuanz3/swecontextbench:example.repo-1",
        SimpleNamespace(preflight_docker="pull", preflight_timeout_seconds=1.0),
    )

    assert result == {"name": "hardened_image", "ok": True, "detail": "pulled"}
    assert calls == [
        ["docker", "image", "inspect", "jiayuanz3/swecontextbench:example.repo-1"],
        ["docker", "pull", "jiayuanz3/swecontextbench:example.repo-1"],
    ]
