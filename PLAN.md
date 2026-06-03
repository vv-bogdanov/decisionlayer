# Proof Plan: Long-Horizon Memory Evaluation

## Main Goal

Prove or disprove this claim with reproducible experiments:

```text
Decision + Fact memory gives a better quality/cost trade-off on long-horizon
agent tasks than recent context, full context, simple RAG, sparse retrieval,
and facts-only memory.
```

The output of this work is not another implementation checklist. The output is
an evidence package: commands, datasets, reports, ablations, failure analysis,
and a clear answer about whether the memory model is actually better.

## Current Starting Point

- [x] Python research harness exists.
- [x] Core memory model exists: Decisions + Facts + refs + recall_count.
- [x] Deterministic extraction, recall, forgetting, and safety policies exist.
- [x] Toy, LongMemEval, LoCoMo, HaluMem, and MemoryAgentBench adapters exist.
- [x] Baseline runner exists.
- [x] Grid, Optuna, and Hydra entrypoints exist.
- [x] Reports, predictions, traces, metrics, and sweep outputs exist.
- [x] Ruff, mypy, and pytest are configured.

## Master Checklist

Use this section as the top-level progress tracker. Detailed checklists live in
the sections below.

- [x] M1: Proof harness hardening is complete.
- [ ] M2: LongMemEval proof run is complete.
- [ ] M3: MemoryAgentBench proof run is complete.
- [ ] M4: HaluMem safety proof is complete.
- [ ] M5: LoCoMo secondary validation is complete.
- [ ] M6: Strong retrieval challenge is complete or intentionally skipped.
- [ ] M7: Final proof report is complete.
- [ ] B1: LongMemEval has a reproducible dev and held-out result.
- [ ] B2: MemoryAgentBench has reproducible results by competency.
- [ ] B3: HaluMem has hallucination/safety results.
- [ ] B4: LoCoMo has raw and audited secondary validation results.
- [ ] B5: 2026 watchlist benchmarks have been inspected.
- [ ] Baseline matrix has been run on every primary benchmark.
- [ ] Ablation matrix has been run on every primary benchmark.
- [ ] Final decision is recorded: supported, partially supported, or not
  supported.

## Evidence Standard

The proof is credible only if the comparisons are fair and reproducible.

- [x] Pin exact dataset versions and local paths in a run manifest.
- [x] Pin model, extractor, judge, embedding model, and prompt versions.
- [ ] Separate tuning/dev runs from final held-out test runs.
- [ ] Use the same token budget and context budget for competing systems.
- [ ] Run deterministic baselines once and LLM-dependent variants at least 3
  times.
- [x] Report confidence intervals or bootstrap intervals for key metrics.
- [ ] Store all generated `metrics.json`, `predictions.jsonl`, `trace.jsonl`,
  and `report.md` under `reports/`.
- [x] Keep dataset download outside the runner; use explicit `data_path`.
- [ ] Document known benchmark weaknesses and manual audit decisions.

## Primary Metrics

Quality:

- [ ] Accuracy / exact match / substring match where deterministic scoring is
  valid.
- [ ] LLM judge score where deterministic scoring is insufficient.
- [ ] Task success for agent-style tasks.
- [ ] Abstention accuracy.
- [ ] Conflict update accuracy.
- [ ] Temporal reasoning accuracy.

Reliability:

- [ ] Source traceability.
- [ ] Unsupported answer rate.
- [ ] False fact creation rate.
- [ ] False decision creation rate.
- [ ] Hallucination rate on HaluMem.

Efficiency:

- [ ] Prompt tokens.
- [ ] Output tokens.
- [ ] Estimated cost.
- [ ] Latency.
- [ ] Memory brief token budget usage.

Decision criterion:

- [ ] `decisions_facts` or a justified improved variant must beat the strongest
  same-budget baseline on at least 3 long-horizon task families.
- [ ] It must not win only by spending more tokens.
- [ ] It must not increase hallucination or unsupported-answer risk.
- [ ] It must have better traceability than full-context or naive RAG baselines.

## Benchmark Ladder

Use a ladder rather than a single leaderboard number.

### B1: LongMemEval

- [ ] B1 complete.

Purpose:

```text
information extraction
multi-session reasoning
temporal reasoning
knowledge updates
abstention
```

Source:

```text
https://github.com/xiaowu0162/LongMemEval
https://arxiv.org/abs/2410.10813
```

Work:

- [x] Create a frozen LongMemEval manifest with file path, row count, hash, and
  subset IDs.
- [x] Run all current baselines on a dev subset.
- [ ] Run all current baselines on a held-out test subset.
- [ ] Add per-question-type tables.
- [ ] Add failure analysis grouped by extraction, recall, scoring, update, and
  abstention.
- [ ] Compare cost/latency against full-context and RAG baselines.
- [ ] Audit a small sample of labels and judge decisions manually.

Target commands:

