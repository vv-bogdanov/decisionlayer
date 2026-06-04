from __future__ import annotations

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "run-swe-contextbench-publishable-d0-d1g"


def test_publishable_script_is_valid_bash() -> None:
    subprocess.run(["bash", "-n", str(SCRIPT)], cwd=PROJECT_ROOT, check=True)


def test_publishable_script_keeps_proof_lane_invariants() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert 'modes="${MODES:-D0,D1G}"' in text
    assert 'codex_reasoning_effort="${CODEX_REASONING_EFFORT:-low}"' in text
    assert "--preflight-docker pull" in text
    assert "scripts/run-swe-contextbench-mini-slice" in text
    assert "scripts/summarize-swe-contextbench-run" in text
    assert "docker login" in text
