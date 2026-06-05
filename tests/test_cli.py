from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from repo_decisions import cli


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.global_config = self.root / "global.toml"
        os.environ["REPO_DECISIONS_GLOBAL_CONFIG"] = str(self.global_config)

    def tearDown(self) -> None:
        os.environ.pop("REPO_DECISIONS_GLOBAL_CONFIG", None)
        self.tmp.cleanup()

    def run_cli(self, *args: str, stdin: str | None = None) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        fake_stdin = io.StringIO(stdin or "")
        with redirect_stdout(stdout), redirect_stderr(stderr), patch("sys.stdin", fake_stdin):
            code = cli.main(["--root", str(self.root), *args])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_locate_add_list_brief_and_supersede_commands(self) -> None:
        code, output, _stderr = self.run_cli("locate", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["records"], 0)

        code, output, _stderr = self.run_cli(
            "add",
            "--title",
            "Use SQLite",
            "--context",
            "Need a local store.",
            "--decision",
            "Use SQLite for local storage.",
            "--consequence",
            "No external database is required.",
            "--option",
            "SQLite",
        )
        self.assertEqual(code, 0)
        self.assertTrue(Path(output.strip()).exists())

        code, output, _stderr = self.run_cli("list", "--json")
        self.assertEqual(code, 0)
        records = json.loads(output)
        self.assertEqual(records[0]["title"], "Use SQLite")
        self.assertEqual(records[0]["status"], "accepted")

        code, output, _stderr = self.run_cli("brief", "--max-chars", "1000")
        self.assertEqual(code, 0)
        self.assertIn("Use SQLite for local storage", output)

        code, output, _stderr = self.run_cli(
            "supersede",
            "1",
            "--title",
            "Use Postgres",
            "--context",
            "The local store needs concurrent writers.",
            "--decision",
            "Use Postgres for primary storage.",
            "--consequence",
            "A database service is required.",
        )
        self.assertEqual(code, 0)
        self.assertIn("superseded", output)
        self.assertIn("created", output)

        code, output, _stderr = self.run_cli("list", "--active-only")
        self.assertEqual(code, 0)
        self.assertIn("Use Postgres", output)
        self.assertNotIn("Use SQLite\t", output)

    def test_config_command_reads_and_updates_local_config(self) -> None:
        code, output, _stderr = self.run_cli("config")
        self.assertEqual(code, 0)
        self.assertIn("does not exist", output)

        code, output, _stderr = self.run_cli(
            "config",
            "--set",
            "adr_dir=architecture/decisions",
            "--set",
            "brief_max_chars=1234",
        )
        self.assertEqual(code, 0)
        self.assertTrue(Path(output.strip()).exists())

        code, output, _stderr = self.run_cli("config")
        self.assertEqual(code, 0)
        self.assertIn('adr_dir = "architecture/decisions"', output)
        self.assertIn('brief_max_chars = "1234"', output)

    def test_codex_print_prompt_and_stdin_paths(self) -> None:
        self.run_cli(
            "add",
            "--title",
            "Keep Wrapper",
            "--context",
            "Hooks are not always available.",
            "--decision",
            "Keep the wrapper fallback.",
            "--consequence",
            "Prompt enrichment remains deterministic.",
        )

        code, output, _stderr = self.run_cli("codex", "--print-prompt", "--", "Implement task")
        self.assertEqual(code, 0)
        self.assertIn("Keep the wrapper fallback", output)
        self.assertIn("Implement task", output)

        code, output, _stderr = self.run_cli("codex", "--print-prompt", stdin="Summarize decisions")
        self.assertEqual(code, 0)
        self.assertIn("Summarize decisions", output)

        code, _output, stderr = self.run_cli("codex", "--print-prompt")
        self.assertEqual(code, 2)
        self.assertIn("requires a prompt", stderr)

    def test_codex_exec_invokes_configured_binary(self) -> None:
        recorder = self.root / "fake-codex"
        args_path = self.root / "codex-args.txt"
        recorder.write_text(
            "#!/usr/bin/env bash\n"
            f"printf '%s\\n' \"$@\" > {args_path}\n",
            encoding="utf-8",
        )
        recorder.chmod(0o755)

        code, _output, _stderr = self.run_cli(
            "codex",
            "--codex-bin",
            str(recorder),
            "--codex-arg=--sandbox",
            "--codex-arg",
            "read-only",
            "--",
            "Do work",
        )

        self.assertEqual(code, 0)
        args = args_path.read_text(encoding="utf-8")
        self.assertIn("exec\n", args)
        self.assertIn("--sandbox\n", args)
        self.assertIn("read-only\n", args)
        self.assertIn("--cd\n", args)
        self.assertIn("Do work\n", args)

    def test_invalid_assignment_raises(self) -> None:
        with self.assertRaises(Exception):
            cli._split_assignment("not-an-assignment")


if __name__ == "__main__":
    unittest.main()
