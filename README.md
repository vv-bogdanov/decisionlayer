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
uv run --extra dev mypy memorycore
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

Run a Hydra multirun:

```bash
uv run --extra experiments python -m memorycore.experiments.run_hydra -m benchmark=toy memory=decisions_facts,hybrid output_dir=reports/hydra_multirun
```

Run a proof baseline table and aggregate proof reports:

```bash
uv run python -m memorycore.experiments.run_experiment \
  benchmark=longmemeval \
  data_path=/path/to/longmemeval_oracle.json \
  compare_memories=no_memory,recent_context_only,full_context_where_possible,simple_rag,bm25,tfidf,hybrid,fact_only,decisions_only,decisions_facts,decisions_plus_facts_plus_refs,decisions_plus_facts_plus_refs_plus_recall_count \
  recall=hybrid \
  limit=100 \
  output_dir=reports/proof/longmemeval_dev

uv run python -m memorycore.experiments.aggregate_proof reports/proof
```

Run real LoCoMo after downloading the official repo data:

```bash
uv run python -m memorycore.experiments.run_experiment benchmark=locomo data_path=/path/to/locomo10.json memory=decisions_facts recall=hybrid limit=25 output_dir=reports/locomo_real_smoke
```

Run real HaluMem on a generated stage file:

```bash
uv run python -m memorycore.experiments.run_experiment benchmark=halumem data_path=/path/to/stage5_1_dialogue_generation.jsonl memory=decisions_facts recall=hybrid limit=25 output_dir=reports/halumem_real_smoke
```

Run real MemoryAgentBench parquet. Use the `experiments` extra because parquet
requires `pyarrow`:

```bash
uv run --extra experiments python -m memorycore.experiments.run_experiment benchmark=memoryagentbench data_path=/path/to/Accurate_Retrieval-00000-of-00001.parquet memory=decisions_facts recall=hybrid limit=25 output_dir=reports/memoryagentbench_real_smoke
```

Generated reports are written under `reports/` and ignored by git.
Each experiment run also writes a `manifest.json` with dataset fingerprint, git
commit, model/scoring config, command, and selected example IDs.

Cost estimates are disabled by default. Pass token prices explicitly when needed:

```bash
uv run python -m memorycore.experiments.run_experiment benchmark=toy memory=decisions_facts input_cost_per_1k=0.15 output_cost_per_1k=0.60
```

LLM judging is also disabled by default. Enable it only when `OPENAI_API_KEY` is
available:

```bash
uv run python -m memorycore.experiments.run_experiment benchmark=toy memory=decisions_facts judge_policy=llm judge_model=gpt-4o-mini
```

LLM extraction is also opt-in and uses the same API key. Safety checks still
block committed decisions unless the input has an explicit `COMMIT DECISION:`
signal:

```bash
uv run python -m memorycore.experiments.run_experiment benchmark=toy memory=decisions_facts extractor_policy=llm extractor_model=gpt-4o-mini
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
LoCoMo / HaluMem / MemoryAgentBench real-schema adapters
BM25, TF-IDF sparse vector, and hybrid recall
baseline runner
experiment reports
run manifests and proof report aggregation
grid, Optuna, and Hydra multirun support
optional LLM judge and LLM extractor behind explicit config
cost estimate, bootstrap accuracy interval, and composite quality scoring
pytest, Ruff, and mypy coverage for core, recall, benchmark, and sweep behavior
```

External benchmark datasets are not downloaded automatically. Pass `data_path`
to the runner when using real dataset files.
