# ADR-Agent Canary Notes

Date: 2026-06-05

Runner:

- `pi --provider llamacpp --model qwen36-35b-a3b-udiq3s --thinking off --no-session`
- Local llama.cpp backend with reasoning disabled.

These runs are fixture canaries, not benchmark proof. They test whether the
agent respects repository ADRs and uses the decision tool surface when the task
requires changing ADRs.

## Real Repository Candidate Scan

Pinned metadata is stored in `benchmarks/adr_agent/repos.toml`.

| Repo | Commit | ADR dir | Notes |
| --- | --- | --- | --- |
| `asyncapi/studio` | `a17876ad12cd213643fbd9425bfba028bc4f38fa` | `doc/adr` | First real canary candidate; numbered ADRs with accepted/proposed statuses. |
| `adr/e-adr` | `312d88800121de7051729df5fc15e629102defa6` | `docs/decisions` | Good format-detection candidate; current records have no explicit status. |
| `thomvaill/log4brains` | `17e32021a8c5130386f17e921d4efa6da7709a66` | `docs/adr` | Dated Log4brains ADRs and nested package ADRs. |
| `sbomify/sbomify` | `e7c86fd14f9a1e3975efc51e3fa094665ee6f9e6` | `docs/ADR` | Uses `.adr-dir`; this scan drove `.adr-dir` and uppercase ADR directory support. |

Real-repo scan fixes:

- `.adr-dir` is now supported as an ADR directory source.
- Uppercase `docs/ADR`, `doc/ADR`, and `ADR` common directories are considered.
- Explicit `## Status` sections now win over inline/code-like `status:` mentions
  elsewhere in an ADR body.

## Fixture Runs

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

### `pi-fixtures-002`

Cases: all five local fixtures after adding the CLI fallback and root-isolation
fixes.

| Case | D0 | D1 | D2 |
| --- | --- | --- | --- |
| `code-follows-jsonl-adr` | passed | failed | passed |
| `format-preservation-add-adr` | failed | passed | passed |
| `supersede-accepted-adr` | failed | failed | passed |
| `conflict-requires-supersede-confirmation` | failed | failed | failed |
| `no-false-decision-creation` | passed | passed | passed |

Important observations:

- `supersede-accepted-adr` is the clearest decision-tool case: only D2 passed
  because it used the repo-decisions CLI and produced write evidence.
- `format-preservation-add-adr` passed in D1 once the local runner discovered an
  installed `repo-decisions` CLI, but D2 is the intended reliable path because
  it explicitly exposes the tool surface.
- `conflict-requires-supersede-confirmation` caught a real D2 prompt weakness:
  the agent detected the conflict but still changed code. The D2 prompt was
  updated to require stopping and asking for explicit supersede confirmation
  before changing code or ADRs.
- `no-false-decision-creation` now passes all modes after broadening the oracle
  to accept semantically equivalent "not an accepted ADR / not authorized"
  wording.

Follow-up run:

| Run | Case | Mode | Status | Changed files |
| --- | --- | --- | --- | ---: |
| `pi-conflict-d2-003` | `conflict-requires-supersede-confirmation` | D2 | passed | 0 |

The follow-up run confirms the hardened D2 guidance can make the local runner
stop on a conflicting request and ask for supersede confirmation without editing
code.

## Real Repo Canary

### `pi-asyncapi-real-001`

Case: `real-asyncapi-format-add-adr`

Source: `asyncapi/studio` at
`a17876ad12cd213643fbd9425bfba028bc4f38fa`.

| Mode | Status | Prompt chars | Duration | Changed ADR files | Tool calls | Writes |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| D2 | passed | 3034 | 34.018s | 1 | 6 | 1 |

The agent created
`doc/adr/0010-expire-generated-api-preview-sessions-after-30-minutes-of-inactivity.md`
through `repo-decisions --root . add`. The generated ADR preserved the real
repository's format:

- `# 10: ...` heading style.
- `**Date:** YYYY-MM-DD`.
- `## Status`, `## Context`, `## Decision`, and `## Consequences` sections.
- Zero-padded filename numbering after ADR-0009.

### `pi-asyncapi-variants-001`

Case: `real-asyncapi-format-add-adr`

Source: `asyncapi/studio` at
`a17876ad12cd213643fbd9425bfba028bc4f38fa`.

| Brief Variant | Status | Prompt chars | Duration | Tool calls | Writes | Notes |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `standard` | passed | 3034 | 33.308s | 4 | 1 | Best default candidate: short, direct, and preserved accepted status. |
| `strict` | passed | 3114 | 46.339s | 5 | 1 | Passed, but slower and did not improve this case. |
| `y` | failed | 3744 | 20.929s | 3 | 1 | Created `Proposed` instead of required `Accepted`; too narrative for this task. |
| `excerpt` | passed | 4169 | 30.119s | 5 | 1 | Passed and produced richer ADR content, but uses the largest prompt. |

Interpretation: the current compact hard-requirements brief remains the best
default for the POC. The Y-statement variant is useful as a research comparator
but should not be the default because the local runner dropped the required
accepted status in this canary. Fuller excerpts may help when context quality
matters, but they spend more prompt budget and need broader evidence before
becoming default.

## Harness Fixes From This Run

- Runtime artifacts such as `__pycache__`, `.pytest_cache`, `.coverage`, and
  `*.pyc` are cleaned before diff/check metrics.
- Agent subprocesses set `GIT_CEILING_DIRECTORIES` so fixture workspaces under
  this repository do not accidentally resolve the parent repository as the
  target root.
- D2 accepts either `mcp-tool-call` or `cli-command` debug evidence, because
  local non-MCP runners can use the CLI fallback.
- D2 now explicitly tells the agent to stop and ask for supersede confirmation
  before making a code change that conflicts with an accepted ADR.

## Next

- Expand real repository canaries using the pinned repository metadata.
- Keep `standard` as the default brief while using `strict`, `y`, and `excerpt`
  only for prompt-selection experiments.
- Keep using wrapper/CLI fallback until isolated Codex lab runtime proof records
  a real `hook-context` event.
