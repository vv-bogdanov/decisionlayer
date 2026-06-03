from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from memorycore.baselines import get_baseline_runner
from memorycore.benchmarks import get_benchmark
from memorycore.experiments.args import parse_overrides
from memorycore.reporting import write_experiment_outputs
from memorycore.reporting.proof import bootstrap_binary_ci

DEFAULT_CONFIG: dict[str, Any] = {
    "benchmark": "toy",
    "data_path": None,
    "memory": "decisions_plus_facts",
    "compare_memories": "",
    "recall": None,
    "extractor_policy": "rule_based",
    "extractor_model": "gpt-4o-mini",
    "extractor_url": "https://api.openai.com/v1/responses",
    "extractor_max_facts": 12,
    "extractor_max_decisions": 4,
    "top_k_decisions": 5,
    "top_k_facts": 5,
    "limit": None,
    "offset": 0,
    "recall_count_weight": 0.05,
    "keyword_weight": 1.0,
    "recency_weight": 0.0,
    "scope_weight": 0.25,
    "refs_expansion_depth": 0,
    "refs_expansion_limit": 10,
    "max_memory_brief_tokens": None,
    "forgetting_policy": "none",
    "forgetting_threshold": None,
    "input_cost_per_1k": 0.0,
    "output_cost_per_1k": 0.0,
    "judge_policy": "none",
    "judge_model": "gpt-4o-mini",
    "judge_url": "https://api.openai.com/v1/responses",
    "output_dir": "reports/latest",
}

LOCAL_LLAMA_JUDGE_MODEL = "qwen36-35b-a3b-udiq3s"
LOCAL_LLAMA_JUDGE_URL = "http://127.0.0.1:18080/v1/responses"


def run_experiment(config: dict[str, Any]) -> dict[str, Any]:
    merged = dict(DEFAULT_CONFIG)
    merged.update({key: value for key, value in config.items() if value != ""})
    memories = configured_memories(merged)
    if len(memories) > 1:
        return run_comparison(merged, memories)
    return run_single(merged, str(merged["memory"]))


def configured_memories(config: dict[str, Any]) -> list[str]:
    compare = str(config.get("compare_memories") or "").strip()
    if not compare:
        return [str(config["memory"])]
    return [item.strip() for item in compare.split(",") if item.strip()]


def run_comparison(config: dict[str, Any], memories: list[str]) -> dict[str, Any]:
    all_predictions: list[dict[str, Any]] = []
    all_traces: list[dict[str, Any]] = []
    baseline_metrics: list[dict[str, Any]] = []
    for memory in memories:
        child_config = dict(config)
        child_config["memory"] = memory
        child_config["compare_memories"] = ""
        child_config["output_dir"] = str(Path(str(config["output_dir"])) / memory)
        result = run_single(child_config, memory)
        all_predictions.extend(result["predictions"])
        all_traces.extend(result["traces"])
        baseline_metrics.append({"memory": memory, **result["metrics"]})

    metrics: dict[str, Any] = {
        "examples": len(all_predictions),
        "baseline_metrics": baseline_metrics,
        "best_memory": best_memory(baseline_metrics),
    }
    failure_cause_metrics = grouped_failure_cause_metrics(all_predictions)
    if failure_cause_metrics:
        metrics["failure_cause_metrics"] = failure_cause_metrics
    write_experiment_outputs(
        output_dir=Path(str(config["output_dir"])),
        config=config,
        metrics=metrics,
        predictions=all_predictions,
        traces=all_traces,
    )
    return {"config": config, "metrics": metrics, "predictions": all_predictions, "traces": all_traces}


def best_memory(baseline_metrics: list[dict[str, Any]]) -> str | None:
    if not baseline_metrics:
        return None
    best = max(baseline_metrics, key=lambda item: float(item.get("accuracy", 0.0)))
    return str(best["memory"])


