from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Literal

from decision_layer.benchmarks.longmemeval_v2 import (
    LongMemEvalV2Example,
    load_longmemeval_v2_examples,
)
from decision_layer.core import DecisionState, add_decision, render_decision_brief
from decision_layer.extraction import RuleBasedDecisionExtractor, SourceMessage

PocMode = Literal["D0", "D1", "D2"]


@dataclass(frozen=True, slots=True)
class PocConfig:
    data_root: Path
    output_dir: Path
    mode: PocMode
    tier: str = "small"
    limit: int | None = None
    oracle_decisions_path: Path | None = None


@dataclass(frozen=True, slots=True)
class PocResult:
    metrics: dict[str, object]
    predictions: list[dict[str, object]]
    decision_trace: list[dict[str, object]]
    brief_trace: list[dict[str, object]]


@dataclass(frozen=True, slots=True)
class PocSuiteConfig:
    data_root: Path
    output_dir: Path
    tier: str = "small"
    limit: int | None = None
    oracle_decisions_path: Path | None = None


@dataclass(frozen=True, slots=True)
class PocSuiteResult:
    metrics: dict[str, object]
    mode_results: dict[PocMode, PocResult]


def run_poc(config: PocConfig) -> PocResult:
    start = perf_counter()
    examples = load_longmemeval_v2_examples(
        config.data_root,
        tier=config.tier,
        limit=config.limit,
    )
    oracle_decisions = load_oracle_decisions(config.oracle_decisions_path)
    extractor = RuleBasedDecisionExtractor()
    predictions: list[dict[str, object]] = []
    decision_trace: list[dict[str, object]] = []
    brief_trace: list[dict[str, object]] = []

    for example in examples:
        state = DecisionState()
        if config.mode == "D1":
            state, traces = apply_oracle_decisions(state, example, oracle_decisions)
            decision_trace.extend(traces)
        elif config.mode == "D2":
            state, traces = apply_automatic_decisions(state, example, extractor)
            decision_trace.extend(traces)

        brief = render_decision_brief(state)
        context = retrieve_keyword_context(example)
        augmented_context = context if config.mode == "D0" else f"{brief.text}\n\n{context}"
        prediction = smoke_oracle_substring_reader(augmented_context, example.question.answer)
        correct = normalize(prediction) == normalize(example.question.answer)

        predictions.append(
            {
                "id": example.question.id,
                "mode": config.mode,
                "question": example.question.question,
                "question_type": example.question.question_type,
                "expected_answer": example.question.answer,
                "prediction": prediction,
                "correct": correct,
                "decision_count": len(brief.decisions),
                "brief_tokens": brief.token_count,
                "reader_policy": "smoke_oracle_substring_reader",
            }
        )
        brief_trace.append(
            {
                "id": example.question.id,
                "mode": config.mode,
                "decision_ids": [decision.id for decision in brief.decisions],
                "brief": brief.text,
                "brief_tokens": brief.token_count,
            }
        )

    metrics = compute_metrics(predictions, start)
    result = PocResult(metrics, predictions, decision_trace, brief_trace)
    write_artifacts(config, examples, result)
    return result


def run_poc_suite(config: PocSuiteConfig) -> PocSuiteResult:
    mode_results: dict[PocMode, PocResult] = {}
    for mode in ("D0", "D1", "D2"):
        mode_results[mode] = run_poc(
            PocConfig(
                data_root=config.data_root,
                output_dir=config.output_dir / mode,
                mode=mode,
                tier=config.tier,
                limit=config.limit,
                oracle_decisions_path=config.oracle_decisions_path,
            )
        )
    suite_metrics = compute_suite_metrics(mode_results)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(config.output_dir / "suite_metrics.json", suite_metrics)
    (config.output_dir / "report.md").write_text(
        render_suite_report(config, suite_metrics),
        encoding="utf-8",
    )
    return PocSuiteResult(suite_metrics, mode_results)


