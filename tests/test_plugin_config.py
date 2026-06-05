from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PluginConfigTests(unittest.TestCase):
    def test_mcp_server_runs_from_plugin_root(self) -> None:
        config_path = ROOT / "plugins/repo-decisions/.mcp.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        server = config["mcpServers"]["repo-adr-decisions"]

        self.assertEqual(server["command"], "./scripts/mcp-server")
        self.assertEqual(server["cwd"], ".")

    def test_plugin_bundle_package_matches_source_package(self) -> None:
        source_dir = ROOT / "repo_decisions"
        bundle_dir = ROOT / "plugins/repo-decisions/repo_decisions"
        for source_path in sorted(source_dir.glob("*.py")):
            bundle_path = bundle_dir / source_path.name
            self.assertTrue(bundle_path.exists(), f"missing bundled {source_path.name}")
            self.assertEqual(
                source_path.read_text(encoding="utf-8"),
                bundle_path.read_text(encoding="utf-8"),
                f"bundled {source_path.name} is out of sync",
            )

    def test_lab_script_exposes_runtime_smoke(self) -> None:
        script = (ROOT / "scripts/codex-plugin-lab").read_text(encoding="utf-8")

        self.assertIn("runtime-smoke Run codex exec", script)
        self.assertIn("runtime-smoke)", script)
        self.assertIn("runtime_smoke", script)


if __name__ == "__main__":
    unittest.main()
