from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

from memorycore.baselines import get_baseline_runner
from memorycore.benchmarks import get_benchmark
from memorycore.experiments.args import parse_overrides
from memorycore.reporting import write_experiment_outputs


DEFAULT_CONFIG: dict[str, Any] = {
    "benchmark": "toy",
    "data_path": None,
    "memory": "decisions_plus_facts",
    "recall": None,
    "extractor_policy": "rule_based",
    "top_k_decisions": 5,
    "top_k_facts": 5,
    "output_dir": "reports/latest",
}


def run_experiment(config: dict[str, Any]) -> dict[str, Any]:
    merged = dict(DEFAULT_CONFIG)
    merged.update({key: value for key, value in config.items() if value != ""})
    benchmark = get_benchmark(str(merged["benchmark"]), data_path=merged.get("data_path"))
    runner = get_baseline_runner(
        str(merged["memory"]),
        extractor_policy=str(merged["extractor_policy"]),
        top_k_decisions=int(merged["top_k_decisions"]),
        top_k_facts=int(merged["top_k_facts"]),
    )
    if merged.get("recall"):
        runner.recall_policy = str(merged["recall"])

    predictions: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    started = time.perf_counter()
    for example in benchmark.iter_examples():
        result = runner.run(example)
        correct = score_prediction(result.answer, example.expected_answer)
        predictions.append(
            {
                "id": example.id,
                "question": example.question,
                "expected_answer": example.expected_answer,
                "prediction": result.answer,
                "correct": correct,
                "memory": runner.name,
            }
        )
        if result.trace:
            traces.append({"id": example.id, **result.trace})

    latency = time.perf_counter() - started
    metrics = compute_metrics(predictions, traces, latency)
    write_experiment_outputs(
        output_dir=Path(str(merged["output_dir"])),
        config=merged,
        metrics=metrics,
        predictions=predictions,
        traces=traces,
    )
    return {"config": merged, "metrics": metrics, "predictions": predictions, "traces": traces}


def score_prediction(prediction: str, expected: str) -> bool:
    prediction_normalized = normalize_text(prediction)
    expected_normalized = normalize_text(expected)
    if not expected_normalized:
        return not prediction_normalized
    return expected_normalized in prediction_normalized or prediction_normalized in expected_normalized


def normalize_text(text: str) -> str:
    return " ".join(text.lower().strip().split())


def compute_metrics(
    predictions: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    latency: float,
) -> dict[str, Any]:
    total = len(predictions)
    correct = sum(1 for item in predictions if item["correct"])
    decision_counts = [len(trace.get("decisions", [])) for trace in traces]
    fact_counts = [len(trace.get("facts", [])) for trace in traces]
    source_traceability = source_traceability_rate(traces)
    return {
        "accuracy": round(correct / total, 6) if total else 0.0,
        "examples": total,
        "correct": correct,
        "latency_seconds": round(latency, 6),
        "decisions_selected_per_recall": round(avg(decision_counts), 6),
        "facts_selected_per_recall": round(avg(fact_counts), 6),
        "source_traceability": round(source_traceability, 6),
        "false_decision_rate": 0.0,
    }


def avg(values: list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def source_traceability_rate(traces: list[dict[str, Any]]) -> float:
    selected = 0
    with_source = 0
    for trace in traces:
        for item in trace.get("decisions", []) + trace.get("facts", []):
            selected += 1
            if item.get("id"):
                with_source += 1
    return with_source / selected if selected else 0.0


def main(argv: list[str] | None = None) -> None:
    overrides = parse_overrides(list(sys.argv[1:] if argv is None else argv))
    result = run_experiment(overrides)
    print(result["metrics"])


if __name__ == "__main__":
    main()

