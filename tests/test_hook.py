from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK_SCRIPT = ROOT / "plugins/repo-decisions/scripts/user-prompt-submit"


class UserPromptSubmitHookTests(unittest.TestCase):
    def test_hook_outputs_additional_context_for_accepted_adrs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            adr_dir = repo / "docs/adr"
            adr_dir.mkdir(parents=True)
            (adr_dir / "0001-use-postgres.md").write_text(
                """# 1. Use Postgres

Date: 2026-06-05

## Status

Accepted

## Context and Problem Statement

The project needs durable relational storage.

## Decision

Use Postgres for primary persistence.

## Consequences

Schema migrations are required.
""",
                encoding="utf-8",
            )
            log_path = repo / "debug.jsonl"
            result = subprocess.run(
                [str(HOOK_SCRIPT)],
                input=json.dumps({"cwd": str(repo), "hook_event_name": "UserPromptSubmit"}),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "REPO_DECISIONS_DEBUG_LOG": str(log_path)},
                check=True,
            )

            payload = json.loads(result.stdout)
            additional_context = payload["hookSpecificOutput"]["additionalContext"]
            self.assertIn("# Repository ADR Decisions (Hard Requirements)", additional_context)
            self.assertIn("Use Postgres", additional_context)
            self.assertIn("Use Postgres for primary persistence", additional_context)

            events = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertTrue(
                any(
                    event.get("event") == "hook-context"
                    and event.get("active_decisions") == 1
                    for event in events
                )
            )

    def test_hook_is_silent_without_active_adrs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            result = subprocess.run(
                [str(HOOK_SCRIPT)],
                input=json.dumps({"cwd": str(repo), "hook_event_name": "UserPromptSubmit"}),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
