from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path

from repo_decisions.core import add_decision, build_brief, locate_adrs, parse_adr_file


class DeterministicFuzzTests(unittest.TestCase):
    def test_parse_markdown_variants_without_crashing(self) -> None:
        rng = random.Random(20260605)
        statuses = [
            "Accepted",
            "accepted.",
            "Proposed",
            "Rejected",
            "Deprecated",
            "Superseded by ADR-0001",
            "",
            "UNKNOWN VALUE",
        ]
        headings = [
            "Context",
            "Context and Problem Statement",
            "Decision",
            "Decision Outcome",
            "Consequences",
            "Considered Options",
            "Status",
        ]
        noise = [
            "",
            "plain text",
            "- bullet",
            "* star bullet",
            "### nested heading",
            "```python\nprint('not a heading')\n```",
            "emoji-like ascii :)",
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            adr_dir = Path(tmpdir)
            for index in range(180):
                status = rng.choice(statuses)
                title = rng.choice(["Use SQLite", "ADR title", "", "Decision: API v2"])
                title_line = f"# {title}" if title else rng.choice(noise)
                body = [title_line]
                if rng.choice([True, False]):
                    body.extend(["", f"Status: {status}"])
                for heading in rng.sample(headings, k=rng.randint(0, len(headings))):
                    body.extend(["", f"## {heading}", ""])
                    body.extend(rng.choice(noise) for _ in range(rng.randint(0, 4)))
                    if heading == "Status" and status:
                        body.append(status)
                    if heading in {"Decision", "Decision Outcome"}:
                        body.append(rng.choice(["Use Postgres.", "Keep the wrapper.", ""]))
                if rng.choice([True, False]):
                    raw = "\n".join(
                        [
                            "---",
                            f"status: {status}",
                            "date: 2026-06-05",
                            "---",
                            *body,
                        ]
                    )
                else:
                    raw = "\n".join(body)

                path = adr_dir / f"{index:04d}-fuzz.md"
                path.write_text(raw, encoding="utf-8")

                record = parse_adr_file(path)
                self.assertEqual(record.path, path)
                self.assertTrue(record.status)

    def test_add_and_brief_with_fuzzed_titles_and_content(self) -> None:
        rng = random.Random(42)
        titles = [
            "Use SQLite",
            "  spaces around title  ",
            "Symbols / slashes ? and % signs",
            "CAPS and snake_case",
            "...",
        ]
        snippets = [
            "Short line.",
            "- bullet-like input",
            "Multiple\nlines\nof content.",
            "Text with punctuation: ,.;:!?",
            "   padded text   ",
        ]

        for index in range(30):
            with tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                title = rng.choice(titles)
                path = add_decision(
                    root,
                    title=title,
                    context=rng.choice(snippets),
                    decision=rng.choice(snippets),
                    consequences=[rng.choice(snippets), rng.choice(snippets)],
                    options=[rng.choice(snippets)],
                )

                self.assertTrue(path.exists())
                self.assertEqual(path.suffix, ".md")
                self.assertNotIn("/", path.name)

                location = locate_adrs(root)
                self.assertEqual(len(location.records), 1)
                brief = build_brief(root, max_chars=500)
                self.assertLessEqual(len(brief), 500)
                self.assertIn("Repository ADR Decisions", brief)


if __name__ == "__main__":
    unittest.main()
