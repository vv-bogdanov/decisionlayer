# Decision Layer POC Research Report

## Summary

This POC tests whether a compact Decision Layer improves long-horizon task
performance on an external benchmark while keeping the backend/model fixed.

The result is positive but bounded. On the current LongMemEval-V2 slice, D2
extracted decisions improve over current D0 by 11 correct answers overall and by
15 correct answers on procedure tasks. D2 also has zero audited false decisions
and answers all cases with non-empty Decision Briefs correctly.

## Hypothesis

Long-running agents fail partly because accepted decisions drift out of the
active prompt. A Decision Layer should reduce that drift by preserving only
current commitments:

- goals
- requirements
- constraints
- procedures
- stable operating rules

It should not store ordinary facts, UI state, retrieved documents, raw history,
tool outputs, or answer-like observations. Those belong to memory, RAG, storage,
or benchmark-specific context providers.

## Experimental Setup

Benchmark: LongMemEval-V2, text-only local subset.

Model/backend:

```text
http://127.0.0.1:18080/v1
qwen36-35b-a3b-udiq3s
```

Reader settings:

- reasoning disabled
- `/no_think`
- one-line boxed answer contract
- `reader_max_tokens=128`
- `context_max_chars=96000`

Modes:

- D0: no Decision Layer.
- D1: oracle-injected decisions from the narrow decision config.
- D2: automatically extracted decisions.

Primary artifacts:

```text
/tmp/decision-layer-d0-current-no-reasoning
/tmp/decision-layer-d1-narrow-relevant-full-v2
/tmp/decision-layer-d2-narrow-full-v5-procedure-audit
```

Configs:

```text
configs/longmemeval-v2-full-deterministic-subset.txt
configs/longmemeval-v2-full-blind-oracle-decisions.narrow.json
configs/longmemeval-v2-full-blind-accepted-decisions.procedure.json
```

## Results

| Run | Correct | Accuracy | Procedure | Static | Dynamic | Briefs | Adds | False Rate | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D0 current | 31/295 | 0.105085 | 3/74 | 22/134 | 6/86 | 0 | 0 | n/a | n/a |
| D1 narrow v2 | 44/295 | 0.149153 | 19/74 | 22/134 | 3/86 | 17 | 18 | n/a | n/a |
| D2 procedure audit | 42/295 | 0.142373 | 18/74 | 20/134 | 4/86 | 16 | 17 | 0.0 | 0.944444 |

Delta against current D0:

| Run | Overall Delta | Procedure Delta | Static Delta | Dynamic Delta |
| --- | ---: | ---: | ---: | ---: |
| D1 narrow v2 | +13 | +16 | 0 | -3 |
| D2 procedure audit | +11 | +15 | -2 | -2 |

The strongest signal is procedure performance: D2 moves from 3/74 to 18/74 on
procedure tasks. D2 is also close to D1 oracle performance: 42 correct versus 44
overall, and 18 versus 19 on procedure tasks.

## Audit Findings

The first D2 narrow audit reported 28 missing expected decisions because the
accepted oracle still included static and dynamic entries that D2 intentionally
skips under the safety rule. After switching the accepted-decisions audit
denominator to procedure questions only:

- missing expected decisions dropped from 28 to 1
- recall increased from 0.377778 to 0.944444
- false decision rate remained 0.0

The remaining procedure miss is:

```text
7e32e4a2
Do not change any other configuration while placing the order.
```

D1 had this brief and still answered the case incorrectly, so this does not
justify expanding the extractor.

## Interpretation

The data supports a narrow claim:

Decision Layer improves procedural reliability when long-horizon tasks require
remembering accepted workflow decisions.

The data does not support a broad claim that Decision Layer replaces ordinary
memory. Static and dynamic environment questions still need environment memory,
retrieval, observations, or task-specific context gathering.

The current best framing is:

```text
Memory remembers facts.
Decision Layer remembers accepted commitments.
```

## Case Pattern

The useful Decision Briefs were compact and procedural. Examples include:

- use Reports first, then Problems for workload balancing by problem tag
- use Cost > Expense Lines for investment allocation
- use Requested Items before Service Catalog when ordering the same requested item
- use Reports > View/Run and Service Catalog for dashboard-based restocking
- clear Assigned to before deleting a user profile during offboarding

These are not raw facts. They are durable workflow commitments that guide later
actions.

## Threats To Validity

- The result is one deterministic local-reader pass.
- The accepted decision set is conservative but not a fully independent
  hand-labeled gold corpus.
- LongMemEval-V2 measures agent memory over web-environment experience; it is not
  itself a direct "hours of autonomous coding work" benchmark.
- D1 and D2 are compared against a local llama.cpp backend, so absolute accuracy
  should not be compared to frontier model leaderboards.
- The current extractor is intentionally narrow and rule-based, so broader
  generalization is not established.

## Recommendations

1. Publish the current result as a POC, not as a product claim.
2. Keep the Decision Layer definition narrow: accepted commitments only.
3. Do not add extractor rules without repeated high-confidence misses.
4. Use coding-agent benchmarks for the next phase.
5. Measure horizon with task-length proxies, not only aggregate accuracy.

## External Context

This POC uses LongMemEval-V2 as the memory-oriented benchmark:

```text
https://arxiv.org/abs/2605.12493
```

For the next phase, METR's time-horizon framing is the right measurement model:

```text
https://metr.org/time-horizons/
https://arxiv.org/abs/2503.14499
```
