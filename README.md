# Decision Layer

Decision Layer is a minimal research POC for testing whether compact accepted
decisions improve long-horizon agent benchmark performance under the same
backend/model.

```text
Memory remembers facts.
Decision Layer remembers accepted commitments.
```

Accepted commitments include goals, requirements, constraints, procedures, and
stable operating rules. Environment facts, UI state, raw history, retrieved
documents, embeddings, storage, extraction, judges, and benchmark runners are
external systems or plugins.

## Current Result

The current POC uses LongMemEval-V2 with a local llama.cpp OpenAI-compatible
reader and reasoning disabled.

| Run | Correct | Accuracy | Procedure | Static | Dynamic | False Rate | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D0 current | 31/295 | 0.105085 | 3/74 | 22/134 | 6/86 | n/a | n/a |
| D1 narrow v2 | 44/295 | 0.149153 | 19/74 | 22/134 | 3/86 | n/a | n/a |
| D2 procedure audit | 42/295 | 0.142373 | 18/74 | 20/134 | 4/86 | 0.0 | 0.944444 |

Headline: D2 improves over current D0 by 11 correct answers overall and by 15
correct answers on procedure tasks. All 16 cases with non-empty Decision Briefs
were answered correctly.

See:

- [Research report](docs/research-report.md)
- [Current POC result](reports/current-poc-result.md)
- [Reproducibility](docs/reproducibility.md)
- [Design](docs/decision-layer-design.md)
- [Coding benchmark selection](docs/coding-benchmark-selection.md)

## What This Is Not

This is not a production memory platform. The first POC intentionally excludes:

- REST API
- UI
- production storage
- SDK
- vector DB
- graph memory
- reranker
- custom benchmark

The point is to isolate whether accepted decisions help before adding
infrastructure.

## Development

```bash
uv sync --extra dev
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
scripts/reproduce-current-result smoke
```

Equivalent direct command:

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

The full deterministic all-topic subset is pinned in:

```text
configs/longmemeval-v2-full-deterministic-subset.txt
```

It contains 295 questions and excludes judge-only eval functions.

## Full Reproduction

The full reproduction requires a local OpenAI-compatible reader:

```text
READER_BASE_URL=http://127.0.0.1:18080/v1
READER_MODEL=qwen36-35b-a3b-udiq3s
READER_MAX_TOKENS=128
CONTEXT_MAX_CHARS=96000
```

Run:

```bash
scripts/reproduce-current-result full
```

The full run is expensive and writes artifacts under `/tmp`.

## Local Reader

Use an OpenAI-compatible local reader such as llama.cpp router. The current POC
used reasoning disabled. The repository does not start or manage the model
server.

## Overnight Run

Prepare and run the full deterministic all-topic suite with a canary gate first:

```bash
scripts/run-overnight-poc
```

To run only the canary gate:

```bash
CANARY_ONLY=1 scripts/run-overnight-poc
```

Artifacts are written to `/tmp/decision-layer-overnight-*` by default. Override
`OUTPUT_DIR`, `DATA_ROOT`, `READER_BASE_URL`, `READER_MODEL`,
`READER_MAX_TOKENS`, or `CONTEXT_MAX_CHARS` when needed.

The overnight runner resumes by default. Use `OVERWRITE=1` to force a fresh
output directory and rerun reader calls.

## License

Apache-2.0. See [LICENSE](LICENSE).
