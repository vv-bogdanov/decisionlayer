# ADR-Agent Canary Notes

Date: 2026-06-05

Runner:

- `pi --provider llamacpp --model qwen36-35b-a3b-udiq3s --thinking off --no-session`
- Local llama.cpp backend with reasoning disabled.

These runs are fixture canaries, not benchmark proof. They test whether the
agent respects repository ADRs and uses the decision tool surface when the task
requires changing ADRs.

## Runs

### `pi-code-jsonl-001`

Case: `code-follows-jsonl-adr`

| Mode | Status | Prompt chars | Duration | Changed files | Tool calls | Writes |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| D0 | passed | 120 | 13.003s | 1 | 0 | 0 |
| D1 | passed | 2201 | 14.123s | 1 | 0 | 0 |
| D2 | passed | 2501 | 11.143s | 1 | 0 | 0 |

Interpretation: this case does not separate baseline from ADR enrichment yet.
The task explicitly tells the agent to follow accepted ADRs, and a coding agent
can inspect repository files directly.

### `pi-format-compare-001`

Case: `format-preservation-add-adr`

| Mode | Status | Prompt chars | Duration | Changed ADR files | Tool calls | Writes |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| D0 | failed | 269 | 15.465s | 1 | 0 | 0 |
| D1 | failed | 2350 | 11.097s | 1 | 0 | 0 |
| D2 | passed | 2873 | 46.404s | 1 | 3 | 1 |

Interpretation: D0 and D1 produced plausible ADR files, but edited ADR
markdown directly and had no repo-decisions debug write event. D2 passed
because the prompt exposed `REPO_DECISIONS_CLI` as a non-MCP fallback and the
agent used it.

## Harness Fixes From This Run

- Runtime artifacts such as `__pycache__`, `.pytest_cache`, `.coverage`, and
  `*.pyc` are cleaned before diff/check metrics.
- Agent subprocesses set `GIT_CEILING_DIRECTORIES` so fixture workspaces under
  this repository do not accidentally resolve the parent repository as the
  target root.
- D2 accepts either `mcp-tool-call` or `cli-command` debug evidence, because
  local non-MCP runners can use the CLI fallback.

## Next

- Run the remaining fixture cases with the same runner.
- Add at least one real repository canary after pinning a small ADR-bearing
  repository by commit SHA.
- Keep using wrapper/CLI fallback until isolated Codex lab runtime proof records
  a real `hook-context` event.
