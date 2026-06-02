from pathlib import Path

from memorycore.benchmarks import get_benchmark
from memorycore.experiments.run_experiment import run_experiment


def test_toy_benchmark_loads_examples() -> None:
    benchmark = get_benchmark("toy")
    examples = benchmark.load()

    assert len(examples) == 2
    assert examples[0].question
    assert examples[0].expected_answer == "SQLite"


def test_longmemeval_default_fixture_runs(tmp_path: Path) -> None:
    result = run_experiment(
        {
            "benchmark": "longmemeval",
            "memory": "decisions_plus_facts",
            "recall": "decision_first",
            "output_dir": str(tmp_path),
        }
    )

    assert result["metrics"]["examples"] == 2
    assert (tmp_path / "metrics.json").exists()
    assert (tmp_path / "predictions.jsonl").exists()
    assert (tmp_path / "trace.jsonl").exists()
    assert (tmp_path / "report.md").exists()


def test_baseline_comparison_report_runs(tmp_path: Path) -> None:
    result = run_experiment(
        {
            "benchmark": "longmemeval",
            "compare_memories": "recent_context_only,simple_rag,fact_only,decisions_plus_facts",
            "output_dir": str(tmp_path),
        }
    )

    assert len(result["metrics"]["baseline_metrics"]) == 4
    assert result["metrics"]["best_memory"]
    assert "Policy Comparison" in (tmp_path / "report.md").read_text(encoding="utf-8")