```bash
uv run python -m memorycore.experiments.run_experiment \
  benchmark=longmemeval \
  data_path=/path/to/longmemeval_oracle.json \
  compare_memories=recent_context_only,simple_rag,bm25,tfidf,hybrid,fact_only,decisions_facts \
  recall=hybrid \
  limit=100 \
  output_dir=reports/proof/longmemeval_dev

uv run --extra experiments python -m memorycore.experiments.run_sweep \
  benchmark=longmemeval \
  data_path=/path/to/longmemeval_oracle.json \
  memory=decisions_facts \
  recall=hybrid \
  metric=quality_score \
  n_trials=24 \
  output_dir=reports/proof/longmemeval_sweep
```

### B2: MemoryAgentBench

- [ ] B2 complete.

Purpose:

```text
accurate retrieval
test-time learning
long-range understanding
conflict resolution
incremental multi-turn interaction
```

Sources:

```text
https://github.com/HUST-AI-HYZ/MemoryAgentBench
https://huggingface.co/datasets/ai-hyz/MemoryAgentBench
https://arxiv.org/abs/2507.05257
```

Work:

- [ ] Create a manifest for all four official splits:
  `Accurate_Retrieval`, `Test_Time_Learning`, `Long_Range_Understanding`,
  `Conflict_Resolution`.
- [ ] Run a small smoke for each split.
- [ ] Run a dev subset for each split.
- [ ] Run a held-out test subset for each split.
- [ ] Fix scoring per split instead of relying only on substring matching.
- [ ] Report metrics by MemoryAgentBench competency.
- [ ] Add budget-aware comparison because some rows have huge contexts.

Target command:

```bash
uv run --extra experiments python -m memorycore.experiments.run_experiment \
  benchmark=memoryagentbench \
  data_path=/path/to/Accurate_Retrieval-00000-of-00001.parquet \
  compare_memories=recent_context_only,simple_rag,bm25,tfidf,hybrid,fact_only,decisions_facts \
  max_memory_brief_tokens=2000 \
  limit=100 \
  output_dir=reports/proof/memoryagentbench_ar_dev
```

### B3: HaluMem

- [ ] B3 complete.

Purpose:

```text
memory hallucination
false fact creation
false decision creation
wrong memory updates
unsupported memory answers
```

Source:

```text
https://github.com/MemTensor/HaluMem
https://arxiv.org/abs/2511.03506
```

Work:

- [ ] Create a manifest for selected HaluMem stage files.
- [ ] Define deterministic hallucination and unsupported-answer metrics where
  possible.
- [ ] Add LLM judge only behind config for ambiguous cases.
- [ ] Compare `decisions_facts` against RAG and facts-only baselines.
- [ ] Verify that decisions are not created without explicit commit signals.
- [ ] Report false decision and false fact rates.

Target command:

```bash
uv run python -m memorycore.experiments.run_experiment \
  benchmark=halumem \
  data_path=/path/to/stage5_1_dialogue_generation.jsonl \
  compare_memories=simple_rag,bm25,tfidf,hybrid,fact_only,decisions_facts \
  limit=100 \
  output_dir=reports/proof/halumem_dev
```

### B4: LoCoMo

- [ ] B4 complete.

Purpose:

```text
long multi-session conversational memory
temporal facts
cross-session personal/event reasoning
```

Source:

```text
https://github.com/snap-research/locomo
```

Caution:

LoCoMo is useful, but we should not rely on it blindly. Treat it as a secondary
benchmark and manually audit a small sample of labels and judge outcomes before
making strong claims.

Work:

- [ ] Create a manifest for `locomo10.json`.
- [ ] Run all baselines on all QA examples.
- [ ] Add category-level metrics.
- [ ] Manually audit at least 30 random QA items.
- [ ] Mark unreliable examples and report results with and without them.

Target command:

```bash
uv run python -m memorycore.experiments.run_experiment \
  benchmark=locomo \
  data_path=/path/to/locomo10.json \
  compare_memories=recent_context_only,simple_rag,bm25,tfidf,hybrid,fact_only,decisions_facts \
  output_dir=reports/proof/locomo_full
```

### B5: 2026 Watchlist

- [ ] B5 complete.

Do not block the first proof package on these, but track them because they are
closer to long-horizon agent use cases.

Sources:

```text
https://github.com/xiaowu0162/LongMemEval-V2
https://arxiv.org/abs/2605.12493
https://arxiv.org/abs/2605.18565
```

Work:

- [ ] Inspect LongMemEval-V2 schema and licensing.
- [ ] Inspect LongMINT availability and schema.
- [ ] Decide whether either benchmark should become part of the proof suite.
- [ ] Add adapters only if the dataset is accessible and the task adds new
  signal beyond LongMemEval and MemoryAgentBench.

## Baseline Matrix

Every serious benchmark run should include:

