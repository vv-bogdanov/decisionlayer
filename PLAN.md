# Implementation Plan

## Status Snapshot

- [x] MVP Python package and `uv` project setup.
- [x] Core Decision + Fact memory runtime.
- [x] Deterministic extraction, recall, forgetting, and safety policies.
- [x] Toy benchmark fixture and runner.
- [x] LongMemEval-compatible smoke adapter with explicit `data_path` support.
- [x] Baseline comparison report for smoke fixtures.
- [x] Optuna/grid sweep runner.
- [x] Report outputs: `metrics.json`, `predictions.jsonl`, `trace.jsonl`,
  `report.md`, `best_config.yaml`, `trials.csv`, `sweep_report.md`.
- [x] Pytest coverage for core, recall, benchmark, and sweep behavior.
- [ ] Real LongMemEval dataset schema validation and subset run.
- [ ] Benchmark-specific LongMemEval scoring.
- [ ] Better retrieval beyond keyword overlap.
- [ ] Dataset-aware extraction without artificial `FACT:` prefixes.
- [ ] Ruff lint/format tooling.

## Context

The repository now contains the first Python research prototype milestone:
package skeleton, core runtime, deterministic policies, benchmark harness,
baseline comparison, reports, sweeps, and tests.

The target from the current technical brief is a Python research prototype for:

```text
Agent Memory = Decisions + Facts
```

The goal is not a production SDK, REST API, UI, database product, or framework
adapter. The goal is a reproducible experiment pipeline that can compare memory
variants on existing memory benchmarks.

## Practical Direction

Start with the cheapest verifiable implementation:

- [x] Minimal Python core.
- [x] Deterministic in-memory storage.
- [x] Small local tests and fixtures.
- [x] One benchmark adapter.
- [x] Shared runner and metrics output.
- [x] Sweeps.
- [ ] Real benchmark validation.
- [ ] Heavier retrieval.

Do not start with SQLite, vector DBs, LLM extraction, graph storage, REST, or SDK
interfaces. They may be useful later, but they add cost before the hypothesis is
measurable.

## Proposed Project Structure

```text
memorycore/
  __init__.py
  core/
    models.py
    store.py
    runtime.py
    trace.py
  policies/
    extraction.py
    recall.py
    forgetting.py
    safety.py
  benchmarks/
    base.py
    longmemeval.py
    locomo.py
    halumem.py
    memoryagentbench.py
  baselines/
    runners.py
  experiments/
    run_experiment.py
    run_sweep.py
  reporting/
    reports.py

configs/
  experiment.yaml
  benchmark/
  memory/
  recall/
  sweep/

tests/
  test_core_memory.py
  test_recall.py
  test_benchmarks.py

reports/
  .gitkeep
```

This structure is intentionally boring: enough separation for experiments, but
no product-style abstraction layer.

## Phase P0: Core And First Runner

Deliver the minimum runnable prototype.

Status:

- [x] Completed.

### Core Models

Implement:

```text
Ref
RawInput
Fact
Decision
MemoryBrief
RecallTrace
```

Required fields:

```text
Decision:
  kind
  key
  value
  scope
  refs
  meta

Fact:
  kind
  text
  scope
  recall_count
  tags
  refs
  meta

Ref:
  target
  rel
  weight
```

Use dataclasses or Pydantic. Prefer dataclasses first unless validation becomes
painful.

### Core API

Implement:

```text
add_raw_input(...)
add_fact(...)
set_decision(...)
recall(...)
forget_facts(...)
export_trace(...)
```

Rules:

- [x] `set_decision` replaces current decision by `key + scope`.
- [x] Old decision value is saved as a fact with tags `history` and
   `decision_change`.
- [x] Facts selected into `MemoryBrief` receive `recall_count += 1`.
- [x] Important facts and decisions should carry source refs when available.
- [x] Decision creation/update requires explicit commit signal in extraction
  policy.

### Initial Policies

Implement only deterministic policies first:

```text
extraction:
  manual_oracle
  rule_based

recall:
  recent_only
  keyword
  decision_first
  decision_first_with_recall_count

forgetting:
  none
  low_recall_count_except_decision_refs

safety:
  require_commit_for_decision
  require_key_value_scope
  preserve_decision_history
```

### Tests

Add focused tests for:

