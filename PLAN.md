# Decision Layer Next Run Plan

## Current Context

Full deterministic LongMemEval-V2 run artifacts:

```text
/tmp/decision-layer-overnight-20260603212552/full
```

Blind D1 full run artifacts:

```text
/tmp/decision-layer-d1-blind-full
```

New D2 full run artifacts after adding investment/offboarding extraction:

```text
/tmp/decision-layer-d2-blind-full
```

Latest D2 full run artifacts after targeted workflow enrichment:

```text
/tmp/decision-layer-d2-blind-full-v2
```

Current result is useful as a pipeline and baseline check, but not as a full
Decision Layer proof. The current D1 oracle contains only a few accepted
commitments, so D1 is not yet a real upper bound.

Key current metrics:

| Mode | Correct | Accuracy | Non-empty Briefs |
| --- | ---: | ---: | ---: |
| D0 | 21/295 | 0.071186 | 0 |
| D1 | 24/295 | 0.081356 | 4 |
| D2 | 25/295 | 0.084746 | 6 |
| Blind D1 | 30/295 | 0.101695 | 74 |
| New D2 | 29/295 | 0.098305 | 11 |
| D2 v2 | 36/295 | 0.122034 | 14 |

Main signal: `procedure` improved from `1/74` in D0 to `6/74` in D2, but this
is based on sparse commitment coverage.

Blind D1 full improves `procedure` to `9/74` with 74 non-empty procedure
briefs. Exact D0-vs-blind-D1 diff: 11 D1-only correct, 2 regressions, net +9.

New D2 improves old D2 from `25/295` to `29/295` and matches blind D1 on
`procedure` at `9/74`, with only 11 non-empty Decision Briefs. D2 audit against
the broad blind oracle has `false_decision_rate=0.0`, but recall is not useful
yet because the draft oracle contains about 70k question-level requirements.

Targeted D2 smoke after enriching problem-request, investment, offboarding, and
stock-restocking decisions: `7/7` correct on `07ffeedf`, `25b00876`,
`4df5e6b4`, `52dd33bb`, `75816b26`, `bfb3bcc4`, and `e334d5c6`, with
`false_decision_rate=0.0`.

D2 v2 full improves old D2 from `25/295` to `36/295` and improves `procedure`
from `6/74` to `13/74`, using only 14 non-empty Decision Briefs. Audit
false-decision rate remains `0.0`. Recall is still not meaningful against the
broad draft oracle. These D2 v2 metrics were produced before the reader prompt
contract was tightened.

Targeted reader-contract smoke after adding `/no_think`, one-line boxed output,
and a more explicit stock-restocking module decision:

```text
/tmp/decision-layer-reader-contract-smoke
```

Result: `2/2` correct on `3a2e9368` and `eb3cfd03`, with only 12 completion
tokens total. `3a2e9368` was mainly a clipped/verbose reader-output issue.
`eb3cfd03` needed the decision to state the exact module set:
`Reports > View/Run` and `Self-Service > Service Catalog`, with no approvals,
procurement, request-management, or stockroom modules.

Blind D1 canary after goal labels + rule-based goal augmentation:

| Mode | Correct | Procedure Correct |
| --- | ---: | ---: |
| D0 baseline canary | 1/13 | 0/4 |
| D1 blind canary | 4/13 | 3/4 |

Decision Briefs should contain only accepted decisions, explicit requirements,
constraints, procedures, and stable operating rules. They should not contain
plain environment facts, UI state, answer keys, or transient observations.

## Active Checklist

- [ ] Audit the draft manually: remove facts, answer-like statements,
  UI state, long observations, weak guesses, and duplicates.
- [ ] Narrow/audit the broad blind oracle before treating `decision_recall` as a
  meaningful metric.
- [ ] Re-run full D2 after the reader-output contract and stock-restocking
  clarification, then refresh the metrics table.
- [ ] Improve decision retrieval/ranking to reduce D1 noise, especially
  `767e4106`.

## Next D1 Command

After the blind oracle is ready:

```bash
uv run decision-layer run-poc \
  --data-root data/longmemeval-v2 \
  --output-dir /tmp/decision-layer-d1-blind-full \
  --mode D1 \
  --tier small \
  --question-id-file configs/longmemeval-v2-full-deterministic-subset.txt \
  --reader openai-chat \
  --reader-base-url http://127.0.0.1:18080/v1 \
  --reader-model qwen36-35b-a3b-udiq3s \
  --reader-max-tokens 128 \
  --context-max-chars 96000 \
  --oracle-decisions configs/longmemeval-v2-full-blind-oracle-decisions.json
```