def run_single(merged: dict[str, Any], memory: str) -> dict[str, Any]:
    benchmark = get_benchmark(
        str(merged["benchmark"]),
        data_path=merged.get("data_path"),
        limit=optional_int(merged.get("limit")),
        offset=int(merged.get("offset") or 0),
    )
    runner = get_baseline_runner(
        memory,
        extractor_policy=str(merged["extractor_policy"]),
        extractor_model=str(merged["extractor_model"]),
        extractor_url=str(merged["extractor_url"]),
        extractor_max_facts=int(merged["extractor_max_facts"]),
        extractor_max_decisions=int(merged["extractor_max_decisions"]),
        top_k_decisions=int(merged["top_k_decisions"]),
        top_k_facts=int(merged["top_k_facts"]),
        include_refs=int(merged.get("refs_expansion_depth") or 0) > 0,
        refs_expansion_depth=int(merged.get("refs_expansion_depth") or 0),
        refs_expansion_limit=int(merged.get("refs_expansion_limit") or 10),
        max_memory_brief_tokens=optional_int(merged.get("max_memory_brief_tokens")),
        forgetting_policy=configured_forgetting_policy(merged),
        forgetting_threshold=optional_int(merged.get("forgetting_threshold")),
        recall_count_weight=float(merged.get("recall_count_weight") or 0.0),
        keyword_weight=float(merged.get("keyword_weight") or 0.0),
        recency_weight=float(merged.get("recency_weight") or 0.0),
        scope_weight=float(merged.get("scope_weight") or 0.0),
    )
    if merged.get("recall"):
        runner.recall_policy = str(merged["recall"])

    predictions: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    started = time.perf_counter()
    for example in benchmark.iter_examples():
        result = runner.run(example)
        expected_answers = expected_answer_options(example)
        scoring_policy = str(example.meta.get("scoring_policy") or "substring_exact_match")
        exact_match, substring_match = score_prediction(result.answer, expected_answers)
        correct = correct_for_scoring_policy(
            exact_match=exact_match,
            substring_match=substring_match,
            scoring_policy=scoring_policy,
        )
        memory_brief = result.brief.render() if result.brief else ""
        predictions.append(
            {
                "id": example.id,
                "question": example.question,
                "expected_answer": example.expected_answer,
                "expected_answers": expected_answers,
                "prediction": result.answer,
                "correct": correct,
                "exact_match": exact_match,
                "substring_match": substring_match,
                "scoring_policy": scoring_policy,
                "memory": runner.name,
                "memory_brief": memory_brief,
                "question_type": example.meta.get("question_type"),
                "is_abstention": bool(example.meta.get("is_abstention", False)),
                "answer_session_ids": example.meta.get("answer_session_ids", []),
                "haystack_session_ids": example.meta.get("haystack_session_ids", []),
                "probable_failure_cause": probable_failure_cause(
                    correct=correct,
                    expected=example.expected_answer,
                    memory_brief=memory_brief,
                    is_abstention=bool(example.meta.get("is_abstention", False)),
                ),
            }
        )
        if result.trace:
            traces.append(
                {
                    "id": example.id,
                    "question_type": example.meta.get("question_type"),
                    "answer_session_ids": example.meta.get("answer_session_ids", []),
                    "haystack_session_ids": example.meta.get("haystack_session_ids", []),
                    "source_messages": source_messages(example),
                    **result.trace,
                }
            )

    apply_judge(predictions, merged)
    latency = time.perf_counter() - started
    metrics = compute_metrics(predictions, traces, latency, merged)
    write_experiment_outputs(
        output_dir=Path(str(merged["output_dir"])),
        config=merged,
        metrics=metrics,
        predictions=predictions,
        traces=traces,
    )
    return {"config": merged, "metrics": metrics, "predictions": predictions, "traces": traces}


def exact_match_score(prediction: str, expected: str) -> bool:
    prediction_normalized = normalize_text(prediction)
    expected_normalized = normalize_text(expected)
    return prediction_normalized == expected_normalized


def substring_match_score(prediction: str, expected: str) -> bool:
    prediction_normalized = normalize_text(prediction)
    expected_normalized = normalize_text(expected)
    if not prediction_normalized or not expected_normalized:
        return prediction_normalized == expected_normalized
    return expected_normalized in prediction_normalized or prediction_normalized in expected_normalized


def score_prediction(prediction: str, expected_answers: list[str]) -> tuple[bool, bool]:
    exact_match = any(exact_match_score(prediction, expected) for expected in expected_answers)
    substring_match = any(substring_match_score(prediction, expected) for expected in expected_answers)
    return exact_match, substring_match


def correct_for_scoring_policy(
    *,
    exact_match: bool,
    substring_match: bool,
    scoring_policy: str,
) -> bool:
    if scoring_policy == "exact_match":
        return exact_match
    if scoring_policy == "llm_judge_required":
        return False
    return exact_match or substring_match


def expected_answer_options(example: Any) -> list[str]:
    values = example.meta.get("expected_answers")
    if isinstance(values, list):
        options = [str(value) for value in values if str(value)]
        if options:
            return options
    return [example.expected_answer]


def normalize_text(text: str) -> str:
    return " ".join(text.lower().strip().split())


def optional_int(value: object) -> int | None:
    if value in {None, ""}:
        return None
    if not isinstance(value, (str, int, float)):
        return None
    return int(value)


