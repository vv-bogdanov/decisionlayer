import json
from pathlib import Path

from decision_layer.poc import PocConfig, PocSuiteConfig, run_poc, run_poc_suite

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "longmemeval_v2"


def test_run_poc_writes_required_artifacts_for_all_modes(tmp_path: Path) -> None:
    oracle_path = FIXTURE_ROOT / "oracle_decisions.json"

    for mode in ("D0", "D1", "D2"):
        output_dir = tmp_path / mode
        result = run_poc(
            PocConfig(
                data_root=FIXTURE_ROOT,
                output_dir=output_dir,
                mode=mode,
                limit=1,
                oracle_decisions_path=oracle_path,
            )
        )

        assert result.metrics["examples"] == 1
        assert (output_dir / "config.json").exists()
        assert (output_dir / "manifest.json").exists()
        assert (output_dir / "metrics.json").exists()
        assert (output_dir / "predictions.jsonl").exists()
        assert (output_dir / "decision_trace.jsonl").exists()
        assert (output_dir / "brief_trace.jsonl").exists()
        assert (output_dir / "report.md").exists()

    d0_metrics = json.loads((tmp_path / "D0" / "metrics.json").read_text(encoding="utf-8"))
    d1_metrics = json.loads((tmp_path / "D1" / "metrics.json").read_text(encoding="utf-8"))
    d2_metrics = json.loads((tmp_path / "D2" / "metrics.json").read_text(encoding="utf-8"))

    assert d0_metrics["non_empty_decision_briefs"] == 0
    assert d1_metrics["non_empty_decision_briefs"] == 1
    assert d2_metrics["non_empty_decision_briefs"] == 1
    assert d2_metrics["processed_messages"] == 1
    assert d2_metrics["decision_candidates"] == 1
    assert d2_metrics["decision_add_events"] == 1


def test_run_poc_suite_writes_comparison_report(tmp_path: Path) -> None:
    result = run_poc_suite(
        PocSuiteConfig(
            data_root=FIXTURE_ROOT,
            output_dir=tmp_path,
            limit=1,
            oracle_decisions_path=FIXTURE_ROOT / "oracle_decisions.json",
        )
    )

    assert "delta_D1_minus_D0" in result.metrics
    assert (tmp_path / "suite_metrics.json").exists()
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "D0" / "metrics.json").exists()
    assert (tmp_path / "D1" / "metrics.json").exists()
    assert (tmp_path / "D2" / "metrics.json").exists()
    assert "Decision Layer POC Suite Report" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_run_poc_manifest_records_explicit_subset(tmp_path: Path) -> None:
    output_dir = tmp_path / "D0"
    run_poc(
        PocConfig(
            data_root=FIXTURE_ROOT,
            output_dir=output_dir,
            mode="D0",
            question_ids=("q_workflow",),
        )
    )

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    config = json.loads((output_dir / "config.json").read_text(encoding="utf-8"))

    assert manifest["source_question_rows"] == 2
    assert manifest["source_haystack_entries"] == 2
    assert manifest["selected_question_count"] == 1
    assert manifest["question_ids"] == ["q_workflow"]
    assert manifest["requested_question_ids"] == ["q_workflow"]
    assert manifest["selected_trajectory_count"] == 1
    assert config["question_ids"] == ["q_workflow"]


def test_run_poc_logs_decision_trace_and_final_decisions(tmp_path: Path) -> None:
    output_dir = tmp_path / "D2"
    run_poc(
        PocConfig(
            data_root=FIXTURE_ROOT,
            output_dir=output_dir,
            mode="D2",
            question_ids=("q_static",),
        )
    )

    decision_trace = [
        json.loads(line)
        for line in (output_dir / "decision_trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    brief_trace = [
        json.loads(line)
        for line in (output_dir / "brief_trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert any(trace["event"] == "message_processed" for trace in decision_trace)
    assert any(trace["event"] == "decision_candidate" for trace in decision_trace)
    assert any(trace["event"] == "decision_added" for trace in decision_trace)
    assert brief_trace[0]["final_decisions"][0]["text"] == (
        "use Guest checkout as the default checkout option"
    )
