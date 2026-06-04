from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_summarize_swe_contextbench_run_outputs_totals(tmp_path: Path) -> None:
    pair = "example__repo-1"
    pair_dir = tmp_path / pair
    (pair_dir / "logs").mkdir(parents=True)
    (pair_dir / "patches").mkdir()
    (pair_dir / "logs" / "d0_result.json").write_text(
        json.dumps({"ok": True, "elapsed_seconds": 1.25}),
        encoding="utf-8",
    )
    (pair_dir / "logs" / "d0_grading_result.json").write_text(
        json.dumps(
            {
                "ok": True,
                "resolved_ids": [pair],
                pair: {
                    "resolved": True,
                    "patch_applied": True,
                    "tests_status": {
                        "FAIL_TO_PASS": {"success": ["test_new"], "failure": []},
                        "PASS_TO_PASS": {"success": ["test_old"], "failure": []},
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    (pair_dir / "patches" / "d0.patch").write_text(
        "diff --git a/tests/test_example.py b/tests/test_example.py\n"
        "--- a/tests/test_example.py\n"
        "+++ b/tests/test_example.py\n"
        "@@ -1,1 +1,2 @@\n"
        "+def test_new(): pass\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "summarize-swe-contextbench-run"),
            "--artifact-root",
            str(tmp_path),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "| D0 | 1/1 | 1/1 | 1 |" in result.stdout
    assert f"| `{pair}` | D0 | yes | 1.25 |" in result.stdout
