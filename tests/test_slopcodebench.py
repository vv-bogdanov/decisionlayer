from __future__ import annotations

import json
from pathlib import Path

from decision_layer.slopcodebench import (
    evaluation_passed_all_cases,
    extract_decisions_from_spec,
    format_decision_brief,
    write_summary_files,
)


def test_extract_decisions_keeps_short_authorized_requirements() -> None:
    spec = """
<!-- hidden benchmark comment -->
# Checkpoint

- Always emit SCHEDULE_PARSED exactly once.
- Sort due jobs by id ascending before execution.
- Example output is not a new decision.

```json
{"example": "must not be extracted"}
```
"""

    decisions = extract_decisions_from_spec(spec, checkpoint_name="checkpoint_1", max_decisions=4)

    assert decisions[0].startswith("checkpoint_1: preserve all behavior")
    assert any("Always emit SCHEDULE_PARSED" in decision for decision in decisions)
    assert any("Sort due jobs" in decision for decision in decisions)
    assert all("hidden benchmark comment" not in decision for decision in decisions)
    assert all("must not be extracted" not in decision for decision in decisions)


def test_format_decision_brief_is_empty_without_decisions() -> None:
    assert format_decision_brief([]) == ""


def test_evaluation_passed_all_cases_rejects_zero_tests() -> None:
    assert not evaluation_passed_all_cases(
        {
            "pytest_exit_code": 0,
            "infrastructure_failure": False,
            "pass_counts": {},
            "total_counts": {},
        }
    )


def test_write_summary_files_collects_d0_d1_delta(tmp_path: Path) -> None:
    d0_cp = tmp_path / "D0" / "example" / "checkpoint_1"
    d1_cp = tmp_path / "D1" / "example" / "checkpoint_1"
    d0_cp.mkdir(parents=True)
    d1_cp.mkdir(parents=True)

    (d0_cp / "evaluation.json").write_text(
        json.dumps(
            {
                "pytest_exit_code": 1,
                "infrastructure_failure": False,
                "pass_counts": {"Core": 0},
                "total_counts": {"Core": 1},
            }
        )
    )
    (d1_cp / "evaluation.json").write_text(
        json.dumps(
            {
                "pytest_exit_code": 0,
                "infrastructure_failure": False,
                "pass_counts": {"Core": 1},
                "total_counts": {"Core": 1},
            }
        )
    )
    decision_dir = tmp_path / "D1" / "example" / "decision_layer" / "checkpoint_decisions"
    decision_dir.mkdir(parents=True)
    (decision_dir / "checkpoint_1.json").write_text(json.dumps(["checkpoint_1: keep x"]))

    summary = write_summary_files(tmp_path, ["D0", "D1"])

    assert summary["modes"]["D0"]["passed"] == 0
    assert summary["modes"]["D1"]["passed"] == 1
    assert summary["deltas"][0]["winner"] == "D1"
    assert (tmp_path / "summary.md").exists()


def test_write_summary_files_counts_runtime_error_as_infra(tmp_path: Path) -> None:
    checkpoint = tmp_path / "D0" / "example" / "checkpoint_1"
    checkpoint.mkdir(parents=True)
    (checkpoint / "evaluation.json").write_text(
        json.dumps(
            {
                "pytest_exit_code": 0,
                "infrastructure_failure": False,
                "pass_counts": {"Core": 1},
                "total_counts": {"Core": 1},
            }
        )
    )
    (tmp_path / "D0" / "example" / "infer.log").write_text(
        json.dumps(
            {
                "level": "error",
                "event": (
                    "Error running problem error_message=\"cleanup failed\" "
                    "error_type='PermissionError' problem='example'"
                ),
            }
        )
        + "\n"
    )

    summary = write_summary_files(tmp_path, ["D0"])

    assert summary["modes"]["D0"]["passed"] == 0
    assert summary["modes"]["D0"]["infra_errors"] == 1
    assert summary["checkpoints"][0]["runtime_error"] == "PermissionError: cleanup failed"
