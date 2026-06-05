from __future__ import annotations

import json
import os
import shutil
import tempfile
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from benchmarks.adr_agent import run_case
from benchmarks.adr_agent import run_suite
from benchmarks.adr_agent.report import build_report
from benchmarks.adr_agent.checks import check_case, load_cases
from benchmarks.adr_agent.run_case import _clean_runtime_artifacts, compose_effective_prompt
from repo_decisions.core import add_decision, supersede_decision


class AdrAgentHarnessTests(unittest.TestCase):
    def test_cases_load(self) -> None:
        cases = load_cases()
        self.assertIn("format-preservation-add-adr", cases)
        self.assertIn("code-follows-jsonl-adr", cases)
        self.assertIn("supersede-accepted-adr", cases)
        self.assertIn("conflict-requires-supersede-confirmation", cases)
        self.assertIn("no-false-decision-creation", cases)
        self.assertEqual(cases["real-asyncapi-format-add-adr"].repo_id, "asyncapi-studio")
        self.assertIsNone(cases["real-asyncapi-format-add-adr"].fixture)

    def test_real_repo_metadata_loads(self) -> None:
        data = tomllib.loads((Path("benchmarks/adr_agent/repos.toml")).read_text(encoding="utf-8"))
        repos = data["repos"]

        self.assertGreaterEqual(len(repos), 4)
        self.assertEqual([repo["id"] for repo in repos if repo["first_canary"]], ["asyncapi-studio"])
        for repo in repos:
            self.assertRegex(repo["commit"], r"^[0-9a-f]{40}$")
            self.assertTrue(repo["adr_dir"])

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

    def test_supersede_case_passes_after_repo_decisions_supersede(self) -> None:
        case = load_cases()["supersede-accepted-adr"]
        with tempfile.TemporaryDirectory() as tmp:
            baseline = Path(tmp) / "baseline"
            workspace = Path(tmp) / "workspace"
            shutil.copytree(case.fixture_dir, baseline)
            shutil.copytree(case.fixture_dir, workspace)
            debug_log = Path(tmp) / "debug.jsonl"
            old_debug_log = os.environ.get("REPO_DECISIONS_DEBUG_LOG")
            os.environ["REPO_DECISIONS_DEBUG_LOG"] = str(debug_log)
            try:
                supersede_decision(
                    workspace,
                    "1",
                    title="Use PostgreSQL",
                    context="The project now needs concurrent writers.",
                    decision="Use PostgreSQL as the primary persistence store.",
                    consequences=["An external database service is required."],
                    options=["SQLite", "PostgreSQL"],
                )
            finally:
                if old_debug_log is None:
                    os.environ.pop("REPO_DECISIONS_DEBUG_LOG", None)
                else:
                    os.environ["REPO_DECISIONS_DEBUG_LOG"] = old_debug_log

            report = check_case(case, workspace, debug_log, baseline=baseline, mode="d1")

        self.assertTrue(report.ok, report.failures)

    def test_conflict_case_requires_confirmation_without_adr_changes(self) -> None:
        case = load_cases()["conflict-requires-supersede-confirmation"]
        with tempfile.TemporaryDirectory() as tmp:
            baseline = Path(tmp) / "baseline"
            workspace = Path(tmp) / "workspace"
            shutil.copytree(case.fixture_dir, baseline)
            shutil.copytree(case.fixture_dir, workspace)

            report = check_case(
                case,
                workspace,
                baseline=baseline,
                mode="d1",
                agent_stdout="This conflicts with ADR-0001. Please confirm a supersede flow.",
            )

        self.assertTrue(report.ok, report.failures)

    def test_conflict_case_fails_on_adr_mutation(self) -> None:
        case = load_cases()["conflict-requires-supersede-confirmation"]
        with tempfile.TemporaryDirectory() as tmp:
            baseline = Path(tmp) / "baseline"
            workspace = Path(tmp) / "workspace"
            shutil.copytree(case.fixture_dir, baseline)
            shutil.copytree(case.fixture_dir, workspace)
            (workspace / "docs/adr/0001-use-sqlite.md").write_text(
                "# 1. Use PostgreSQL\n\n## Status\n\nAccepted\n\n## Decision\n\nUse PostgreSQL.\n",
                encoding="utf-8",
            )

            report = check_case(
                case,
                workspace,
                baseline=baseline,
                mode="d1",
                agent_stdout="Implemented.",
            )

        self.assertFalse(report.ok)
        self.assertTrue(any(item.startswith("unexpected ADR changes") for item in report.failures))

    def test_conflict_case_fails_on_code_mutation(self) -> None:
        case = load_cases()["conflict-requires-supersede-confirmation"]
        with tempfile.TemporaryDirectory() as tmp:
            baseline = Path(tmp) / "baseline"
            workspace = Path(tmp) / "workspace"
            shutil.copytree(case.fixture_dir, baseline)
            shutil.copytree(case.fixture_dir, workspace)
            (workspace / "src/app.py").write_text('DATABASE_URL = "postgresql://localhost:5432/app"\n', encoding="utf-8")

            report = check_case(
                case,
                workspace,
                baseline=baseline,
                mode="d1",
                agent_stdout="This conflicts with ADR-0001. Please confirm a supersede flow.",
            )

        self.assertFalse(report.ok)
        self.assertTrue(any(item.startswith("unexpected file changes") for item in report.failures))

    def test_no_false_decision_case_passes_without_adr_creation(self) -> None:
        case = load_cases()["no-false-decision-creation"]
        with tempfile.TemporaryDirectory() as tmp:
            baseline = Path(tmp) / "baseline"
            workspace = Path(tmp) / "workspace"
            shutil.copytree(case.fixture_dir, baseline)
            shutil.copytree(case.fixture_dir, workspace)

            report = check_case(
                case,
                workspace,
                baseline=baseline,
                mode="d1",
                agent_stdout="I will not create an ADR because there is no explicit decision authorization.",
            )

        self.assertTrue(report.ok, report.failures)

    def test_prompt_modes(self) -> None:
        brief = "# Repository ADR Decisions\n\n- ADR-0001: Use JSONL.\n"
        task = "Implement persistence."

        self.assertEqual(compose_effective_prompt(task, brief, "d0"), "Implement persistence.\n")
        self.assertIn("ADR-0001", compose_effective_prompt(task, brief, "d1"))
        self.assertIn("Repo Decisions Tool Requirement", compose_effective_prompt(task, brief, "d2"))
        self.assertIn("REPO_DECISIONS_CLI", compose_effective_prompt(task, brief, "d2"))
        self.assertIn("explicit supersede confirmation", compose_effective_prompt(task, brief, "d2"))

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

    def test_run_case_external_case_requires_source_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stderr = StringIO()
            with redirect_stdout(StringIO()), redirect_stderr(stderr):
                code = run_case.main(
                    [
                        "real-asyncapi-format-add-adr",
                        "--results-dir",
                        tmp,
                    ]
                )

        self.assertEqual(code, 2)
        self.assertIn("Pass --source-dir", stderr.getvalue())

    def test_run_case_cleans_runtime_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src/__pycache__").mkdir(parents=True)
            (root / "src/__pycache__/module.cpython-312.pyc").write_bytes(b"cache")
            (root / ".pytest_cache").mkdir()
            (root / ".coverage").write_text("coverage", encoding="utf-8")
            (root / "src/persistence.py").write_text("keep", encoding="utf-8")

            _clean_runtime_artifacts(root)

            self.assertFalse((root / "src/__pycache__").exists())
            self.assertFalse((root / ".pytest_cache").exists())
            self.assertFalse((root / ".coverage").exists())
            self.assertTrue((root / "src/persistence.py").exists())

    def test_run_case_cli_fallback_uses_fixture_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(StringIO()):
                code = run_case.main(
                    [
                        "format-preservation-add-adr",
                        "--mode",
                        "d2",
                        "--results-dir",
                        tmp,
                        "--run-id",
                        "cli-fallback",
                        "--agent-command",
                        (
                            '"$REPO_DECISIONS_CLI" --root . add '
                            '--title "Use HTTP Client Timeout" '
                            '--context "Outbound calls must not hang indefinitely." '
                            '--option "No timeout" '
                            '--option "5 second timeout" '
                            '--decision "All outbound HTTP clients must use a 5 second timeout." '
                            '--consequence "Slow downstream services fail fast."'
                        ),
                    ]
                )
            result_path = Path(tmp) / "cli-fallback/format-preservation-add-adr/d2/result.json"
            payload = json.loads(result_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["metrics"]["changed_adr_files"], 1)
        self.assertEqual(payload["metrics"]["write_events"], 1)
        self.assertGreaterEqual(payload["metrics"]["tool_calls"], 1)
        self.assertTrue(payload["workspace"].startswith(tmp))

    def test_run_suite_groups_results_under_one_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(StringIO()):
                code = run_suite.main(
                    [
                        "--case",
                        "code-follows-jsonl-adr",
                        "--mode",
                        "d0",
                        "--mode",
                        "d1",
                        "--results-dir",
                        tmp,
                        "--run-id",
                        "grouped",
                        "--quiet",
                    ]
                )
            result_files = sorted(Path(tmp).glob("grouped/code-follows-jsonl-adr/*/result.json"))

        self.assertEqual(code, 0)
        self.assertEqual(len(result_files), 2)

    def test_report_summarizes_prepared_results(self) -> None:
        report = build_report(
            Path("/tmp/run-1"),
            [
                {
                    "case_id": "code-follows-jsonl-adr",
                    "mode": "d0",
                    "status": "prepared",
                    "metrics": {"prompt_chars": 100, "initial_brief_chars": 0},
                },
                {
                    "case_id": "code-follows-jsonl-adr",
                    "mode": "d1",
                    "status": "passed",
                    "metrics": {
                        "prompt_chars": 200,
                        "duration_sec": 1.5,
                        "diff_size": 10,
                        "changed_files": 1,
                        "changed_adr_files": 0,
                        "tool_calls": 0,
                        "write_events": 0,
                    },
                    "checks": {"failures": []},
                },
            ],
        )

        self.assertIn("# ADR-Agent Canary Report", report)
        self.assertIn("code-follows-jsonl-adr", report)
        self.assertIn("prepared", report)

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