- [x] Adding raw inputs and facts.
- [x] Creating a decision.
- [x] Updating a decision and preserving history as fact.
- [x] Recall returns decisions first.
- [x] Recall increments `recall_count` for selected facts.
- [x] Trace explains selected decisions/facts.
- [x] Forgetting does not remove facts referenced by current decisions.

### CLI

Create a minimal command:

```text
python -m memorycore.experiments.run_experiment benchmark=toy memory=decisions_facts
```

The first benchmark can be a tiny local fixture. This prevents external dataset
download and API keys from blocking core validation.

## Phase P1: LongMemEval And Baselines

Add the first real external benchmark adapter.

Status:

- [x] LongMemEval-compatible JSON adapter with local `data_path`.
- [x] Tiny LongMemEval-compatible smoke fixture.
- [x] Baseline runner and comparison report.
- [ ] Real LongMemEval schema validation.
- [ ] Real LongMemEval subset report.

### LongMemEval Adapter

Use LongMemEval as the first benchmark because it directly tests:

```text
information extraction
multi-session reasoning
temporal reasoning
knowledge updates
abstention
```

Adapter responsibilities:

- [x] Load local LongMemEval JSON files.
- [x] Convert sessions/messages into raw inputs.
- [x] Feed history into memory runtime.
- [x] Run recall for each question.
- [x] Produce prediction records.
- [x] Save trace records.
- [ ] Validate against the real LongMemEval schema and fields.

Do not hardcode dataset download into the runner. Prefer a config path, because
datasets and licenses can change.

### Baselines

Implement through the same runner:

```text
no_memory
recent_context_only
full_context_where_possible
simple_rag
fact_only
decisions_only
decisions_plus_facts
decisions_plus_facts_plus_refs
decisions_plus_facts_plus_refs_plus_recall_count
```

For P1, required minimum:

- [x] `recent_context_only`
- [x] `simple_rag`
- [x] `fact_only`
- [x] `decisions_facts`

### Scoring

Start with metrics that do not require expensive judging:

```text
accuracy
exact_match
substring_match
memory_brief_tokens
facts_selected_per_recall
decisions_selected_per_recall
source_traceability
false_decision_rate
latency
```

- [x] `accuracy`
- [x] `exact_match`
- [x] `substring_match`
- [x] `memory_brief_tokens`
- [x] `facts_selected_per_recall`
- [x] `decisions_selected_per_recall`
- [x] `source_traceability`
- [x] `false_decision_rate`
- [x] `latency`
- [ ] LongMemEval-specific deterministic scoring.
- [ ] LLM-as-judge behind config.

### Reports

Each run should write:

```text
metrics.json
predictions.jsonl
trace.jsonl
report.md
```

The markdown report should include:

- [x] Summary table.
- [x] Per-policy comparison.
- [x] Sample memory briefs.
- [x] Failure cases.
- [x] Basic token summary via `memory_brief_tokens`.
- [ ] Cost estimate.

## Phase P2: Sweeps And More Benchmarks

Status:

- [x] `run_sweep`.
- [x] Optuna objective.
- [x] Grid fallback.
- [x] `best_config.yaml`.
- [x] `trials.csv`.
- [x] `sweep_report.md`.
- [x] Generic JSON adapters for LoCoMo, HaluMem, and MemoryAgentBench.
- [ ] Hydra multirun integration.
- [ ] Real LoCoMo run.
- [ ] Real HaluMem run.
- [ ] Real MemoryAgentBench run.

### Hydra And Optuna

Add:

- [x] `run_sweep`
- [x] `best_config.yaml`
- [x] `trials.csv`
- [x] `sweep_report.md`

Initial tunable parameters:

- [x] `top_k_facts`
- [x] `top_k_decisions`
- [ ] `recall_count_weight`
- [ ] `keyword_weight`
- [ ] `recency_weight`
- [ ] `scope_weight`
- [ ] `refs_expansion_depth`
- [ ] `max_memory_brief_tokens`
- [ ] `forgetting_threshold`

Start with one objective metric. Multi-objective optimization can wait until the
single-metric pipeline is stable.

### LoCoMo Adapter

Add LoCoMo after LongMemEval. It is useful for long-term conversational memory,
QA over long conversations, temporal facts, and multi-session memory.

- [x] Generic JSON adapter.
- [ ] Real dataset schema validation.
- [ ] Real benchmark run.

### HaluMem Adapter

Add HaluMem to test memory hallucination risks:

```text
false fact creation
false decision creation
wrong decision update
unsupported memory answer
```

This is important because the architecture claims decision safety and source
traceability as strengths.

