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
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
```

Run a toy experiment:

```bash
uv run python -m memorycore.experiments.run_experiment benchmark=toy memory=decisions_facts output_dir=reports/latest
```

Run the LongMemEval-compatible smoke fixture:

```bash
uv run python -m memorycore.experiments.run_experiment benchmark=longmemeval memory=decisions_facts recall=decision_first output_dir=reports/longmemeval_smoke
```

Run a real LongMemEval oracle subset after downloading
`longmemeval_oracle.json` from `xiaowu0162/longmemeval-cleaned`:

```bash
uv run python -m memorycore.experiments.run_experiment benchmark=longmemeval data_path=/path/to/longmemeval_oracle.json memory=decisions_facts recall=decision_first limit=25 output_dir=reports/longmemeval_oracle_subset
```

Run the first baseline comparison report:

```bash
uv run python -m memorycore.experiments.run_experiment benchmark=longmemeval compare_memories=recent_context_only,simple_rag,fact_only,decisions_facts output_dir=reports/comparison
```

Run the first real LongMemEval oracle baseline comparison:

```bash
uv run python -m memorycore.experiments.run_experiment benchmark=longmemeval data_path=/path/to/longmemeval_oracle.json compare_memories=recent_context_only,simple_rag,fact_only,decisions_facts limit=25 output_dir=reports/longmemeval_oracle_baselines
```

Compare retrieval policies on the same subset:

```bash
uv run python -m memorycore.experiments.run_experiment benchmark=longmemeval data_path=/path/to/longmemeval_oracle.json compare_memories=simple_rag,bm25,tfidf,hybrid,decisions_facts limit=25 output_dir=reports/longmemeval_retrieval_compare
```

Run a sweep:

```bash
uv run --extra experiments python -m memorycore.experiments.run_sweep benchmark=longmemeval memory=decisions_facts search=optuna n_trials=4 output_dir=reports/sweep
```

Generated reports are written under `reports/` and ignored by git.

Cost estimates are disabled by default. Pass token prices explicitly when needed:

```bash
uv run python -m memorycore.experiments.run_experiment benchmark=toy memory=decisions_facts input_cost_per_1k=0.15 output_cost_per_1k=0.60
```

LLM judging is also disabled by default. Enable it only when `OPENAI_API_KEY` is
available:

```bash
uv run python -m memorycore.experiments.run_experiment benchmark=toy memory=decisions_facts judge_policy=llm judge_model=gpt-4o-mini
```

## Current Scope

Implemented:

```text
core memory models
in-memory store
add_raw_input / add_fact / set_decision / recall / forget_facts / export_trace
deterministic extraction, recall, forgetting, and safety policies
toy benchmark
LongMemEval-compatible adapter with local data_path support
LongMemEval oracle schema parsing, source-message traces, limit/offset
LoCoMo / HaluMem / MemoryAgentBench JSON adapters
baseline runner
experiment reports
grid and Optuna sweep runner
pytest coverage for core, recall, benchmark, and sweep behavior
```

External benchmark datasets are not downloaded automatically. Pass `data_path`
to the runner when using real dataset files.
