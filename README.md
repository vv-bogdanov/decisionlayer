# memorycore

Research prototype for Decision-First Agent Memory:

```text
Agent Memory = Decisions + Facts
```

The project is intentionally scoped as an experiment harness, not a production
SDK. See `PLAN.md` and `decision-first-memory-research-prototype-tz.md` for the
full implementation direction.

## Quick Start

Use `uv` for the fastest reproducible local environment:

```bash
uv run pytest
```

Run a toy experiment:

```bash
uv run python -m memorycore.experiments.run_experiment benchmark=toy memory=decisions_plus_facts output_dir=reports/latest
```

Run the LongMemEval-compatible smoke fixture:

```bash
uv run python -m memorycore.experiments.run_experiment benchmark=longmemeval memory=decisions_plus_facts recall=decision_first output_dir=reports/longmemeval_smoke
```

Run a sweep:

```bash
uv run --extra experiments python -m memorycore.experiments.run_sweep benchmark=longmemeval memory=decisions_plus_facts search=optuna n_trials=4 output_dir=reports/sweep
```

Generated reports are written under `reports/` and ignored by git.

## Current Scope

Implemented:

```text
core memory models
in-memory store
add_raw_input / add_fact / set_decision / recall / forget_facts / export_trace
deterministic extraction, recall, forgetting, and safety policies
toy benchmark
LongMemEval-compatible adapter with local data_path support
LoCoMo / HaluMem / MemoryAgentBench JSON adapters
baseline runner
experiment reports
grid and Optuna sweep runner
pytest coverage for core, recall, benchmark, and sweep behavior
```

External benchmark datasets are not downloaded automatically. Pass `data_path`
to the runner when using real dataset files.
