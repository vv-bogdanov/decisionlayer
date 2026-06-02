# Implementation Plan

## Context

The repository is currently at the documentation stage. There is no Python package,
test suite, dependency manifest, benchmark harness, or runtime code yet.

The target from the current technical brief is a Python research prototype for:

```text
Agent Memory = Decisions + Facts
```

The goal is not a production SDK, REST API, UI, database product, or framework
adapter. The goal is a reproducible experiment pipeline that can compare memory
variants on existing memory benchmarks.

## Practical Direction

Start with the cheapest verifiable implementation:

1. Minimal Python core.
2. Deterministic in-memory storage.
3. Small local tests and fixtures.
4. One benchmark adapter.
5. Shared runner and metrics output.
6. Only then add sweeps, more benchmarks, and heavier retrieval.

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

1. `set_decision` replaces current decision by `key + scope`.
2. Old decision value is saved as a fact with tags `history` and
   `decision_change`.
3. Facts selected into `MemoryBrief` receive `recall_count += 1`.
4. Important facts and decisions should carry source refs when available.
5. Decision creation/update requires explicit commit signal in extraction policy.

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

1. Adding raw inputs and facts.
2. Creating a decision.
3. Updating a decision and preserving history as fact.
4. Recall returns decisions first.
5. Recall increments `recall_count` for selected facts.
6. Trace explains selected decisions/facts.
7. Forgetting does not remove facts referenced by current decisions.

### CLI

Create a minimal command:

```text
python -m memorycore.experiments.run_experiment benchmark=toy memory=decisions_facts
```

The first benchmark can be a tiny local fixture. This prevents external dataset
download and API keys from blocking core validation.

## Phase P1: LongMemEval And Baselines

Add the first real external benchmark adapter.

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

1. Load local LongMemEval JSON files.
2. Convert sessions/messages into raw inputs.
3. Feed history into memory runtime.
4. Run recall for each question.
5. Produce prediction records.
6. Save trace records.

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

```text
recent_context_only
simple_rag
fact_only
decisions_plus_facts
```

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

Add LLM-as-judge later behind config.

### Reports

Each run should write:

```text
metrics.json
predictions.jsonl
trace.jsonl
report.md
```

The markdown report should include:

```text
summary table
per-policy comparison
sample memory briefs
failure cases
basic cost/token summary
```

## Phase P2: Sweeps And More Benchmarks

### Hydra And Optuna

Add:

```text
run_sweep
best_config.yaml
trials.csv
sweep_report.md
```

Initial tunable parameters:

```text
top_k_facts
top_k_decisions
recall_count_weight
keyword_weight
recency_weight
scope_weight
refs_expansion_depth
max_memory_brief_tokens
forgetting_threshold
```

Start with one objective metric. Multi-objective optimization can wait until the
single-metric pipeline is stable.

### LoCoMo Adapter

Add LoCoMo after LongMemEval. It is useful for long-term conversational memory,
QA over long conversations, temporal facts, and multi-session memory.

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

### MemoryAgentBench Adapter

Add after the simpler adapters are stable. It is broader and heavier, so it
should not block the initial prototype.

## Phase P3: Better Retrieval And Safety

Add only after benchmark reports show where the current prototype fails.

Possible additions:

```text
LLM extraction
LLM extraction safety checks
semantic/vector recall
hybrid keyword/vector recall
refs expansion
reranking
age-aware forgetting
failure analysis reports
multi-objective scoring
```

Keep each addition benchmark-driven. If a new component does not improve quality,
debuggability, cost, or maintainability, remove it.

## Definition Of Done

Single experiment:

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

1. Add `pyproject.toml` with package metadata and test dependencies.
2. Create package skeleton under `memorycore/`.
3. Implement core models and in-memory store.
4. Implement runtime operations.
5. Implement deterministic recall policies.
6. Add focused pytest coverage for core behavior.
7. Add toy benchmark fixture and runner.
8. Add report/traces output.
9. Add LongMemEval adapter using local dataset path from config.
10. Add first baseline comparison report.
