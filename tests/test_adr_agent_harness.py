from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from benchmarks.adr_agent import run_case
from benchmarks.adr_agent.checks import check_case, load_cases
from benchmarks.adr_agent.run_case import compose_effective_prompt
from repo_decisions.core import add_decision


class AdrAgentHarnessTests(unittest.TestCase):
    def test_cases_load(self) -> None:
        cases = load_cases()
        self.assertIn("format-preservation-add-adr", cases)
        self.assertIn("code-follows-jsonl-adr", cases)

    def test_format_preservation_case_passes_after_repo_decisions_add(self) -> None:
        case = load_cases()["format-preservation-add-adr"]
        with tempfile.TemporaryDirectory() as tmp:
            baseline = Path(tmp) / "baseline"
            workspace = Path(tmp) / "workspace"
            shutil.copytree(case.fixture_dir, baseline)
            shutil.copytree(case.fixture_dir, workspace)
            debug_log = Path(tmp) / "debug.jsonl"
            old_debug_log = os.environ.get("REPO_DECISIONS_DEBUG_LOG")
            os.environ["REPO_DECISIONS_DEBUG_LOG"] = str(debug_log)
            try:
                add_decision(
                    workspace,
                    title="Use HTTP Client Timeout",
                    context="Outbound calls must not hang indefinitely.",
                    decision="All outbound HTTP clients must use a 5 second timeout.",
                    consequences=["Slow downstream services fail fast."],
                    options=["No timeout", "5 second timeout"],
                )
            finally:
                if old_debug_log is None:
                    os.environ.pop("REPO_DECISIONS_DEBUG_LOG", None)
                else:
                    os.environ["REPO_DECISIONS_DEBUG_LOG"] = old_debug_log

            report = check_case(case, workspace, debug_log, baseline=baseline, mode="d1")

        self.assertTrue(report.ok, report.failures)

    def test_format_case_fails_when_adr_changes_without_debug_write(self) -> None:
        case = load_cases()["format-preservation-add-adr"]
        with tempfile.TemporaryDirectory() as tmp:
            baseline = Path(tmp) / "baseline"
            workspace = Path(tmp) / "workspace"
            shutil.copytree(case.fixture_dir, baseline)
            shutil.copytree(case.fixture_dir, workspace)
            new_adr = workspace / "docs/adr/0002-use-http-client-timeout.md"
            new_adr.write_text(
                "\n".join(
                    [
                        "# 2. Use HTTP Client Timeout",
                        "",
                        "## Status",
                        "",
                        "Accepted",
                        "",
                        "## Context and Problem Statement",
                        "",
                        "Outbound calls must not hang indefinitely.",
                        "",
                        "## Decision",
                        "",
                        "All outbound HTTP clients must use a 5 second timeout.",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            report = check_case(case, workspace, baseline=baseline, mode="d1")

        self.assertFalse(report.ok)
        self.assertIn("missing repo-decisions write event in debug log", report.failures)

    def test_prompt_modes(self) -> None:
        brief = "# Repository ADR Decisions\n\n- ADR-0001: Use JSONL.\n"
        task = "Implement persistence."

        self.assertEqual(compose_effective_prompt(task, brief, "d0"), "Implement persistence.\n")
        self.assertIn("ADR-0001", compose_effective_prompt(task, brief, "d1"))
        self.assertIn("Repo Decisions Tool Requirement", compose_effective_prompt(task, brief, "d2"))

    def test_run_case_prepare_writes_mode_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(StringIO()):
                code = run_case.main(
                    [
                        "code-follows-jsonl-adr",
                        "--mode",
                        "d1",
                        "--results-dir",
                        tmp,
                    ]
                )
            result_files = list(Path(tmp).glob("*/code-follows-jsonl-adr/d1/result.json"))
            payload = json.loads(result_files[0].read_text(encoding="utf-8"))
            effective_prompt = Path(payload["effective_prompt_file"]).read_text(encoding="utf-8")

        self.assertEqual(code, 0)
        self.assertEqual(payload["mode"], "d1")
        self.assertIn("Repository ADR Decisions", effective_prompt)

    def test_code_case_passes_after_jsonl_implementation(self) -> None:
        case = load_cases()["code-follows-jsonl-adr"]
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            shutil.copytree(case.fixture_dir, workspace)
            (workspace / "src/persistence.py").write_text(
                "\n".join(
                    [
                        "from __future__ import annotations",
                        "",
                        "import json",
                        "from pathlib import Path",
                        "",
                        "",
                        "def append_event(path: Path, event: dict[str, object]) -> None:",
                        "    with open(path, 'a', encoding='utf-8') as handle:",
                        "        handle.write(json.dumps(event, sort_keys=True) + '\\n')",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            report = check_case(case, workspace)
            payload = json.loads(json.dumps(report.to_dict()))

        self.assertTrue(payload["ok"], payload["failures"])


if __name__ == "__main__":
    unittest.main()
