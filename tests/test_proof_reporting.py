import json
from pathlib import Path

from memorycore.experiments.aggregate_proof import main as aggregate_proof_main
from memorycore.experiments.run_experiment import run_experiment
from memorycore.reporting.proof import bootstrap_binary_ci

FIXTURE_DIR = Path(__file__).parent / "fixtures"
MEMORYAGENTBENCH_FIXTURE = FIXTURE_DIR / "memoryagentbench_sample.json"


def test_bootstrap_binary_ci_is_deterministic() -> None:
    assert bootstrap_binary_ci([True, False, True], n_samples=50, seed=1) == bootstrap_binary_ci(
        [True, False, True],
        n_samples=50,
        seed=1,
    )


def test_manifest_contains_reproducibility_fields(tmp_path: Path) -> None:
    run_experiment({"benchmark": "toy", "memory": "decisions_facts", "output_dir": str(tmp_path)})

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert "git" in manifest
    assert manifest["run"]["benchmark"] == "toy"
    assert manifest["run"]["predictions_count"] == 2
    assert manifest["run"]["prediction_ids"] == ["toy-1", "toy-2"]
    assert manifest["model_config"]["extractor_policy"] == "rule_based"


def test_aggregate_proof_writes_index(tmp_path: Path) -> None:
    proof_root = tmp_path / "proof"
    run_experiment(
        {
            "benchmark": "toy",
            "memory": "decisions_facts",
            "output_dir": str(proof_root / "toy_run"),
        }
    )

    aggregate_proof_main([str(proof_root)])

    index = (proof_root / "index.md").read_text(encoding="utf-8")
    assert "Proof Run Index" in index
    assert "toy_run" in index
    assert "decisions_facts" in index


def test_aggregate_proof_summarizes_comparison_runs(tmp_path: Path) -> None:
    proof_root = tmp_path / "proof"
    run_experiment(
        {
            "benchmark": "toy",
            "compare_memories": "no_memory,decisions_facts",
            "output_dir": str(proof_root / "toy_compare"),
        }
    )

    aggregate_proof_main([str(proof_root)])

    index = (proof_root / "index.md").read_text(encoding="utf-8")
    assert "Baseline And Ablation Summary" in index
    assert "Cost/Latency Pareto Candidates" in index
    assert "no_memory" in index
    summary = index.split("## Baseline And Ablation Summary", 1)[1]
    assert "toy_compare/no_memory" not in summary


def test_aggregate_proof_summarizes_memoryagentbench_competencies(tmp_path: Path) -> None:
    proof_root = tmp_path / "proof"
    run_experiment(
        {
            "benchmark": "memoryagentbench",
            "data_path": str(MEMORYAGENTBENCH_FIXTURE),
            "compare_memories": "no_memory,decisions_facts",
            "output_dir": str(proof_root / "memoryagentbench_smoke"),
        }
    )

    aggregate_proof_main([str(proof_root)])

    index = (proof_root / "index.md").read_text(encoding="utf-8")
    assert "MemoryAgentBench Competency Summary" in index
    assert "memoryagentbench_sample" in index
