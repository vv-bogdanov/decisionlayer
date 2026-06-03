import json
from pathlib import Path

import pytest

import memorycore.experiments.run_experiment as run_experiment_module
from memorycore.benchmarks import get_benchmark
from memorycore.benchmarks.memoryagentbench import (
    record_to_memoryagentbench_examples,
    scoring_policy_for_memoryagentbench,
)
from memorycore.experiments.run_experiment import (
    correct_for_scoring_policy,
    run_experiment,
    score_prediction,
    substring_match_score,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"
LONGMEMEVAL_FIXTURE = FIXTURE_DIR / "longmemeval_oracle_sample.json"
LOCOMO_FIXTURE = FIXTURE_DIR / "locomo_sample.json"
HALUMEM_FIXTURE = FIXTURE_DIR / "halumem_sample.jsonl"
MEMORYAGENTBENCH_FIXTURE = FIXTURE_DIR / "memoryagentbench_sample.json"


class ArrayLike:
    def __init__(self, values: list[str]) -> None:
        self.values = values

    def tolist(self) -> list[str]:
        return self.values


class FakeJudgeResponse:
    def __enter__(self) -> "FakeJudgeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return b'{"output":[{"content":[{"text":"correct"}]}]}'


def test_toy_benchmark_loads_examples() -> None:
    benchmark = get_benchmark("toy")
    examples = benchmark.load()

    assert len(examples) == 2
    assert examples[0].question
    assert examples[0].expected_answer == "SQLite"


def test_empty_prediction_does_not_match_non_empty_answer() -> None:
    assert substring_match_score("", "GPS system not functioning correctly") is False
    assert substring_match_score("", "") is True


def test_longmemeval_default_fixture_runs(tmp_path: Path) -> None:
    result = run_experiment(
        {
            "benchmark": "longmemeval",
            "memory": "decisions_facts",
            "recall": "decision_first",
            "output_dir": str(tmp_path),
        }
    )

    assert result["metrics"]["examples"] == 2
    assert (tmp_path / "metrics.json").exists()
    assert (tmp_path / "predictions.jsonl").exists()
    assert (tmp_path / "trace.jsonl").exists()
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "report.md").exists()
    assert "accuracy_ci_low" in result["metrics"]
    assert "accuracy_ci_high" in result["metrics"]


def test_cost_estimate_uses_configured_token_prices(tmp_path: Path) -> None:
    result = run_experiment(
        {
            "benchmark": "toy",
            "memory": "decisions_facts",
            "input_cost_per_1k": 1.0,
            "output_cost_per_1k": 2.0,
            "output_dir": str(tmp_path),
        }
    )

    assert result["metrics"]["prompt_tokens"] > 0
    assert result["metrics"]["output_tokens"] > 0
    assert result["metrics"]["cost_estimate_usd"] > 0
    assert result["metrics"]["quality_score"] > 0
    assert result["metrics"]["objectives"]["accuracy"] == result["metrics"]["accuracy"]


def test_llm_judge_is_behind_explicit_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        run_experiment(
            {
                "benchmark": "toy",
                "memory": "decisions_facts",
                "judge_policy": "llm",
                "output_dir": str(tmp_path),
            }
        )


def test_llama_cpp_judge_uses_local_responses_api_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request: object, timeout: int) -> FakeJudgeResponse:
        del timeout
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeJudgeResponse()

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(run_experiment_module, "urlopen", fake_urlopen)

    result = run_experiment(
        {
            "benchmark": "toy",
            "memory": "decisions_facts",
            "judge_policy": "llama_cpp",
            "output_dir": str(tmp_path),
        }
    )

    assert result["metrics"]["judge_score"] == 1.0
    assert captured["url"] == "http://127.0.0.1:18080/v1/responses"
    assert captured["payload"]["model"] == "qwen36-35b-a3b-udiq3s"
    assert "Authorization" not in captured["headers"]


def test_longmemeval_real_schema_fixture_parses_and_windows() -> None:
    benchmark = get_benchmark(
        "longmemeval",
        data_path=str(LONGMEMEVAL_FIXTURE),
        limit=1,
        offset=1,
    )
    examples = benchmark.load()

    assert len(examples) == 1
    example = examples[0]
    assert example.id == "sample_002"
    assert example.scope == "longmemeval:sample_002"
    assert example.meta["question_type"] == "temporal-reasoning"
    assert example.meta["answer_session_ids"] == ["session_car_1"]
    assert len(example.messages) == 2
    assert example.messages[0].meta["session_id"] == "session_car_1"
    assert example.messages[0].meta["has_answer"] is True


def test_longmemeval_real_schema_run_has_grouped_metrics_and_source_refs(tmp_path: Path) -> None:
    result = run_experiment(
        {
            "benchmark": "longmemeval",
            "data_path": str(LONGMEMEVAL_FIXTURE),
            "memory": "decisions_facts",
            "recall": "decision_first",
            "limit": 3,
            "output_dir": str(tmp_path),
        }
    )

    assert result["metrics"]["examples"] == 3
    assert "question_type_metrics" in result["metrics"]
    assert "temporal-reasoning" in result["metrics"]["question_type_metrics"]
    assert "abstention_accuracy" in result["metrics"]
    assert result["predictions"][0]["question_type"] == "single-session-user"
    assert result["traces"][0]["facts"][0]["refs"][0]["rel"] == "source"
    assert result["traces"][0]["source_messages"][0]["content"] == "I had oatmeal for breakfast today."
    manifest = (tmp_path / "manifest.json").read_text(encoding="utf-8")
    assert "longmemeval_oracle_sample.json" in manifest
    assert "sha256" in manifest
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "Question Type Metrics" in report