def probable_failure_cause(
    *,
    correct: bool,
    expected: str,
    memory_brief: str,
    is_abstention: bool,
) -> str:
    if correct:
        return ""
    if is_abstention:
        return "abstention"
    if not memory_brief.strip():
        return "recall"
    if normalize_text(expected) and normalize_text(expected) in normalize_text(memory_brief):
        return "scoring"
    return "extraction_or_recall"


def source_messages(example: Any) -> list[dict[str, Any]]:
    return [
        {
            "role": message.role,
            "content": message.content,
            "scope": message.scope,
            "meta": message.meta,
        }
        for message in example.messages
    ]


def apply_judge(predictions: list[dict[str, Any]], config: dict[str, Any]) -> None:
    policy = str(config.get("judge_policy") or "none")
    if policy == "none":
        return
    if policy not in {"llm", "llama_cpp"}:
        raise ValueError(f"unknown judge_policy: {policy}")
    api_key = os.environ.get("OPENAI_API_KEY") if policy == "llm" else None
    if policy == "llm" and not api_key:
        raise RuntimeError("judge_policy=llm requires OPENAI_API_KEY")
    model = str(config["judge_model"])
    url = str(config["judge_url"])
    if policy == "llama_cpp":
        if model == str(DEFAULT_CONFIG["judge_model"]):
            model = LOCAL_LLAMA_JUDGE_MODEL
        if url == str(DEFAULT_CONFIG["judge_url"]):
            url = LOCAL_LLAMA_JUDGE_URL
    for prediction in predictions:
        label = llm_judge_prediction(
            question=str(prediction["question"]),
            expected=str(prediction["expected_answer"]),
            prediction=str(prediction["prediction"]),
            model=model,
            url=url,
            api_key=api_key,
        )
        prediction["judge_label"] = label
        prediction["judge_score"] = 1.0 if label == "correct" else 0.0
        if prediction.get("scoring_policy") == "llm_judge_required":
            prediction["correct"] = label == "correct"


def llm_judge_prediction(
    *,
    question: str,
    expected: str,
    prediction: str,
    model: str,
    url: str,
    api_key: str | None,
) -> str:
    prompt = (
        "Judge whether the prediction answers the question with the same meaning as the expected answer. "
        "Return only 'correct' or 'incorrect'.\n\n"
        f"Question: {question}\nExpected: {expected}\nPrediction: {prediction}"
    )
    payload = json.dumps({"model": model, "input": prompt}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(url, data=payload, headers=headers, method="POST")
    with urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    output_text = extract_response_text(data).lower()
    return "correct" if "correct" in output_text and "incorrect" not in output_text else "incorrect"


def extract_response_text(data: dict[str, Any]) -> str:
    if isinstance(data.get("output_text"), str):
        return str(data["output_text"])
    chunks: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks)


def compute_metrics(
    predictions: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    latency: float,
    config: dict[str, Any],
) -> dict[str, Any]:
    total = len(predictions)
    correct = sum(1 for item in predictions if item["correct"])
    exact_matches = sum(1 for item in predictions if item["exact_match"])
    substring_matches = sum(1 for item in predictions if item["substring_match"])
    decision_counts = [len(trace.get("decisions", [])) for trace in traces]
    fact_counts = [len(trace.get("facts", [])) for trace in traces]
    brief_token_counts = [token_count(item.get("memory_brief", "")) for item in predictions]
    output_token_counts = [token_count(item.get("prediction", "")) for item in predictions]
    source_traceability = source_traceability_rate(traces)
    prompt_tokens = sum(brief_token_counts)
    output_tokens = sum(output_token_counts)
    metrics: dict[str, Any] = {
        "accuracy": round(correct / total, 6) if total else 0.0,
        "exact_match": round(exact_matches / total, 6) if total else 0.0,
        "substring_match": round(substring_matches / total, 6) if total else 0.0,
        "examples": total,
        "correct": correct,
        "latency_seconds": round(latency, 6),
        "memory_brief_tokens": round(avg(brief_token_counts), 6),
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "cost_estimate_usd": round(
            prompt_tokens * float(config.get("input_cost_per_1k") or 0.0) / 1000
            + output_tokens * float(config.get("output_cost_per_1k") or 0.0) / 1000,
            6,
        ),
        "decisions_selected_per_recall": round(avg(decision_counts), 6),
        "facts_selected_per_recall": round(avg(fact_counts), 6),
        "source_traceability": round(source_traceability, 6),
        "false_decision_rate": 0.0,
    }
    accuracy_ci_low, accuracy_ci_high = bootstrap_binary_ci([bool(item["correct"]) for item in predictions])
    metrics["accuracy_ci_low"] = accuracy_ci_low
    metrics["accuracy_ci_high"] = accuracy_ci_high
    metrics["quality_score"] = composite_quality_score(metrics)
    metrics["objectives"] = {
        "accuracy": metrics["accuracy"],
        "source_traceability": metrics["source_traceability"],
        "memory_brief_tokens": metrics["memory_brief_tokens"],
        "cost_estimate_usd": metrics["cost_estimate_usd"],
    }
    type_metrics = grouped_metrics(predictions, "question_type")
    if type_metrics:
        metrics["question_type_metrics"] = type_metrics
    scoring_policy_metrics = grouped_metrics(predictions, "scoring_policy")
    if scoring_policy_metrics:
        metrics["scoring_policy_metrics"] = scoring_policy_metrics
    failure_cause_metrics = grouped_failure_cause_metrics(predictions)
    if failure_cause_metrics:
        metrics["failure_cause_metrics"] = failure_cause_metrics
    judge_predictions = [item for item in predictions if "judge_score" in item]
    if judge_predictions:
        metrics["judge_score"] = round(
            sum(float(item["judge_score"]) for item in judge_predictions) / len(judge_predictions),
            6,
        )
    abstention_predictions = [item for item in predictions if item.get("is_abstention")]
    if abstention_predictions:
        metrics["abstention_accuracy"] = round(
            sum(1 for item in abstention_predictions if item["correct"]) / len(abstention_predictions),
            6,
        )
    return metrics


