from __future__ import annotations

import csv
import json
import sys
from itertools import product
from pathlib import Path
from typing import Any

from memorycore.experiments.args import parse_overrides
from memorycore.experiments.run_experiment import DEFAULT_CONFIG, run_experiment
from memorycore.reporting.proof import write_run_manifest

DEFAULT_SWEEP_CONFIG: dict[str, Any] = {
    "benchmark": "toy",
    "data_path": None,
    "memory": "decisions_plus_facts",
    "recall": "decision_first",
    "extractor_policy": "rule_based",
    "search": "optuna",
    "metric": "accuracy",
    "n_trials": 12,
    "output_dir": "reports/sweep",
    "top_k_facts_min": 1,
    "top_k_facts_max": 8,
    "top_k_decisions_min": 1,
    "top_k_decisions_max": 5,
    "recall_count_weight_min": 0.0,
    "recall_count_weight_max": 0.2,
    "keyword_weight_min": 0.5,
    "keyword_weight_max": 2.0,
    "recency_weight_min": 0.0,
    "recency_weight_max": 0.5,
    "scope_weight_min": 0.0,
    "scope_weight_max": 1.0,
    "refs_expansion_depth_min": 0,
    "refs_expansion_depth_max": 2,
    "max_memory_brief_tokens_min": 0,
    "max_memory_brief_tokens_max": 2000,
    "forgetting_threshold_min": -1,
    "forgetting_threshold_max": 2,
}


def run_sweep(config: dict[str, Any]) -> dict[str, Any]:
    merged = dict(DEFAULT_SWEEP_CONFIG)
    merged.update({key: value for key, value in config.items() if value != ""})
    output_dir = Path(str(merged["output_dir"]))
    output_dir.mkdir(parents=True, exist_ok=True)

    trials = (
        run_optuna(merged, output_dir)
        if optuna_available() and merged["search"] == "optuna"
        else run_grid(merged, output_dir)
    )
    metric = str(merged["metric"])
    best = max(trials, key=lambda row: float(row.get(metric, 0.0))) if trials else {}
    best_config = dict(merged)
    for key in TUNABLES:
        if key in best:
            best_config[key] = best[key]

    write_sweep_outputs(output_dir, merged, best_config, trials)
    return {"config": merged, "best_config": best_config, "trials": trials}


def optuna_available() -> bool:
    try:
        import optuna  # noqa: F401
    except ImportError:
        return False
    return True


def run_optuna(config: dict[str, Any], output_dir: Path) -> list[dict[str, Any]]:
    import optuna

    trials: list[dict[str, Any]] = []
    metric = str(config["metric"])

    def objective(trial: optuna.Trial) -> float:
        top_k_facts = trial.suggest_int(
            "top_k_facts",
            int(config["top_k_facts_min"]),
            int(config["top_k_facts_max"]),
        )
        top_k_decisions = trial.suggest_int(
            "top_k_decisions",
            int(config["top_k_decisions_min"]),
            int(config["top_k_decisions_max"]),
        )
        params = {
            "top_k_facts": top_k_facts,
            "top_k_decisions": top_k_decisions,
            "recall_count_weight": trial.suggest_float(
                "recall_count_weight",
                float(config["recall_count_weight_min"]),
                float(config["recall_count_weight_max"]),
            ),
            "keyword_weight": trial.suggest_float(
                "keyword_weight",
                float(config["keyword_weight_min"]),
                float(config["keyword_weight_max"]),
            ),
            "recency_weight": trial.suggest_float(
                "recency_weight",
                float(config["recency_weight_min"]),
                float(config["recency_weight_max"]),
            ),
            "scope_weight": trial.suggest_float(
                "scope_weight",
                float(config["scope_weight_min"]),
                float(config["scope_weight_max"]),
            ),
            "refs_expansion_depth": trial.suggest_int(
                "refs_expansion_depth",
                int(config["refs_expansion_depth_min"]),
                int(config["refs_expansion_depth_max"]),
            ),
            "max_memory_brief_tokens": trial.suggest_int(
                "max_memory_brief_tokens",
                int(config["max_memory_brief_tokens_min"]),
                int(config["max_memory_brief_tokens_max"]),
            ),
            "forgetting_threshold": trial.suggest_int(
                "forgetting_threshold",
                int(config["forgetting_threshold_min"]),
                int(config["forgetting_threshold_max"]),
            ),
        }
        result = run_trial(config, output_dir, len(trials), params)
        row = {
            "trial": len(trials),
            **params,
            **result["metrics"],
        }
        row["quality_score"] = quality_score(result["metrics"])
        trials.append(row)
        return float(row.get(metric, result["metrics"].get(metric, 0.0)))

    sampler = optuna.samplers.TPESampler(seed=0)
    study = optuna.create_study(direction="maximize", sampler=sampler)
    study.optimize(objective, n_trials=int(config["n_trials"]), show_progress_bar=False)
    return trials