- [x] Generic JSON adapter.
- [ ] Real dataset schema validation.
- [ ] Real benchmark run.

### MemoryAgentBench Adapter

Add after the simpler adapters are stable. It is broader and heavier, so it
should not block the initial prototype.

- [x] Generic JSON adapter.
- [ ] Real dataset schema validation.
- [ ] Real benchmark run.

## Phase P3: Better Retrieval And Safety

Add only after benchmark reports show where the current prototype fails.

Status:

- [ ] Not started. Wait for real LongMemEval baseline results first.

Possible additions:

- [ ] LLM extraction.
- [ ] LLM extraction safety checks.
- [ ] Semantic/vector recall.
- [ ] Hybrid keyword/vector recall.
- [ ] Refs expansion.
- [ ] Reranking.
- [ ] Age-aware forgetting.
- [x] Failure analysis reports, initial version.
- [ ] Multi-objective scoring.

Keep each addition benchmark-driven. If a new component does not improve quality,
debuggability, cost, or maintainability, remove it.

## Definition Of Done

Single experiment:

- [x] Smoke fixture command works.
- [ ] Real LongMemEval dataset command works.

```text
python -m memorycore.experiments.run_experiment benchmark=longmemeval memory=decisions_facts recall=decision_first
```

Expected outputs:

```text
metrics.json
predictions.jsonl
trace.jsonl
report.md
```

Sweep:

- [x] Smoke fixture command works.
- [ ] Real LongMemEval dataset command works.

```text
python -m memorycore.experiments.run_sweep benchmark=longmemeval memory=decisions_facts search=optuna
```

Expected outputs:

```text
best_config.yaml
trials.csv
sweep_report.md
```

## Key Trade-Offs

1. In-memory storage first means the prototype is easier to test and debug, but
   not production-ready.
2. Keyword/recent recall first gives a measurable baseline quickly, but will not
   be the best retrieval quality.
3. Rule-based/manual extraction reduces cost and randomness, but cannot prove
   end-to-end LLM extraction quality.
4. One benchmark first reduces integration risk, but conclusions must wait until
   at least LongMemEval, LoCoMo, and HaluMem are compared.
5. Reports and traces are mandatory from the beginning because benchmark scores
   without debuggability will not explain whether Decisions, Facts, refs, or
   recallCount are helping.

## First Implementation Checklist

- [x] Add `pyproject.toml` with package metadata and test dependencies.
- [x] Create package skeleton under `memorycore/`.
- [x] Implement core models and in-memory store.
- [x] Implement runtime operations.
- [x] Implement deterministic recall policies.
- [x] Add focused pytest coverage for core behavior.
- [x] Add toy benchmark fixture and runner.
- [x] Add report/traces output.
- [x] Add LongMemEval adapter using local dataset path from config.
- [x] Add first baseline comparison report.

## Next Plan: Real Benchmark Signal

The first prototype milestone is implemented. The next stage should focus on
getting the first honest benchmark result, not on adding more architecture.

### Goal

Answer this question on real data:

```text
Does Decision-First Memory produce a measurable signal over simple baselines?
```

Use a small but real LongMemEval subset first. Expand only after the runner,
scoring, traces, and failure analysis are trustworthy.

### N1: Real LongMemEval Subset

Implement a real LongMemEval subset runner.

Work:

- [ ] Add clear local dataset instructions.
- [ ] Inspect the real LongMemEval file schema.
- [ ] Adapt `memorycore/benchmarks/longmemeval.py` to that schema.
- [ ] Support subset limits for quick runs.
- [ ] Preserve raw sessions/messages in traces.
- [ ] Add tests with a small fixture matching the real schema.

Do not download datasets automatically inside the runner. Keep `data_path`
explicit so benchmark data, licenses, and local storage remain under user
control.

Target command:

```bash
uv run python -m memorycore.experiments.run_experiment \
  benchmark=longmemeval \
  data_path=/path/to/longmemeval \
  memory=decisions_facts \
  recall=decision_first \
  output_dir=reports/longmemeval_real_subset
```

Expected outputs:

```text
metrics.json
predictions.jsonl
trace.jsonl
report.md
```

### N2: Benchmark-Specific Scoring

Strengthen scoring before adding heavier retrieval.

Work:

- [x] Keep existing exact/substring metrics.
- [ ] Add LongMemEval-specific scoring where answer types require it.
- [ ] Separate metrics by case type when available:
  - [ ] extraction
  - [ ] multi-session reasoning
  - [ ] temporal reasoning
  - [ ] knowledge updates
  - [ ] abstention
