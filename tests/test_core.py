from __future__ import annotations

import os
import json
import tempfile
import unittest
from pathlib import Path

from repo_decisions.core import (
    add_decision,
    build_brief,
    locate_adrs,
    parse_adr_file,
    supersede_decision,
)


class RepoDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.global_config = self.root / "global.toml"
        os.environ["REPO_DECISIONS_GLOBAL_CONFIG"] = str(self.global_config)
        os.environ.pop("REPO_DECISIONS_DEBUG_LOG", None)

    def tearDown(self) -> None:
        os.environ.pop("REPO_DECISIONS_GLOBAL_CONFIG", None)
        os.environ.pop("REPO_DECISIONS_DEBUG_LOG", None)
        self.tmp.cleanup()

    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text.strip() + "\n", encoding="utf-8")
        return path

    def test_locate_defaults_to_docs_adr_when_empty(self) -> None:
        location = locate_adrs(self.root)

        self.assertEqual(location.adr_dir, self.root / "docs/adr")
        self.assertEqual(location.records, tuple())
        self.assertEqual(location.source, "default")

    def test_parses_nygard_and_brief_includes_only_accepted(self) -> None:
        self.write(
            "docs/adr/0001-record-decisions.md",
            """
            # 1. Record decisions

            Date: 2026-06-05

            ## Status

            Accepted

            ## Context

            Decisions are easy to forget.

            ## Decision

            We will record architecture decisions as ADRs.

            ## Consequences

            Future agents can see the rationale.
            """,
        )
        self.write(
            "docs/adr/0002-draft.md",
            """
            # 2. Draft only

            ## Status

            Proposed

            ## Context

            Work in progress.

            ## Decision

            Not active yet.

            ## Consequences

            None.
            """,
        )

        location = locate_adrs(self.root)
        brief = build_brief(self.root)

        self.assertEqual(len(location.records), 2)
        self.assertIn("ADR-0001", brief)
        self.assertIn("We will record architecture decisions", brief)
        self.assertNotIn("Draft only", brief)

    def test_strips_number_prefix_from_title(self) -> None:
        path = self.write(
            "docs/adr/0007-numbered-title.md",
            """
            # 7. Numbered Title

            ## Status

            Accepted

            ## Context

            Existing ADRs include numbers in H1 headings.

            ## Decision

            Store the semantic title without the H1 number prefix.

            ## Consequences

            Prompt briefs avoid duplicate numbering.
            """,
        )

        record = parse_adr_file(path)
        brief = build_brief(self.root)

        self.assertEqual(record.title, "Numbered Title")
        self.assertIn("ADR-0007: Numbered Title", brief)
        self.assertNotIn("ADR-0007: 7. Numbered Title", brief)

    def test_parses_madr_frontmatter(self) -> None:
        path = self.write(
            "docs/decisions/0001-use-madr.md",
            """
            ---
            status: accepted
            date: 2026-06-05
            ---

            # Use MADR

            ## Context and Problem Statement

            We need options and rationale.

            ## Considered Options

            - Nygard
            - MADR

            ## Decision Outcome

            Chosen option: "MADR", because it captures tradeoffs.

            ### Consequences

            Good, because future readers see alternatives.
            """,
        )

        record = parse_adr_file(path)

        self.assertEqual(record.status, "accepted")
        self.assertEqual(record.date, "2026-06-05")
        self.assertEqual(record.options, ["Nygard", "MADR"])
        self.assertIn("MADR", record.decision)

    def test_local_config_overrides_directory(self) -> None:
        self.write(".codex/repo-decisions.toml", 'adr_dir = "architecture/decisions"\n')
        self.write(
            "architecture/decisions/001-use-custom-dir.md",
            """
            # 001. Use custom dir

            ## Status

            Accepted

            ## Context

            Existing repo convention.

            ## Decision

            Keep ADRs here.

            ## Consequences

            Plugin must find them.
            """,
        )

        location = locate_adrs(self.root)

        self.assertEqual(location.adr_dir, self.root / "architecture/decisions")
        self.assertEqual(location.source, "config")
        self.assertEqual(location.profile.number_width, 3)

    def test_detects_adr_tools_style_doc_adr_directory(self) -> None:
        self.write(
            "doc/adr/0001-record-architecture-decisions.md",
            """
            # 1. Record architecture decisions

            Date: 2026-06-05

            ## Status

            Accepted

            ## Context

            We need to record architectural decisions.

            ## Decision

            We will use Architecture Decision Records.

            ## Consequences

            Decisions are visible in the project repository.
            """,
        )

        location = locate_adrs(self.root)

        self.assertEqual(location.adr_dir, self.root / "doc/adr")
        self.assertEqual(location.records[0].status, "accepted")
        self.assertEqual(location.profile.filename_style, "{number:04d}-{slug}.md")

    def test_add_uses_fallback_template_when_no_adrs_exist(self) -> None:
        path = add_decision(
            self.root,
            title="Start ADR log",
            context="The repository has no ADR convention yet.",
            decision="We will start with the fallback ADR template.",
            consequences=["Future decisions have a consistent shape."],
            options=["No ADRs", "Fallback template"],
        )
        text = path.read_text(encoding="utf-8")

        self.assertEqual(path, self.root / "docs/adr/0001-start-adr-log.md")
        self.assertIn("## Context and Problem Statement", text)
        self.assertIn("## Considered Options", text)
        self.assertIn("## Decision", text)

    def test_debug_log_records_add_write_hash(self) -> None:
        log_path = self.root / "debug.jsonl"
        os.environ["REPO_DECISIONS_DEBUG_LOG"] = str(log_path)

        path = add_decision(
            self.root,
            title="Audit writes",
            context="Tests need proof the tool performed ADR writes.",
            decision="Write debug JSONL events for ADR operations.",
            consequences=["Harness checks can prove tool usage."],
            options=["Transcript only", "Debug log"],
        )

        events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
        write = next(event for event in events if event["operation"] == "add")
        after = write["after"][str(path)]

        self.assertEqual(write["event"], "write")
        self.assertEqual(after["exists"], True)
        self.assertEqual(len(after["sha256"]), 64)

    def test_add_preserves_detected_numbering_and_headings(self) -> None:
        self.write(
            "docs/adr/007-existing.md",
            """
            # 7. Existing

            Date: 2026-06-05

            ## Status

            Accepted

            ## Context

            Existing Nygard style.

            ## Decision

            Keep the style.

            ## Consequences

            New records should match.
            """,
        )

        path = add_decision(
            self.root,
            title="Use wrapper enrichment",
            context="Hooks are not verified.",
            decision="We will use a wrapper for the first POC.",
            consequences=["Prompt enrichment is deterministic."],
            options=["Hook", "Wrapper"],
        )
        text = path.read_text(encoding="utf-8")

        self.assertEqual(path.name, "008-use-wrapper-enrichment.md")
        self.assertIn("## Status", text)
        self.assertIn("## Context", text)
        self.assertIn("## Decision", text)
        self.assertIn("Wrapper", text)

    def test_supersede_creates_replacement_and_updates_old_status(self) -> None:
        old = self.write(
            "docs/adr/0001-use-hooks.md",
            """
            # 1. Use hooks

            Date: 2026-06-05

            ## Status

            Accepted

            ## Context

            We wanted automatic injection.

            ## Decision

            Use hooks for prompt enrichment.

            ## Consequences

            Depends on hook mutation.
            """,
        )

        old_path, new_path = supersede_decision(
            self.root,
            "1",
            title="Use wrapper enrichment",
            context="Hook prompt mutation is not verified.",
            decision="Use wrapper prompt enrichment for the first POC.",
            consequences=["Prompt enrichment is deterministic."],
            options=["Hook", "Wrapper"],
        )

        self.assertEqual(old_path, old)
        self.assertEqual(new_path.name, "0002-use-wrapper-enrichment.md")
        self.assertIn("Superseded by ADR-0002", old.read_text(encoding="utf-8"))
        self.assertIn("Supersedes: [ADR-0001", new_path.read_text(encoding="utf-8"))
        brief = build_brief(self.root)
        self.assertIn("ADR-0002", brief)
        self.assertNotIn("ADR-0001", brief)


if __name__ == "__main__":
    unittest.main()
