# Decision Layer

A minimal POC for testing whether a compact layer of current accepted decisions
improves the same long-horizon benchmark backend.

```text
Memory remembers facts.
Decision Layer remembers commitments.
```

## Development

```bash
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
uv run --extra dev mypy src/decision_layer
```

## CLI Smoke

```bash
uv run decision-layer --state /tmp/decision-state.json add "Use Python for the POC."
uv run decision-layer --state /tmp/decision-state.json list
uv run decision-layer --state /tmp/decision-state.json brief
```

## POC Smoke

```bash
uv run decision-layer run-suite \
  --data-root tests/fixtures/longmemeval_v2 \
  --output-dir /tmp/decision-layer-poc \
  --question-id q_static \
  --oracle-decisions tests/fixtures/longmemeval_v2/oracle_decisions.json
```

## Dataset

Prepare the text-only LongMemEval-V2 files outside the runner:

```bash
scripts/prepare-longmemeval-v2 data/longmemeval-v2
```

The first real-data POC subset is pinned in
`configs/longmemeval-v2-poc-subset.txt`.

## Local Reader

Use an OpenAI-compatible local reader such as llama.cpp router:

```bash
uv run decision-layer run-suite \
  --data-root data/longmemeval-v2 \
  --output-dir /tmp/decision-layer-llama \
  --question-id-file configs/longmemeval-v2-poc-subset.txt \
  --reader openai-chat \
  --reader-base-url http://127.0.0.1:18080/v1 \
  --reader-model qwen36-35b-a3b-udiq3s \
  --oracle-decisions configs/longmemeval-v2-poc-oracle-decisions.json
```
