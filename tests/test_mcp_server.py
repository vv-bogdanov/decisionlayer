from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from repo_decisions import mcp_server


class McpServerTests(unittest.TestCase):
    def test_tools_are_prefixed_and_descriptive(self) -> None:
        tools = mcp_server._tools()
        names = [tool["name"] for tool in tools]

        self.assertEqual(
            names,
            [
                "adr_locate_directory",
                "adr_list_decisions",
                "adr_build_brief",
                "adr_add_decision",
                "adr_supersede_decision",
                "adr_configure",
            ],
        )
        self.assertTrue(all(name.startswith("adr_") for name in names))
        self.assertTrue(all("Architecture Decision Record" in tool["description"] or "ADR" in tool["description"] for tool in tools))
        self.assertTrue(tools[0]["annotations"]["readOnlyHint"])
        self.assertFalse(tools[3]["annotations"]["destructiveHint"])
        self.assertTrue(tools[4]["annotations"]["destructiveHint"])

    def test_old_tool_names_remain_compatible_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            response = mcp_server._call_tool(
                "add",
                {
                    "root": str(root),
                    "title": "Use SQLite",
                    "context": "Need local persistence.",
                    "decision": "Use SQLite for local persistence.",
                    "consequences": ["No external database is required."],
                },
            )
            self.assertIn("created", response["content"][0]["text"])

            listed = mcp_server._call_tool("list", {"root": str(root)})
            payload = json.loads(listed["content"][0]["text"])
            self.assertEqual(payload[0]["title"], "Use SQLite")

            brief = mcp_server._call_tool("adr_build_brief", {"root": str(root)})
            self.assertIn("Use SQLite for local persistence", brief["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
