from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from repo_decisions import mcp_server


class McpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

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
        self.assertTrue(all(tool["outputSchema"]["type"] == "object" for tool in tools))
        self.assertTrue(tools[0]["annotations"]["readOnlyHint"])
        self.assertFalse(tools[3]["annotations"]["destructiveHint"])
        self.assertTrue(tools[4]["annotations"]["destructiveHint"])
        self.assertEqual(tools[0]["outputSchema"]["required"], ["root", "adr_dir", "source", "records", "profile"])

    def test_old_tool_names_remain_compatible_aliases(self) -> None:
        response = mcp_server._call_tool(
            "add",
            {
                "root": str(self.root),
                "title": "Use SQLite",
                "context": "Need local persistence.",
                "decision": "Use SQLite for local persistence.",
                "consequences": ["No external database is required."],
            },
        )
        self.assertIn("created", response["content"][0]["text"])
        self.assertTrue(response["structuredContent"]["created"])

        located = mcp_server._call_tool("locate", {"root": str(self.root)})
        self.assertEqual(json.loads(located["content"][0]["text"])["records"], 1)
        self.assertEqual(located["structuredContent"]["records"], 1)

        listed = mcp_server._call_tool("list", {"root": str(self.root)})
        payload = json.loads(listed["content"][0]["text"])
        self.assertEqual(payload[0]["title"], "Use SQLite")
        self.assertEqual(listed["structuredContent"]["decisions"][0]["title"], "Use SQLite")

        brief = mcp_server._call_tool("adr_build_brief", {"root": str(self.root), "max_chars": 1000})
        self.assertIn("Use SQLite for local persistence", brief["content"][0]["text"])
        self.assertEqual(brief["structuredContent"]["active_count"], 1)

        config = mcp_server._call_tool(
            "config",
            {"root": str(self.root), "set": {"adr_dir": "docs/adr", "brief_max_chars": "500"}},
        )
        self.assertIn("updated", config["content"][0]["text"])
        self.assertTrue(config["structuredContent"]["updated"])
        shown = mcp_server._call_tool("adr_configure", {"root": str(self.root)})
        self.assertIn("brief_max_chars", shown["content"][0]["text"])
        self.assertEqual(shown["structuredContent"]["config"]["brief_max_chars"], "500")

    def test_supersede_and_error_paths(self) -> None:
        mcp_server._call_tool(
            "adr_add_decision",
            {
                "root": str(self.root),
                "title": "Use SQLite",
                "context": "Need local persistence.",
                "decision": "Use SQLite for local persistence.",
                "consequences": "No external database is required.",
            },
        )
        superseded = mcp_server._call_tool(
            "adr_supersede_decision",
            {
                "root": str(self.root),
                "target": "1",
                "title": "Use Postgres",
                "context": "Need concurrent writers.",
                "decision": "Use Postgres for primary persistence.",
                "consequences": ["A database service is required."],
                "options": ["SQLite", "Postgres"],
            },
        )
        self.assertIn("superseded", superseded["content"][0]["text"])

        with self.assertRaises(ValueError):
            mcp_server._call_tool("unknown", {"root": str(self.root)})
        with self.assertRaises(ValueError):
            mcp_server._call_tool("adr_add_decision", {"root": str(self.root)})
        with self.assertRaises(ValueError):
            mcp_server._strings({"bad": "shape"})

    def test_handle_initialize_list_call_and_errors(self) -> None:
        initialized = mcp_server._handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        assert initialized is not None
        self.assertEqual(initialized["result"]["serverInfo"]["name"], "repo-adr-decisions")

        self.assertIsNone(mcp_server._handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))

        listed = mcp_server._handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert listed is not None
        self.assertIn("tools", listed["result"])

        called = mcp_server._handle(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "adr_locate_directory", "arguments": {"root": str(self.root)}},
            }
        )
        assert called is not None
        self.assertIn("content", called["result"])
        self.assertIn("structuredContent", called["result"])

        unknown = mcp_server._handle({"jsonrpc": "2.0", "id": 4, "method": "nope"})
        assert unknown is not None
        self.assertEqual(unknown["error"]["code"], -32601)

        failed = mcp_server._handle(
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "unknown"}}
        )
        assert failed is not None
        self.assertEqual(failed["error"]["code"], -32602)

        bad_args = mcp_server._handle(
            {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {"name": "adr_add_decision", "arguments": {"root": str(self.root)}},
            }
        )
        assert bad_args is not None
        self.assertTrue(bad_args["result"]["isError"])
        self.assertIn("Missing required argument", bad_args["result"]["structuredContent"]["error"])


if __name__ == "__main__":
    unittest.main()
