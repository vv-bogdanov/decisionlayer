import json
from pathlib import Path

from decision_layer.poc import PocConfig, run_poc

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
