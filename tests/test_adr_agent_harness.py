from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from benchmarks.adr_agent.checks import check_case, load_cases
from repo_decisions.core import add_decision


class AdrAgentHarnessTests(unittest.TestCase):
    def test_cases_load(self) -> None:
        cases = load_cases()
        self.assertIn("format-preservation-add-adr", cases)
        self.assertIn("code-follows-jsonl-adr", cases)

    def test_format_preservation_case_passes_after_repo_decisions_add(self) -> None:
        case = load_cases()["format-preservation-add-adr"]
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
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

            report = check_case(case, workspace, debug_log)

        self.assertTrue(report.ok, report.failures)

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
