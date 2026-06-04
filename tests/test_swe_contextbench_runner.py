from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path
from types import ModuleType

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
