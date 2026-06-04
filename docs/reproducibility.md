# Reproducibility

This document records how to reproduce the current Decision Layer POC result.

The full run is intentionally local and model-dependent. The smoke checks are
cheap and should pass on any development machine. The full LongMemEval-V2 run
requires prepared benchmark data and a local OpenAI-compatible reader.

## Environment

Requirements:

- Python 3.11 or newer
- `uv`
- local llama.cpp OpenAI-compatible endpoint for the full run
- LongMemEval-V2 text-only data prepared under `data/longmemeval-v2`

The current full result used:

```text
reader_base_url=http://127.0.0.1:18080/v1
reader_model=qwen36-35b-a3b-udiq3s
reader_max_tokens=128
context_max_chars=96000
reasoning=off
```

The llama.cpp server was started externally. This repository does not manage the
model server.

## Install

```bash
uv sync --extra dev
```

## Development Checks

```bash
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
uv run --extra dev mypy src/decision_layer
```

## Dataset Preparation

Prepare LongMemEval-V2 data:

```bash
scripts/prepare-longmemeval-v2 data/longmemeval-v2
```

The repository intentionally ignores `data/`, so prepared benchmark files are
local artifacts.

The deterministic full subset is:

```text
configs/longmemeval-v2-full-deterministic-subset.txt
```

It contains 295 questions and excludes judge-only eval functions.

## Smoke Reproduction

Run the cheap fixture-level smoke:

```bash
scripts/reproduce-current-result smoke
```

This validates the package, tests, and a fixture POC run. It does not reproduce
the full research numbers.

## Full Current D0 Baseline

```bash
uv run decision-layer run-poc \
  --data-root data/longmemeval-v2 \
  --output-dir /tmp/decision-layer-d0-current-no-reasoning \
  --mode D0 \
  --tier small \
  --question-id-file configs/longmemeval-v2-full-deterministic-subset.txt \
  --reader openai-chat \
  --reader-base-url http://127.0.0.1:18080/v1 \
  --reader-model qwen36-35b-a3b-udiq3s \
  --reader-max-tokens 128 \
  --context-max-chars 96000
```

Expected final metrics:

```text
correct=31/295
accuracy=0.105085
procedure=3/74
static=22/134
dynamic=6/86
```

## Full Current D2 Procedure Audit

```bash
uv run decision-layer run-poc \
  --data-root data/longmemeval-v2 \
  --output-dir /tmp/decision-layer-d2-narrow-full-v5-procedure-audit \
  --mode D2 \
  --tier small \
  --question-id-file configs/longmemeval-v2-full-deterministic-subset.txt \
  --reader openai-chat \
  --reader-base-url http://127.0.0.1:18080/v1 \
  --reader-model qwen36-35b-a3b-udiq3s \
  --reader-max-tokens 128 \
  --context-max-chars 96000 \
  --accepted-decisions configs/longmemeval-v2-full-blind-accepted-decisions.procedure.json
```

Expected final metrics:

```text
correct=42/295
accuracy=0.142373
procedure=18/74
static=20/134
dynamic=4/86
false_decision_rate=0.0
decision_recall=0.944444
```

## D1 Oracle Reference

D1 is an upper-bound reference because it injects narrow oracle decisions:

```bash
uv run decision-layer run-poc \
  --data-root data/longmemeval-v2 \
  --output-dir /tmp/decision-layer-d1-narrow-relevant-full-v2 \
  --mode D1 \
  --tier small \
  --question-id-file configs/longmemeval-v2-full-deterministic-subset.txt \
  --reader openai-chat \
  --reader-base-url http://127.0.0.1:18080/v1 \
  --reader-model qwen36-35b-a3b-udiq3s \
  --reader-max-tokens 128 \
  --context-max-chars 96000 \
  --oracle-decisions configs/longmemeval-v2-full-blind-oracle-decisions.narrow.json
```

Expected final metrics:

```text
correct=44/295
accuracy=0.149153
procedure=19/74
static=22/134
dynamic=3/86
```

## Streaming Artifacts

Long runs write artifacts as each example completes:

```text
predictions.jsonl
brief_trace.jsonl
decision_trace.jsonl
metrics.partial.json
metrics.json
report.md
```

Runner resume is enabled by default and keyed by request hash. Use `--no-resume`
only when intentionally overwriting cached reader outputs.
