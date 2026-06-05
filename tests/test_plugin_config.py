from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PluginConfigTests(unittest.TestCase):
    def test_mcp_server_runs_from_plugin_root(self) -> None:
        config_path = ROOT / "plugins/repo-decisions/.mcp.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        server = config["mcpServers"]["repo-decisions"]

        self.assertEqual(server["command"], "./scripts/mcp-server")
        self.assertEqual(server["cwd"], ".")


if __name__ == "__main__":
    unittest.main()
