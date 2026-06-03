# LongMemEval-V2 Small POC Run

## Run

- date: 2026-06-03
- artifact path: `/tmp/decision-layer-poc-check-audit`
- verified command: `scripts/run-poc-check`
- benchmark: LongMemEval-V2
- tier: `small`
- subset file: `configs/longmemeval-v2-poc-subset.txt`
- oracle decisions: `configs/longmemeval-v2-poc-oracle-decisions.json`
- reader policy: `openai_chat`
- reader model: `qwen36-35b-a3b-udiq3s`
- reader base URL: `http://127.0.0.1:18080/v1`
- accepted D2 decisions: `configs/longmemeval-v2-poc-accepted-d2-decisions.json`

## Subset

The subset is procedure-only and uses deterministic official-style scoring:

- `025db8ef`: procedure, ordered phrase match
- `0b50ca0d`: procedure, multiple choice
- `100ff132`: procedure, multiple choice

All 3 examples are scorable locally. No LLM judge examples are included.

## Results

| Mode | Accuracy | Correct | Non-empty Briefs | Prompt Tokens | Total Tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| D0 | 0.0 | 0 / 3 | 0 / 3 | 164193 | 164577 |
| D1 | 1.0 | 3 / 3 | 3 / 3 | 164395 | 164518 |
| D2 | 1.0 | 3 / 3 | 3 / 3 | 164520 | 164622 |

- `D1 - D0`: `+1.0`
- `D2 - D0`: `+1.0`
- D2 false decision rate: `0.0`
- D2 decision recall: `1.0`
- D2 decision persistence rate: `1.0`

## Category Effect

| Category | D0 | D1 | D2 | D1-D0 | D2-D0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| procedure | 0.0 | 1.0 | 1.0 | +1.0 | +1.0 |

## D2 Extraction

Structured D2 processed 300 user-goal messages across the three examples and
found 42 workflow candidates. After per-example deduplication, it added 9
decision events: three active decisions per example.

The active D2 decisions were:

- For Agent Workload Balancing, use Reports first, then Problems.
- For incident-report criteria tasks that create item requests, use Open
  Records > Items (Item Requests).
- To locate an incident-related performance report, use the All filter, type
  reports, open View/Run, then locate the relevant report.

## Interpretation

Oracle Decision Layer shows a clear signal on this procedure subset: compact
workflow commitments were enough for the same local reader to answer all three
questions correctly.

Automatic Decision Layer now matches the oracle result on this small subset.
The signal comes from structured workflow extraction over user goal text, not
from tool outputs or external documents.

The result is not a final benchmark proof. The subset is intentionally small,
and the extractor includes POC-specific workflow rules. The next step is to
audit false-decision risk, add category-level reporting, then expand the subset.

## Scope Limits

- LLM judge scoring is not needed for this subset: all three examples use
  deterministic LongMemEval-V2 eval functions.
- Evidence-quality scoring is not available for the selected text-only subset.
- Cost estimate is not reported because the reader is a local llama.cpp model
  without model pricing.
- Decision update correctness is not exercised because this subset contains no
  replace/remove decision events.
