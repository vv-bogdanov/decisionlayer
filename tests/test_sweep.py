from pathlib import Path

from memorycore.experiments.run_sweep import run_sweep


def test_sweep_writes_expected_outputs(tmp_path: Path) -> None:
    result = run_sweep(
        {
            "benchmark": "toy",
            "memory": "decisions_facts",
            "search": "grid",
            "n_trials": 2,
            "top_k_facts_min": 1,
            "top_k_facts_max": 2,
            "top_k_decisions_min": 1,
            "top_k_decisions_max": 2,
            "output_dir": str(tmp_path),
        }
    )

    assert len(result["trials"]) == 2
    assert "recall_count_weight" in result["trials"][0]
    assert "quality_score" in result["trials"][0]
    assert (tmp_path / "best_config.yaml").exists()
    assert (tmp_path / "trials.csv").exists()
    assert (tmp_path / "sweep_report.md").exists()