def run_grid(config: dict[str, Any], output_dir: Path) -> list[dict[str, Any]]:
    trials: list[dict[str, Any]] = []
    fact_values = bounded_values(
        int(config["top_k_facts_min"]),
        int(config["top_k_facts_max"]),
        int(config["n_trials"]),
    )
    decision_values = bounded_values(
        int(config["top_k_decisions_min"]),
        int(config["top_k_decisions_max"]),
        int(config["n_trials"]),
    )
    for top_k_facts, top_k_decisions in list(product(fact_values, decision_values))[: int(config["n_trials"])]:
        params = {
            "top_k_facts": top_k_facts,
            "top_k_decisions": top_k_decisions,
            "recall_count_weight": float(config["recall_count_weight_min"]),
            "keyword_weight": float(config["keyword_weight_min"]),
            "recency_weight": float(config["recency_weight_min"]),
            "scope_weight": float(config["scope_weight_min"]),
            "refs_expansion_depth": int(config["refs_expansion_depth_min"]),
            "max_memory_brief_tokens": int(config["max_memory_brief_tokens_min"]),
            "forgetting_threshold": int(config["forgetting_threshold_min"]),
        }
        result = run_trial(config, output_dir, len(trials), params)
        trials.append(
            {
                "trial": len(trials),
                **params,
                **result["metrics"],
                "quality_score": quality_score(result["metrics"]),
            }
        )
    return trials


def bounded_values(minimum: int, maximum: int, n_trials: int) -> list[int]:
    if maximum <= minimum:
        return [minimum]
    limit = max(1, min(maximum - minimum + 1, n_trials))
    return list(range(minimum, minimum + limit))


def run_trial(
    config: dict[str, Any],
    output_dir: Path,
    trial_number: int,
    params: dict[str, Any],
) -> dict[str, Any]:
    experiment_config = {
        key: value
        for key, value in config.items()
        if key in DEFAULT_CONFIG or key in {"benchmark", "data_path", "memory", "recall"}
    }
    experiment_config.update(
        {
            **params,
            "output_dir": str(output_dir / f"trial_{trial_number:03d}"),
        }
    )
    return run_experiment(experiment_config)


TUNABLES = (
    "top_k_facts",
    "top_k_decisions",
    "recall_count_weight",
    "keyword_weight",
    "recency_weight",
    "scope_weight",
    "refs_expansion_depth",
    "max_memory_brief_tokens",
    "forgetting_threshold",
)


def quality_score(metrics: dict[str, Any]) -> float:
    accuracy = float(metrics.get("accuracy", 0.0))
    traceability = float(metrics.get("source_traceability", 0.0))
    brief_tokens = float(metrics.get("memory_brief_tokens", 0.0))
    token_penalty = min(brief_tokens / 4000.0, 1.0) * 0.1
    return round(accuracy + 0.1 * traceability - token_penalty, 6)


def write_sweep_outputs(
    output_dir: Path,
    config: dict[str, Any],
    best_config: dict[str, Any],
    trials: list[dict[str, Any]],
) -> None:
    (output_dir / "best_config.yaml").write_text(render_yaml(best_config), encoding="utf-8")
    write_trials_csv(output_dir / "trials.csv", trials)
    (output_dir / "sweep_report.md").write_text(
        render_sweep_report(config=config, best_config=best_config, trials=trials),
        encoding="utf-8",
    )
    (output_dir / "sweep_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_run_manifest(
        output_dir,
        config={**config, "run_kind": "sweep"},
        metrics={
            "trials": len(trials),
            "best_metric": config.get("metric"),
            "best_value": best_config.get(str(config.get("metric"))),
        },
        predictions_count=0,
        traces_count=0,
    )


def render_yaml(data: dict[str, Any]) -> str:
    lines = []
    for key in sorted(data):
        value = data[key]
        if value is None:
            rendered = ""
        elif isinstance(value, str):
            rendered = value
        else:
            rendered = json.dumps(value, ensure_ascii=False)
        lines.append(f"{key}: {rendered}")
    return "\n".join(lines) + "\n"


def write_trials_csv(path: Path, trials: list[dict[str, Any]]) -> None:
    if not trials:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = sorted({key for row in trials for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trials)


def render_sweep_report(
    *,
    config: dict[str, Any],
    best_config: dict[str, Any],
    trials: list[dict[str, Any]],
) -> str:
    metric = str(config["metric"])
    lines = [
        "# Sweep Report",
        "",
        "## Summary",
        "",
        f"- search: `{config['search']}`",
        f"- metric: `{metric}`",
        f"- trials: `{len(trials)}`",
        f"- best top_k_facts: `{best_config.get('top_k_facts')}`",
        f"- best top_k_decisions: `{best_config.get('top_k_decisions')}`",
        "",
        "## Trials",
        "",
        "| trial | top_k_facts | top_k_decisions | refs_depth | metric | quality_score |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in trials:
        lines.append(
            (
                "| {trial} | {top_k_facts} | {top_k_decisions} | {refs_expansion_depth} | {metric} | {quality_score} |"
            ).format(
                trial=row["trial"],
                top_k_facts=row["top_k_facts"],
                top_k_decisions=row["top_k_decisions"],
                refs_expansion_depth=row["refs_expansion_depth"],
                metric=row.get(metric, 0.0),
                quality_score=row.get("quality_score", 0.0),
            )
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    overrides = parse_overrides(list(sys.argv[1:] if argv is None else argv))
    result = run_sweep(overrides)
    print({"best_config": result["best_config"], "trials": len(result["trials"])})


if __name__ == "__main__":
    main()