- [ ] Add unsupported/abstention handling where labels support it.
- [ ] Keep LLM-as-judge out of the default path until deterministic scoring is
   understood.

Practical reason: poor scoring can make retrieval changes look better or worse
than they are.

### N3: Real Baseline Table

Run the first real comparison table on the same LongMemEval subset.

Required baselines:

- [x] `recent_context_only`, smoke fixture.
- [x] `simple_rag`, smoke fixture.
- [x] `fact_only`, smoke fixture.
- [x] `decisions_facts`, smoke fixture.
- [ ] `recent_context_only`, real LongMemEval subset.
- [ ] `simple_rag`, real LongMemEval subset.
- [ ] `fact_only`, real LongMemEval subset.
- [ ] `decisions_facts`, real LongMemEval subset.

Target command:

```bash
uv run python -m memorycore.experiments.run_experiment \
  benchmark=longmemeval \
  data_path=/path/to/longmemeval \
  compare_memories=recent_context_only,simple_rag,fact_only,decisions_facts \
  output_dir=reports/longmemeval_baselines
```

Report must show:

- [x] Summary table, smoke fixture.
- [x] Per-baseline metrics, smoke fixture.
- [x] Sample memory briefs, smoke fixture.
- [x] Failure cases, smoke fixture.
- [x] Trace examples, smoke fixture.
- [ ] Same report on real LongMemEval subset.

The point is to see whether failures come from extraction, recall, scoring, or
the memory model itself.

### N4: Retrieval Improvement Only After Baseline

Improve retrieval only after the real baseline table exists.

Preferred first upgrade:

- [ ] BM25 or TF-IDF recall.

Avoid vector databases at this stage. If a dependency is needed, prefer a mature
small package or `scikit-learn` only if it clearly improves quality and keeps the
prototype simple.

Compare:

- [x] `keyword`, smoke fixture.
- [x] `decision_first`, smoke fixture.
- [x] `decision_first_with_recall_count`, smoke fixture.
- [ ] `BM25/TF-IDF`.
- [ ] Real subset comparison.

Do not keep a retrieval policy that does not improve quality, traceability, cost,
or debugging clarity.

### N5: Extraction Upgrade

The current rule-based extractor is useful for smoke tests, but weak for real
LongMemEval data.

Next extraction step:

```text
dataset-aware deterministic extraction
```

Work:

- [ ] Extract facts from benchmark sessions/messages without requiring artificial
   `FACT:` prefixes.
- [ ] Preserve source refs for every extracted fact.
- [ ] Only create decisions from explicit update/commit-like signals in the data.
- [ ] Store ambiguous updates as facts or hypotheses, not decisions.

LLM extraction should be a separate policy later. It should not be mixed into
the first real benchmark result, because it adds cost, randomness, and another
failure source.

### N6: Quality Tooling

Add lightweight tooling after the real subset runner works.

Preferred tools:

- [x] `uv`
- [ ] `ruff`
- [x] `pytest`

Possible additions:

- [ ] `pyright` or `mypy`

Only add type-checking if it catches real mistakes without slowing iteration
too much.

Target commands:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

### Next Milestone Commit

The next large commit should be:

```text
Add real LongMemEval subset runner
```

It should include:

- [ ] Real-schema LongMemEval parser.
- [ ] Local fixture matching that schema.
- [ ] Subset-limit config or CLI override.
- [ ] Benchmark-specific metrics where practical.
- [ ] Baseline comparison report on the subset.
- [ ] README command for `data_path`.
- [ ] Tests and smoke verification.

### Next Definition Of Done

The next stage is complete when these commands work on a local LongMemEval data
path:

```bash
uv run pytest

uv run python -m memorycore.experiments.run_experiment \
  benchmark=longmemeval \
  data_path=/path/to/longmemeval \
  memory=decisions_facts \
  recall=decision_first \
  output_dir=reports/longmemeval_real_subset

uv run python -m memorycore.experiments.run_experiment \
  benchmark=longmemeval \
  data_path=/path/to/longmemeval \
  compare_memories=recent_context_only,simple_rag,fact_only,decisions_facts \
  output_dir=reports/longmemeval_baselines
```

And the generated report makes it clear whether each failure is likely caused by:

```text
extraction
recall
scoring
memory update
abstention
```
