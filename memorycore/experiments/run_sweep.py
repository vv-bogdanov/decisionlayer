from __future__ import annotations

import csv
import json
import sys
from itertools import product
from pathlib import Path
from typing import Any

from memorycore.experiments.args import parse_overrides
from memorycore.experiments.run_experiment import DEFAULT_CONFIG, run_experiment


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
}


def run_sweep(config: dict[str, Any]) -> dict[str, Any]:
    merged = dict(DEFAULT_SWEEP_CONFIG)
    merged.update({key: value for key, value in config.items() if value != ""})
    output_dir = Path(str(merged["output_dir"]))
    output_dir.mkdir(parents=True, exist_ok=True)

    trials = run_optuna(merged, output_dir) if optuna_available() and merged["search"] == "optuna" else run_grid(merged, output_dir)
    metric = str(merged["metric"])
    best = max(trials, key=lambda row: float(row.get(metric, 0.0))) if trials else {}
    best_config = dict(merged)
    for key in ("top_k_facts", "top_k_decisions"):
        if key in best:
            best_config[key] = int(best[key])

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
        result = run_trial(config, output_dir, len(trials), top_k_facts, top_k_decisions)
        row = {
            "trial": len(trials),
            "top_k_facts": top_k_facts,
            "top_k_decisions": top_k_decisions,
            **result["metrics"],
        }
        trials.append(row)
        return float(result["metrics"].get(metric, 0.0))

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
        result = run_trial(config, output_dir, len(trials), top_k_facts, top_k_decisions)
        trials.append(
            {
                "trial": len(trials),
                "top_k_facts": top_k_facts,
                "top_k_decisions": top_k_decisions,
                **result["metrics"],
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
    top_k_facts: int,
    top_k_decisions: int,
) -> dict[str, Any]:
    experiment_config = {
        key: value
        for key, value in config.items()
        if key in DEFAULT_CONFIG or key in {"benchmark", "data_path", "memory", "recall"}
    }
    experiment_config.update(
        {
            "top_k_facts": top_k_facts,
            "top_k_decisions": top_k_decisions,
            "output_dir": str(output_dir / f"trial_{trial_number:03d}"),
        }
    )
    return run_experiment(experiment_config)


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
        "| trial | top_k_facts | top_k_decisions | metric |",
        "| ---: | ---: | ---: | ---: |",
    ]
    for row in trials:
        lines.append(
            f"| {row['trial']} | {row['top_k_facts']} | {row['top_k_decisions']} | {row.get(metric, 0.0)} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    overrides = parse_overrides(list(sys.argv[1:] if argv is None else argv))
    result = run_sweep(overrides)
    print({"best_config": result["best_config"], "trials": len(result["trials"])})


if __name__ == "__main__":
    main()