def test_baseline_comparison_report_runs(tmp_path: Path) -> None:
    result = run_experiment(
        {
            "benchmark": "longmemeval",
            "compare_memories": "recent_context_only,simple_rag,fact_only,decisions_facts",
            "output_dir": str(tmp_path),
        }
    )

    assert len(result["metrics"]["baseline_metrics"]) == 4
    assert result["metrics"]["best_memory"]
    assert "failure_cause_metrics" in result["metrics"]
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "Policy Comparison" in report
    assert "Failure Cause Metrics" in report
    assert "Traceability" in report


def test_real_schema_baseline_comparison_report_runs(tmp_path: Path) -> None:
    result = run_experiment(
        {
            "benchmark": "longmemeval",
            "data_path": str(LONGMEMEVAL_FIXTURE),
            "compare_memories": "recent_context_only,simple_rag,fact_only,decisions_facts",
            "limit": 2,
            "output_dir": str(tmp_path),
        }
    )

    assert len(result["metrics"]["baseline_metrics"]) == 4
    assert result["predictions"][0]["haystack_session_ids"]
    assert "Policy Comparison" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_locomo_real_schema_fixture_expands_qa_examples() -> None:
    benchmark = get_benchmark("locomo", data_path=str(LOCOMO_FIXTURE))
    examples = benchmark.load()

    assert len(examples) == 1
    example = examples[0]
    assert example.id == "conv-test:qa:0"
    assert example.scope == "locomo:conv-test"
    assert example.expected_answer == "7 May 2023"
    assert example.meta["evidence"] == ["D1:1"]
    assert example.messages[0].meta["dia_id"] == "D1:1"
    assert example.messages[0].meta["session_date_time"] == "2023-05-07"


def test_halumem_real_schema_fixture_creates_memory_point_examples() -> None:
    benchmark = get_benchmark("halumem", data_path=str(HALUMEM_FIXTURE))
    examples = benchmark.load()

    assert len(examples) == 1
    example = examples[0]
    assert example.id == "halu-test:memory:3"
    assert example.expected_answer == "Martin Mark works at Huaxin Consulting"
    assert example.meta["memory_type"] == "Persona Memory"
    assert example.messages[-1].role == "memory"
    assert example.messages[-1].meta["source_kind"] == "memory_point"


def test_memoryagentbench_schema_fixture_expands_question_arrays() -> None:
    benchmark = get_benchmark("memoryagentbench", data_path=str(MEMORYAGENTBENCH_FIXTURE))
    examples = benchmark.load()

    assert len(examples) == 1
    example = examples[0]
    assert example.id == "mab-test-1"
    assert example.expected_answer == "Huaxin Consulting"
    assert example.meta["source"] == "Accurate_Retrieval"
    assert example.messages[0].meta["has_answer"] is True
    assert example.meta["scoring_policy"] == "substring_exact_match"


def test_memoryagentbench_report_includes_scoring_policy_metrics(tmp_path: Path) -> None:
    run_experiment(
        {
            "benchmark": "memoryagentbench",
            "data_path": str(MEMORYAGENTBENCH_FIXTURE),
            "memory": "decisions_facts",
            "output_dir": str(tmp_path),
        }
    )

    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "Scoring Policy Metrics" in report


def test_memoryagentbench_array_answers_are_kept_as_aliases() -> None:
    examples = record_to_memoryagentbench_examples(
        {
            "questions": ["Where is Normandy located?"],
            "answers": [ArrayLike(["France", "Republic of France"])],
            "metadata": {
                "source": "Accurate_Retrieval",
                "qa_pair_ids": ["mab-answer-alias"],
            },
        },
        row_index=0,
    )

    assert examples[0].expected_answer == "France"
    assert examples[0].meta["expected_answers"] == ["France", "Republic of France"]


def test_score_prediction_accepts_expected_answer_aliases() -> None:
    exact_match, substring_match = score_prediction("Republic of France", ["France", "Republic of France"])

    assert exact_match is True
    assert substring_match is True


def test_memoryagentbench_scoring_policy_mapping() -> None:
    assert (
        scoring_policy_for_memoryagentbench(source="factconsolidation_mh_6k", question_type=None)
        == "substring_exact_match"
    )
    assert scoring_policy_for_memoryagentbench(source="recsys_redial_full", question_type=None) == "exact_match"
    assert (
        scoring_policy_for_memoryagentbench(source="icl_banking77_5900shot_balance", question_type=None)
        == "exact_match"
    )
    assert (
        scoring_policy_for_memoryagentbench(source="infbench_sum_eng_shots2", question_type=None)
        == "llm_judge_required"
    )


def test_exact_scoring_policy_does_not_accept_substring_only_matches() -> None:
    assert (
        correct_for_scoring_policy(
            exact_match=False,
            substring_match=True,
            scoring_policy="substring_exact_match",
        )
        is True
    )
    assert (
        correct_for_scoring_policy(
            exact_match=False,
            substring_match=True,
            scoring_policy="exact_match",
        )
        is False
    )


def test_real_schema_smoke_runs_for_additional_benchmarks(tmp_path: Path) -> None:
    for benchmark_name, data_path in (
        ("locomo", LOCOMO_FIXTURE),
        ("halumem", HALUMEM_FIXTURE),
        ("memoryagentbench", MEMORYAGENTBENCH_FIXTURE),
    ):
        result = run_experiment(
            {
                "benchmark": benchmark_name,
                "data_path": str(data_path),
                "memory": "decisions_facts",
                "recall": "hybrid",
                "limit": 1,
                "output_dir": str(tmp_path / benchmark_name),
            }
        )

        assert result["metrics"]["examples"] == 1
        assert result["traces"][0]["source_messages"]
