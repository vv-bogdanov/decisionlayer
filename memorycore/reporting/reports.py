from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_experiment_outputs(
    *,
    output_dir: Path,
    config: dict[str, Any],
    metrics: dict[str, Any],
    predictions: list[dict[str, Any]],
    traces: list[dict[str, Any]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "config.json", config)
    write_json(output_dir / "metrics.json", metrics)
    write_jsonl(output_dir / "predictions.jsonl", predictions)
    write_jsonl(output_dir / "trace.jsonl", traces)
    (output_dir / "report.md").write_text(
        render_markdown_report(config=config, metrics=metrics, predictions=predictions),
        encoding="utf-8",
    )


def render_markdown_report(
    *,
    config: dict[str, Any],
    metrics: dict[str, Any],
    predictions: list[dict[str, Any]],
) -> str:
    lines = [
        "# Experiment Report",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key in sorted(metrics):
        if key in {"baseline_metrics", "question_type_metrics"}:
            continue
        lines.append(f"| {key} | {metrics[key]} |")
    question_type_metrics = metrics.get("question_type_metrics")
    if isinstance(question_type_metrics, dict) and question_type_metrics:
        lines.extend(
            [
                "",
                "## Question Type Metrics",
                "",
                "| Question Type | Accuracy | Exact Match | Substring Match | Examples |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for question_type, row in sorted(question_type_metrics.items()):
            lines.append(
                "| {question_type} | {accuracy} | {exact_match} | {substring_match} | {examples} |".format(
                    question_type=question_type,
                    accuracy=row.get("accuracy"),
                    exact_match=row.get("exact_match"),
                    substring_match=row.get("substring_match"),
                    examples=row.get("examples"),
                )
            )
    baseline_metrics = metrics.get("baseline_metrics")
    if isinstance(baseline_metrics, list) and baseline_metrics:
        lines.extend(
            [
                "",
                "## Policy Comparison",
                "",
                "| Memory | Accuracy | Examples | Brief Tokens |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for row in baseline_metrics:
            lines.append(
                "| {memory} | {accuracy} | {examples} | {memory_brief_tokens} |".format(
                    memory=row.get("memory"),
                    accuracy=row.get("accuracy"),
                    examples=row.get("examples"),
                    memory_brief_tokens=row.get("memory_brief_tokens"),
                )
            )
    lines.extend(
        [
            "",
            "## Config",
            "",
            f"- benchmark: `{config.get('benchmark')}`",
            f"- memory: `{config.get('memory')}`",
            f"- recall: `{config.get('recall')}`",
            "",
            "## Sample Predictions",
            "",
        ]
    )
    for prediction in predictions[:5]:
        lines.extend(
            [
                f"### {prediction['id']}",
                "",
                f"- question: {prediction['question']}",
                f"- expected: {prediction['expected_answer']}",
                f"- predicted: {prediction['prediction']}",
                f"- correct: {prediction['correct']}",
                f"- question_type: {prediction.get('question_type')}",
                "",
                "Memory brief:",
                "",
                "```text",
                str(prediction.get("memory_brief", ""))[:1000],
                "```",
                "",
            ]
        )
    failures = [prediction for prediction in predictions if not prediction.get("correct")]
    lines.extend(["## Failure Cases", ""])
    if not failures:
        lines.append("No failures in this run.")
    for prediction in failures[:10]:
        lines.extend(
            [
                f"### {prediction['id']}",
                "",
                f"- memory: {prediction.get('memory')}",
                f"- question: {prediction['question']}",
                f"- expected: {prediction['expected_answer']}",
                f"- predicted: {prediction['prediction']}",
                f"- probable cause: {prediction.get('probable_failure_cause')}",
                "",
            ]
        )
    return "\n".join(lines)
