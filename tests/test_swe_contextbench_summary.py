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

    assert "| D0 | 1/1 | 1/1 | 1 | 0 |" in result.stdout
    assert "| D1 | 0/0 | 0/1 | 0 | 0 |" in result.stdout
    assert f"| `{pair}` | D0 | yes | 1.25 |" in result.stdout


def test_summarize_swe_contextbench_run_excludes_infra_errors(tmp_path: Path) -> None:
    pair = "example__repo-2"
    pair_dir = tmp_path / pair
    (pair_dir / "logs").mkdir(parents=True)
    (pair_dir / "patches").mkdir()
    (pair_dir / "logs" / "d0_result.json").write_text(
        json.dumps({"ok": True, "elapsed_seconds": 1.0}),
        encoding="utf-8",
    )
    (pair_dir / "logs" / "d0_grading_result.json").write_text(
        json.dumps(
            {
                "ok": True,
                "resolved_ids": [],
                pair: {
                    "resolved": False,
                    "error": "Hardened image not found for instance: example__repo-2",
                },
            }
        ),
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

    assert "| D0 | 0/0 | 1/1 | 0 | 1 |" in result.stdout
    assert "Hardened image not found" in result.stdout


def test_summarize_swe_contextbench_repeats_outputs_pair_matrix(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    pair = "example__repo-3"
    config.write_text(
        json.dumps(
            {
                "pairs": [
                    {
                        "related_instance_id": pair,
                        "d1_applicability": "apply",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    run_a = tmp_path / "run-a"
    run_b = tmp_path / "run-b"
    write_summary_fixture(run_a, pair, "d0", resolved=True)
    write_summary_fixture(run_a, pair, "d1g", resolved=False)
    write_summary_fixture(run_b, pair, "d0", resolved=False)
    write_summary_fixture(run_b, pair, "d1g", resolved=True)

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "summarize-swe-contextbench-repeats"),
            "--config",
            str(config),
            "a=" + str(run_a),
            "b=" + str(run_b),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "| `a` |" in result.stdout
    assert "| D0 | 1/2 | 1/1, 0/1 | 0-1 | 0 | 0 |" in result.stdout
    assert "| D1G | 1/2 | 0/1, 1/1 | 0-1 | 0 | 0 |" in result.stdout
    assert f"| `{pair}` | apply | 1/2 | 1/2 |" in result.stdout


def write_summary_fixture(root: Path, pair: str, mode: str, *, resolved: bool) -> None:
    pair_dir = root / pair
    (pair_dir / "logs").mkdir(parents=True, exist_ok=True)
    (pair_dir / "patches").mkdir(parents=True, exist_ok=True)
    (pair_dir / "logs" / f"{mode}_result.json").write_text(
        json.dumps({"ok": True, "elapsed_seconds": 1.0}),
        encoding="utf-8",
    )
    (pair_dir / "logs" / f"{mode}_grading_result.json").write_text(
        json.dumps(
            {
                "ok": True,
                "resolved_ids": [pair] if resolved else [],
                pair: {
                    "resolved": resolved,
                    "patch_applied": True,
                    "tests_status": {
                        "FAIL_TO_PASS": {
                            "success": ["test_new"] if resolved else [],
                            "failure": [] if resolved else ["test_new"],
                        },
                        "PASS_TO_PASS": {"success": ["test_old"], "failure": []},
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    (pair_dir / "patches" / f"{mode}.patch").write_text("", encoding="utf-8")