def apply_oracle_decisions(
    state: DecisionState,
    example: LongMemEvalV2Example,
    oracle_decisions: dict[str, list[str]],
) -> tuple[DecisionState, list[dict[str, object]]]:
    traces = []
    for index, text in enumerate(oracle_decisions.get(example.question.id, [])):
        state, trace = add_decision(
            state,
            text,
            authority="manual_api_commit",
            decision_id=f"{example.question.id}_oracle_{index}",
            meta={"source_message_id": f"{example.question.id}:oracle:{index}"},
        )
        traces.append(trace.to_dict())
    return state, traces


def apply_automatic_decisions(
    state: DecisionState,
    example: LongMemEvalV2Example,
    extractor: RuleBasedDecisionExtractor,
) -> tuple[DecisionState, list[dict[str, object]]]:
    traces = []
    for trajectory in example.trajectories:
        message = SourceMessage(
            id=f"{trajectory.id}:goal",
            role="user",
            content=trajectory.goal,
            source_kind="chat",
        )
        for command in extractor.extract(message):
            if command.action != "add":
                continue
            state, trace = add_decision(
                state,
                command.text,
                authority="user_commit",
                meta={"source_message_id": command.source_message_id},
            )
            traces.append(trace.to_dict())
    return state, traces


def retrieve_keyword_context(example: LongMemEvalV2Example, *, max_items: int = 4) -> str:
    query_terms = set(normalize(example.question.question).split())
    scored = []
    for trajectory in example.trajectories:
        for state in trajectory.states:
            text = state_text(trajectory.goal, state)
            terms = set(normalize(text).split())
            score = len(query_terms & terms)
            scored.append((score, text))
    selected = sorted(scored, key=lambda item: item[0], reverse=True)[:max_items]
    return "\n".join(text for _score, text in selected if text)


def state_text(goal: str, state: dict[str, object]) -> str:
    parts = [
        f"Goal: {goal}",
        f"Thought: {state.get('thought', '')}",
        f"Action: {state.get('action', '')}",
        f"Observation: {state.get('accessibility_tree', '')}",
    ]
    return "\n".join(part for part in parts if part.strip())


def smoke_oracle_substring_reader(context: str, expected_answer: str) -> str:
    if normalize(expected_answer) in normalize(context):
        return expected_answer
    return ""


def compute_metrics(predictions: list[dict[str, object]], start: float) -> dict[str, object]:
    total = len(predictions)
    correct = sum(1 for prediction in predictions if prediction.get("correct") is True)
    non_empty_briefs = sum(
        1 for prediction in predictions if int_prediction_value(prediction, "decision_count") > 0
    )
    return {
        "examples": total,
        "accuracy": round(correct / total, 6) if total else 0.0,
        "correct": correct,
        "non_empty_decision_briefs": non_empty_briefs,
        "avg_brief_tokens": round(
            sum(int_prediction_value(prediction, "brief_tokens") for prediction in predictions)
            / total,
            6,
        )
        if total
        else 0.0,
        "latency_seconds": round(perf_counter() - start, 6),
        "reader_policy": "smoke_oracle_substring_reader",
    }


def compute_suite_metrics(mode_results: dict[PocMode, PocResult]) -> dict[str, object]:
    d0_accuracy = float_metric(mode_results["D0"].metrics, "accuracy")
    d1_accuracy = float_metric(mode_results["D1"].metrics, "accuracy")
    d2_accuracy = float_metric(mode_results["D2"].metrics, "accuracy")
    return {
        "D0": mode_results["D0"].metrics,
        "D1": mode_results["D1"].metrics,
        "D2": mode_results["D2"].metrics,
        "delta_D1_minus_D0": round(d1_accuracy - d0_accuracy, 6),
        "delta_D2_minus_D0": round(d2_accuracy - d0_accuracy, 6),
        "reader_policy": "smoke_oracle_substring_reader",
    }


def float_metric(metrics: dict[str, object], key: str) -> float:
    value = metrics.get(key)
    if not isinstance(value, int | float):
        raise TypeError(f"metric field must be numeric: {key}")
    return float(value)


def int_prediction_value(prediction: dict[str, object], key: str) -> int:
    value = prediction.get(key)
    if not isinstance(value, int):
        raise TypeError(f"prediction field must be an int: {key}")
    return value


