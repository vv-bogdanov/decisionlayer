from __future__ import annotations

import hashlib
import json
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_run_manifest(
    output_dir: Path,
    *,
    config: dict[str, Any],
    metrics: dict[str, Any],
    predictions_count: int = 0,
    traces_count: int = 0,
    prediction_ids: list[str] | None = None,
) -> None:
    manifest = build_run_manifest(
        config=config,
        metrics=metrics,
        predictions_count=predictions_count,
        traces_count=traces_count,
        prediction_ids=prediction_ids,
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_run_manifest(
    *,
    config: dict[str, Any],
    metrics: dict[str, Any],
    predictions_count: int = 0,
    traces_count: int = 0,
    prediction_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "command": str(config.get("command") or " ".join(sys.argv)),
        "git": git_info(),
        "dataset": dataset_manifest(config),
        "run": {
            "benchmark": config.get("benchmark"),
            "benchmark_split": benchmark_split(config),
            "memory": config.get("memory"),
            "compare_memories": config.get("compare_memories"),
            "recall": config.get("recall"),
            "limit": config.get("limit"),
            "offset": config.get("offset"),
            "output_dir": config.get("output_dir"),
            "predictions_count": predictions_count,
            "traces_count": traces_count,
            "prediction_ids": sorted(set(prediction_ids or [])),
        },
        "model_config": model_config(config),
        "metrics_summary": metrics_summary(metrics),
    }


def git_info() -> dict[str, Any]:
    return {
        "commit": git_command("rev-parse", "--short", "HEAD"),
        "commit_full": git_command("rev-parse", "HEAD"),
        "dirty": bool(git_command("status", "--porcelain")),
    }


def git_command(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            check=False,
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def dataset_manifest(config: dict[str, Any]) -> dict[str, Any]:
    data_path = config.get("data_path")
    if not data_path:
        return {"path": None, "exists": False}
    path = Path(str(data_path))
    payload: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "split": benchmark_split(config),
    }
    if not path.exists():
        return payload
    if path.is_file():
        payload.update(
            {
                "kind": "file",
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
        return payload
    files = sorted(child for child in path.rglob("*") if child.is_file())
    payload.update(
        {
            "kind": "directory",
            "file_count": len(files),
            "size_bytes": sum(child.stat().st_size for child in files),
            "sha256": sha256_directory(path, files),
        }
    )
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_directory(root: Path, files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(str(path.stat().st_size).encode("utf-8"))
        digest.update(sha256_file(path).encode("utf-8"))
    return digest.hexdigest()


def benchmark_split(config: dict[str, Any]) -> str | None:
    explicit = config.get("benchmark_split") or config.get("split")
    if explicit:
        return str(explicit)
    data_path = config.get("data_path")
    if data_path:
        return Path(str(data_path)).stem
    return None


def model_config(config: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "extractor_policy",
        "extractor_model",
        "extractor_url",
        "extractor_max_facts",
        "extractor_max_decisions",
        "judge_policy",
        "judge_model",
        "judge_url",
        "top_k_decisions",
        "top_k_facts",
        "recall_count_weight",
        "keyword_weight",
        "recency_weight",
        "scope_weight",
        "refs_expansion_depth",
        "refs_expansion_limit",
        "max_memory_brief_tokens",
        "forgetting_policy",
        "forgetting_threshold",
        "input_cost_per_1k",
        "output_cost_per_1k",
    )
    return {key: config.get(key) for key in keys if key in config}


def metrics_summary(metrics: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "accuracy",
        "accuracy_ci_low",
        "accuracy_ci_high",
        "judge_score",
        "quality_score",
        "examples",
        "correct",
        "memory_brief_tokens",
        "prompt_tokens",
        "output_tokens",
        "cost_estimate_usd",
        "latency_seconds",
        "source_traceability",
        "false_decision_rate",
        "best_memory",
    )
    return {key: metrics.get(key) for key in keys if key in metrics}


def bootstrap_binary_ci(
    values: list[bool],
    *,
    n_samples: int = 1000,
    confidence: float = 0.95,
    seed: int = 0,
) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    rng = random.Random(seed)
    sample_size = len(values)
    means = []
    for _ in range(n_samples):
        correct = sum(1 for _ in range(sample_size) if values[rng.randrange(sample_size)])
        means.append(correct / sample_size)
    means.sort()
    tail = (1.0 - confidence) / 2.0
    low_index = min(max(int(tail * n_samples), 0), n_samples - 1)
    high_index = min(max(int((1.0 - tail) * n_samples) - 1, 0), n_samples - 1)
    return round(means[low_index], 6), round(means[high_index], 6)


def write_proof_index(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    rows = collect_proof_runs(root)
    index_path = root / "index.md"
    index_path.write_text(render_proof_index(root=root, rows=rows), encoding="utf-8")
    return index_path


def collect_proof_runs(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for metrics_path in sorted(root.rglob("metrics.json")):
        run_dir = metrics_path.parent
        metrics = read_json(metrics_path)
        config = read_json(run_dir / "config.json")
        manifest = read_json(run_dir / "manifest.json")
        rows.append(
            {
                "run_dir": run_dir,
                "config": config,
                "metrics": metrics,
                "manifest": manifest,
            }
        )
    return rows


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def render_proof_index(root: Path, rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Proof Run Index",
        "",
        f"Generated at: `{utc_now()}`",
        "",
        "| Run | Benchmark | Memory | Examples | Accuracy | CI 95% | Quality | Cost | Brief Tokens | Git |",
        "| --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        config = row["config"]
        metrics = row["metrics"]
        manifest = row["manifest"]
        relative = row["run_dir"].relative_to(root).as_posix()
        git = manifest.get("git", {}) if isinstance(manifest, dict) else {}
        ci = ci_text(metrics)
        row_template = (
            "| {run} | {benchmark} | {memory} | {examples} | {accuracy} | {ci} | {quality} | {cost} | {brief} | {git} |"
        )
        lines.append(
            row_template.format(
                run=f"[{relative}]({relative}/report.md)",
                benchmark=config.get("benchmark", ""),
                memory=config.get("compare_memories") or config.get("memory", ""),
                examples=metrics.get("examples", ""),
                accuracy=metrics.get("accuracy", ""),
                ci=ci,
                quality=metrics.get("quality_score", ""),
                cost=metrics.get("cost_estimate_usd", ""),
                brief=metrics.get("memory_brief_tokens", ""),
                git=git.get("commit", ""),
            )
        )
    if not rows:
        lines.append("| _No runs found_ |  |  |  |  |  |  |  |  |  |")
    return "\n".join(lines) + "\n"


def ci_text(metrics: dict[str, Any]) -> str:
    low = metrics.get("accuracy_ci_low")
    high = metrics.get("accuracy_ci_high")
    if low is None or high is None:
        return ""
    return f"{low}..{high}"
