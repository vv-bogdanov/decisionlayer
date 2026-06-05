# Codex Hook Feasibility Notes

Date: 2026-06-05
Codex CLI: 0.137.0

## Question

Can a `UserPromptSubmit` command hook mutate the model-visible prompt so the
ADR requirements block is injected automatically?

## Checks

### `codex debug prompt-input`

A temporary `CODEX_HOME` with `hooks.json` was created. The hook wrote a marker
file and printed a unique marker to stdout.

Result:

- The hook marker file was not created.
- The marker did not appear in `codex debug prompt-input` output.

Conclusion: `codex debug prompt-input` renders the prompt input but does not
execute lifecycle hooks in this version, so it cannot prove hook prompt
mutation.

### `codex exec` with temporary project hook

A temporary Git repository with `.codex/hooks.json` and a
`UserPromptSubmit` command hook was used with
`--dangerously-bypass-hook-trust`.

Result:

- The hook marker file was not created.

Likely cause: project-local `.codex` config was not trusted/loaded in this
throwaway repository.

### `codex exec` with inline hook config

An inline `-c hooks.UserPromptSubmit=...` configuration was tried to avoid
writing to the real user-level Codex config.

Result:

- The hook marker file was not created.
- The test prompt was rejected by model safety before producing useful
  evidence.

## Decision

Use a wrapper fallback for the first POC. The wrapper can deterministically
prepend the ADR requirements block to the user prompt before invoking Codex.

Keep hook support as a later optional integration path, but do not make the POC
depend on unverified command-hook prompt mutation.

## Implication

Phase 4 should implement:

- `repo-decisions brief` as the shared enrichment primitive.
- `repo-decisions codex ...` as the reliable wrapper path.
- Codex hook packaging only as optional refresh/logging or future injection
  support after a manual `/hooks` trust flow proves the behavior.