def grouped_failure_cause_metrics(predictions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    failures = [item for item in predictions if not item.get("correct")]
    if not failures:
        return {}
    groups: dict[str, list[dict[str, Any]]] = {}
    for prediction in failures:
        cause = str(prediction.get("probable_failure_cause") or "unknown")
        groups.setdefault(cause, []).append(prediction)
    total = len(predictions)
    failure_total = len(failures)
    return {
        cause: {
            "failures": len(rows),
            "failure_share": round(len(rows) / failure_total, 6) if failure_total else 0.0,
            "dataset_share": round(len(rows) / total, 6) if total else 0.0,
        }
        for cause, rows in sorted(groups.items())
    }


def configured_forgetting_policy(config: dict[str, Any]) -> str | None:
    policy = str(config.get("forgetting_policy") or "none")
    if policy != "none":
        return policy
    if optional_int(config.get("forgetting_threshold")) is not None:
        return "low_recall_count_except_decision_refs"
    return None


def composite_quality_score(metrics: dict[str, Any]) -> float:
    accuracy = float(metrics.get("accuracy", 0.0))
    traceability = float(metrics.get("source_traceability", 0.0))
    brief_tokens = float(metrics.get("memory_brief_tokens", 0.0))
    cost = float(metrics.get("cost_estimate_usd", 0.0))
    token_penalty = min(brief_tokens / 4000.0, 1.0) * 0.1
    cost_penalty = min(cost, 1.0) * 0.05
    return round(accuracy + 0.1 * traceability - token_penalty - cost_penalty, 6)


def avg(values: list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def token_count(text: object) -> int:
    return len(str(text).split())


def grouped_metrics(
    predictions: list[dict[str, Any]],
    key: str,
) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for prediction in predictions:
        value = prediction.get(key)
        if not value:
            continue
        groups.setdefault(str(value), []).append(prediction)
    metrics: dict[str, dict[str, Any]] = {}
    for group, rows in sorted(groups.items()):
        total = len(rows)
        correct = sum(1 for item in rows if item["correct"])
        metrics[group] = {
            "examples": total,
            "accuracy": round(correct / total, 6) if total else 0.0,
            "exact_match": round(sum(1 for item in rows if item["exact_match"]) / total, 6) if total else 0.0,
            "substring_match": round(sum(1 for item in rows if item["substring_match"]) / total, 6) if total else 0.0,
        }
    return metrics


def source_traceability_rate(traces: list[dict[str, Any]]) -> float:
    selected = 0
    with_source = 0
    for trace in traces:
        for item in trace.get("decisions", []) + trace.get("facts", []):
            selected += 1
            refs = item.get("refs", [])
            if any(ref.get("rel") == "source" for ref in refs if isinstance(ref, dict)):
                with_source += 1
    return with_source / selected if selected else 0.0


def main(argv: list[str] | None = None) -> None:
    overrides = parse_overrides(list(sys.argv[1:] if argv is None else argv))
    result = run_experiment(overrides)
    print(result["metrics"])


if __name__ == "__main__":
    main()
