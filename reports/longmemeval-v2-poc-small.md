# LongMemEval-V2 Small POC Run

## Run

- date: 2026-06-03
- artifact path: `/tmp/decision-layer-lmev2-poc-20260603171130`
- benchmark: LongMemEval-V2
- tier: `small`
- subset file: `configs/longmemeval-v2-poc-subset.txt`
- oracle decisions: `configs/longmemeval-v2-poc-oracle-decisions.json`
- reader policy: `openai_chat`
- reader model: `qwen36-35b-a3b-udiq3s`
- reader base URL: `http://127.0.0.1:18080/v1`

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
| D1 | 1.0 | 3 / 3 | 3 / 3 | 164395 | 164517 |
| D2 | 0.0 | 0 / 3 | 0 / 3 | 164331 | 164715 |

- `D1 - D0`: `+1.0`
- `D2 - D0`: `0.0`

## Interpretation

Oracle Decision Layer shows a clear signal on this procedure subset: compact
workflow commitments were enough for the same local reader to answer all three
questions correctly.

Automatic Decision Layer does not show signal yet. D2 extracted no decisions
from these trajectories, which means the current trigger detector is too narrow
for protocol/workflow knowledge. This is an extraction failure, not evidence
against the Decision Layer hypothesis.

The result is not a final benchmark proof. The subset is intentionally small,
and the oracle decisions are hand-written upper-bound commitments. The next
step is to add structured extraction for protocol/workflow candidate messages
and rerun the same subset before expanding.