- [ ] `no_memory`
- [ ] `recent_context_only`
- [ ] `full_context_where_possible`
- [ ] `simple_rag`
- [ ] `bm25`
- [ ] `tfidf`
- [ ] `hybrid`
- [ ] `fact_only`
- [ ] `decisions_only`
- [ ] `decisions_facts`
- [ ] `decisions_plus_facts_plus_refs`
- [ ] `decisions_plus_facts_plus_refs_plus_recall_count`

Add later only if needed:

- [ ] Local embedding vector recall.
- [ ] Cross-encoder or LLM reranker.
- [ ] Strong open-source memory baseline if it can be run reproducibly.

## Ablation Plan

The proof must show which component helps.

- [ ] Facts only vs Decisions only.
- [ ] Decisions + Facts vs Facts only.
- [ ] With refs expansion vs without refs expansion.
- [ ] With recall_count weighting vs without recall_count weighting.
- [ ] With forgetting vs without forgetting.
- [ ] With age-aware forgetting vs basic low-recall forgetting.
- [ ] Rule-based extraction vs LLM extraction.
- [ ] Sparse recall vs vector recall.
- [ ] Hybrid recall vs reranked hybrid recall.
- [ ] Same quality at lower token budget.
- [ ] Same token budget at higher quality.

## Implementation Milestones

### M1: Proof Harness Hardening

- [x] M1 complete.

- [x] Add run manifest output with dataset path, hash, size, split, model config,
  git commit, and command.
- [x] Add bootstrap confidence interval helper.
- [x] Add benchmark-run table aggregation across report directories.
- [x] Add `reports/proof/index.md` generator.
- [x] Add command recipes to `README.md`.
- [x] Keep `uv run pytest`, Ruff, and mypy green.

### M2: LongMemEval Proof Run

- [ ] M2 complete.

- [x] Freeze LongMemEval manifest.
- [x] Run dev baseline table.
- [ ] Tune only on dev subset.
- [ ] Run held-out test baseline table.
- [ ] Generate ablation table.
- [ ] Generate cost/latency Pareto table.
- [ ] Write failure analysis.

### M3: MemoryAgentBench Proof Run

- [ ] M3 complete.

- [ ] Freeze split manifests.
- [ ] Add split-specific scoring where needed.
- [ ] Run smoke for every split.
- [ ] Run dev baseline table for every split.
- [ ] Run held-out test table for every split.
- [ ] Summarize by competency.

### M4: HaluMem Safety Proof

- [ ] M4 complete.

- [ ] Freeze HaluMem manifest.
- [ ] Add unsupported-answer and hallucination metrics.
- [ ] Run baseline table.
- [ ] Verify false decision rate.
- [ ] Compare with and without decision safety.
- [ ] Add qualitative failure examples.

### M5: LoCoMo Secondary Validation

- [ ] M5 complete.

- [ ] Freeze LoCoMo manifest.
- [ ] Run all baselines.
- [ ] Audit labels.
- [ ] Report raw and audited metrics.
- [ ] Decide whether LoCoMo supports or weakens the main claim.

### M6: Strong Retrieval Challenge

- [ ] M6 complete or intentionally skipped.

- [ ] Add local embedding vector recall if sparse retrieval is not competitive.
- [ ] Add reranker only if recall traces show ranking failures.
- [ ] Compare against `decisions_facts` at the same token budget.
- [ ] Remove any component that does not improve quality, traceability, cost, or
  maintainability.

### M7: Final Proof Report

- [ ] M7 complete.

- [ ] Write `reports/proof/final_report.md`.
- [ ] Include benchmark versions and commands.
- [ ] Include all primary metrics.
- [ ] Include ablations.
- [ ] Include confidence intervals.
- [ ] Include cost/latency tables.
- [ ] Include failure analysis.
- [ ] State whether the hypothesis is supported, partially supported, or not
  supported.

## Definition Of Proof

The main claim is supported only if all are true:

- [ ] Our best Decision + Fact variant beats the strongest same-budget baseline
  on LongMemEval.
- [ ] It beats the strongest same-budget baseline on at least two additional
  long-horizon task families.
- [ ] It has equal or lower hallucination / unsupported-answer rate.
- [ ] It has better source traceability.
- [ ] It uses fewer tokens or lower cost than full-context baselines.
- [ ] The result survives ablations and is not explained by one lucky component
  or one weak baseline.
- [ ] The result is reproducible from a clean checkout with documented commands.

If these conditions fail, the correct result is not to force the claim. The
correct result is to document where the model loses and decide whether the next
business-relevant improvement is extraction, recall, update safety, scoring, or
cost reduction.

## Practical Next Step

Start with `M1` and `M2`.

The next commit should be:

```text
Add proof run manifests and LongMemEval aggregation
```

Minimum next deliverables:

- [x] `manifest.json` for every experiment run.
- [x] `reports/proof/index.md` aggregation.
- [x] LongMemEval dev baseline table with all current baselines.
- [ ] LongMemEval failure analysis table.
- [x] Updated README commands.
