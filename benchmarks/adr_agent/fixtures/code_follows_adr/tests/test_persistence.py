from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.persistence import append_event


class PersistenceTests(unittest.TestCase):
    def test_append_event_writes_json_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            append_event(path, {"kind": "created", "value": 1})
            append_event(path, {"kind": "updated", "value": 2})

            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.endswith("\n"))
            self.assertEqual(
                [json.loads(line) for line in text.splitlines()],
                [{"kind": "created", "value": 1}, {"kind": "updated", "value": 2}],
            )


if __name__ == "__main__":
    unittest.main()