def write_artifacts(
    config: PocConfig,
    examples: tuple[LongMemEvalV2Example, ...],
    result: PocResult,
) -> None:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(config.output_dir / "config.json", config_to_dict(config))
    write_json(config.output_dir / "manifest.json", build_manifest(config, examples))
    write_json(config.output_dir / "metrics.json", result.metrics)
    write_jsonl(config.output_dir / "predictions.jsonl", result.predictions)
    write_jsonl(config.output_dir / "decision_trace.jsonl", result.decision_trace)
    write_jsonl(config.output_dir / "brief_trace.jsonl", result.brief_trace)
    (config.output_dir / "report.md").write_text(render_report(config, result), encoding="utf-8")


def config_to_dict(config: PocConfig) -> dict[str, object]:
    return {
        "data_root": str(config.data_root),
        "output_dir": str(config.output_dir),
        "mode": config.mode,
        "tier": config.tier,
        "limit": config.limit,
        "oracle_decisions_path": str(config.oracle_decisions_path)
        if config.oracle_decisions_path
        else None,
    }


def build_manifest(
    config: PocConfig,
    examples: tuple[LongMemEvalV2Example, ...],
) -> dict[str, object]:
    return {
        "benchmark": "longmemeval_v2",
        "mode": config.mode,
        "tier": config.tier,
        "data_root": str(config.data_root),
        "questions_sha256": file_sha256(config.data_root / "questions.jsonl"),
        "haystack_sha256": file_sha256(
            config.data_root / "haystacks" / f"lme_v2_{config.tier}.json"
        ),
        "examples": len(examples),
        "question_ids": [example.question.id for example in examples],
    }


def render_report(config: PocConfig, result: PocResult) -> str:
    lines = [
        "# Decision Layer POC Report",
        "",
        f"- mode: `{config.mode}`",
        "- benchmark: `longmemeval_v2`",
        f"- tier: `{config.tier}`",
        f"- examples: `{result.metrics['examples']}`",
        f"- accuracy: `{result.metrics['accuracy']}`",
        f"- non_empty_decision_briefs: `{result.metrics['non_empty_decision_briefs']}`",
        f"- avg_brief_tokens: `{result.metrics['avg_brief_tokens']}`",
        f"- reader_policy: `{result.metrics['reader_policy']}`",
        "",
        "This report is produced by the deterministic smoke runner. It is not a proof run.",
    ]
    return "\n".join(lines) + "\n"


def render_suite_report(config: PocSuiteConfig, metrics: dict[str, object]) -> str:
    d0 = metrics["D0"]
    d1 = metrics["D1"]
    d2 = metrics["D2"]
    if not isinstance(d0, dict) or not isinstance(d1, dict) or not isinstance(d2, dict):
        raise TypeError("suite metrics must include per-mode metric objects")
    lines = [
        "# Decision Layer POC Suite Report",
        "",
        "- benchmark: `longmemeval_v2`",
        f"- tier: `{config.tier}`",
        f"- limit: `{config.limit}`",
        f"- reader_policy: `{metrics['reader_policy']}`",
        "",
        "| Mode | Accuracy | Non-empty Briefs | Avg Brief Tokens |",
        "| --- | ---: | ---: | ---: |",
        format_suite_row("D0", d0),
        format_suite_row("D1", d1),
        format_suite_row("D2", d2),
        "",
        f"- delta_D1_minus_D0: `{metrics['delta_D1_minus_D0']}`",
        f"- delta_D2_minus_D0: `{metrics['delta_D2_minus_D0']}`",
        "",
        "This suite uses the deterministic smoke reader and is not a proof run.",
    ]
    return "\n".join(lines) + "\n"


def format_suite_row(mode: str, metrics: dict[str, object]) -> str:
    return (
        f"| {mode} | {metrics['accuracy']} | {metrics['non_empty_decision_briefs']} | "
        f"{metrics['avg_brief_tokens']} |"
    )


def load_oracle_decisions(path: Path | None) -> dict[str, list[str]]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("oracle decisions file must be a JSON object")
    decisions: dict[str, list[str]] = {}
    for question_id, values in data.items():
        if not isinstance(values, list):
            raise ValueError(f"oracle decisions for {question_id} must be a list")
        decisions[str(question_id)] = [str(value) for value in values]
    return decisions


def write_json(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def normalize(text: str) -> str:
    return " ".join(text.lower().split())
