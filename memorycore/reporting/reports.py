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
        lines.append(f"| {key} | {metrics[key]} |")
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
                "",
            ]
        )
    return "\n".join(lines)

