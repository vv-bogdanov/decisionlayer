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
  --limit 1 \
  --oracle-decisions tests/fixtures/longmemeval_v2/oracle_decisions.json
```
