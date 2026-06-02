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

