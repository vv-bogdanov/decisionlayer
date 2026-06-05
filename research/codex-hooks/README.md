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

Use a plugin-bundled `UserPromptSubmit` hook as the primary automatic
enrichment path. Keep the wrapper as a fallback for executions where hooks are
disabled, unavailable, or not yet trusted.

## Implication

The plugin should implement:

- `repo-decisions brief` as the shared enrichment primitive.
- `hooks/hooks.json` with a `UserPromptSubmit` command hook.
- A hook script that returns `hookSpecificOutput.additionalContext`.
- `repo-decisions codex ...` as the wrapper fallback.

## Source Follow-up

After the initial runtime spikes, the Codex source confirmed the intended
mechanism:

- `codex-rs/hooks/src/events/user_prompt_submit.rs` parses
  `hookSpecificOutput.additionalContext` from hook JSON output. Plain non-JSON
  stdout is also treated as additional context.
- `codex-rs/core/src/hook_runtime.rs` records hook additional contexts as
  `HookAdditionalContext`.
- `codex-rs/core/src/context/hook_additional_context.rs` marks that fragment
  with role `developer`.

So the failed smoke tests above did not disprove prompt enrichment. They showed
that `codex debug prompt-input` does not execute lifecycle hooks and that the
temporary project hook was probably not loaded or trusted.

## Alternatives Checked

- `AGENTS.md`: loaded once per run/session and limited to static repository
  guidance. It cannot run a command to refresh ADR decisions before each prompt.
- `developer_instructions` / `model_instructions_file`: config-time/static
  instruction overrides, not dynamic prompt enrichment.
- `codex exec` stdin additional context: works, but requires a wrapper or a
  changed invocation.
- `thread/inject_items` app-server API: can append model-visible history, but
  requires a custom app-server client instead of normal CLI usage.
- Forking Codex CLI: possible but too much maintenance for this POC.

Conclusion: in normal Codex CLI usage, the supported dynamic automatic channel
is a lifecycle hook. Without a hook, the practical options are wrapper,
app-server client, or fork.

## Runtime Smoke Follow-up

Additional local checks were run against installed `codex-cli 0.137.0`:

- `codex features list` reports `hooks` as enabled.
- The installed native binary contains `UserPromptSubmit`, `additionalContext`,
  `hooks.json`, and `--dangerously-bypass-hook-trust` strings.
- `codex exec` with inline hook config and `--dangerously-bypass-hook-trust`
  did not run the hook; no `REPO_DECISIONS_DEBUG_LOG` file was created.
- `codex exec` with a temporary trusted project `.codex/hooks.json`, temporary
  accepted ADR marker, `--enable hooks`, and
  `--dangerously-bypass-hook-trust` also did not run the hook.

This means the source-level contract is clear, but we do not yet have runtime
proof that `codex exec` executes `UserPromptSubmit` in this environment. For
non-interactive benchmark runs, the verified path remains the wrapper unless
app-server `hooks/list` or an interactive `/hooks` flow proves plugin hook
execution.
