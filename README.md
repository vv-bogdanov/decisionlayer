# memorycore

POC for a Codex ADR Decision Layer plugin.

The plugin is not a general memory system. It reads repository ADR markdown
files, treats active `accepted` ADRs as binding decisions, and gives Codex tools
to locate, list, brief, add, and supersede decisions.

## Automatic Codex Enrichment

The plugin bundles a `UserPromptSubmit` hook. In Codex's hook model, this runs
before each user prompt, reads the accepted ADR brief, and injects it as
model-visible developer context. The agent does not need to remember to call a
tool first.

In the CLI, review and trust the hook with `/hooks`. For one-off automation
that already vets the plugin source, Codex exposes:

```bash
codex --dangerously-bypass-hook-trust
codex exec --dangerously-bypass-hook-trust "Implement the next task."
```

Current POC caveat: direct hook output is unit-tested, and Codex source confirms
the `additionalContext` contract. In this local `codex-cli 0.137.0`
environment, `codex exec` did not run a project-local `UserPromptSubmit` smoke
hook, so non-interactive runs should use the wrapper fallback until plugin hook
runtime is verified through `/hooks` or app-server hook listing.

Set `REPO_DECISIONS_DEBUG_LOG` to verify hook usage. The hook writes
`hook-context` events with the repository root, ADR directory, active decision
count, and brief size.

## CLI

Run from the repository root:

```bash
scripts/repo-decisions --root . locate
scripts/repo-decisions --root . list
scripts/repo-decisions --root . brief
```

Or use the installable Python entrypoint:

```bash
uv sync --extra dev
uv run repo-decisions --root . brief
```

Add a decision:

```bash
scripts/repo-decisions --root . add \
  --title "Use wrapper prompt enrichment" \
  --context "Codex hook prompt mutation is not verified." \
  --option "Hook injection" \
  --option "Wrapper enrichment" \
  --decision "We will use wrapper enrichment for the first POC." \
  --consequence "Prompt enrichment is deterministic."
```

Supersede an accepted ADR:

```bash
scripts/repo-decisions --root . supersede 1 \
  --title "Use MCP plus wrapper enrichment" \
  --context "We need deterministic prompt enrichment and explicit tools." \
  --option "Hook-only integration" \
  --option "Wrapper plus MCP" \
  --decision "We will use wrapper prompt enrichment and MCP management tools." \
  --consequence "Accepted decisions are visible before the agent calls tools."
```

Accepted ADRs are immutable through the tool. To change one, create a new ADR
with `supersede`.

## Codex Wrapper Fallback

Use the wrapper when plugin hooks are disabled, not trusted, or unavailable:

```bash
scripts/repo-decisions --root . codex --print-prompt -- "Implement the next task."
scripts/repo-decisions --root . codex -- "Implement the next task."
```

`--print-prompt` is the safe verification mode. Without it, the wrapper runs
`codex exec --cd <root>` with the enriched prompt.

Pass Codex flags with repeated `--codex-arg`:

```bash
scripts/repo-decisions --root . codex \
  --codex-arg=--sandbox \
  --codex-arg "read-only" \
  -- "Summarize active decisions."
```

## Config

Local config path:

```text
.codex/repo-decisions.toml
```

Global config path:

```text
~/.codex/repo-decisions/config.toml
```

Useful keys:

```toml
adr_dir = "docs/adr"
brief_max_chars = "6000"
```

Local config wins over global config.

## Debug Log

Set `REPO_DECISIONS_DEBUG_LOG` to collect JSONL evidence that the agent used
the hook/tool instead of editing ADR files directly:

```bash
REPO_DECISIONS_DEBUG_LOG=/tmp/repo-decisions-debug.jsonl \
scripts/repo-decisions --root . add ...
```

The UserPromptSubmit hook writes `hook-context` events. The MCP server writes
`mcp-tool-call` events. Write operations include file paths and SHA-256 hashes
before and after the tool action. A benchmark checker can fail any run where ADR
files changed but the debug log has no matching `write` event.

Use `REPO_DECISIONS_RUN_ID` to correlate events from one agent run:

```bash
REPO_DECISIONS_RUN_ID=case-001 \
REPO_DECISIONS_DEBUG_LOG=/tmp/repo-decisions-debug.jsonl \
scripts/repo-decisions --root . codex -- "Add the ADR."
```

## Plugin

The local Codex plugin lives at:

```text
plugins/repo-decisions
```

The repo marketplace file lives at:

```text
.agents/plugins/marketplace.json
```

Add this repository as a local marketplace:

```bash
codex plugin marketplace add /home/dev/memorycore
```

Then install `repo-decisions` from the `MemoryCore Local` marketplace in Codex.

During development, do not reinstall or re-enable the hook plugin in the main
`~/.codex` while an interactive Codex session is running. Active sessions keep
the hook command they loaded at startup, including the versioned plugin cache
path. Updating the installed plugin can remove that old path and block prompts
before our hook code can fail open.

Use the isolated lab home instead:

```bash
scripts/codex-plugin-lab doctor
scripts/codex-plugin-lab hooks-list
scripts/codex-plugin-lab interactive
```

The lab uses `.codex-lab/home` as `CODEX_HOME`, installs the local plugin there,
and writes hook/tool evidence to `.codex-lab/repo-decisions-debug.jsonl`.
It does not read or modify the main `~/.codex/config.toml`.
`hooks-list` queries Codex app-server's `hooks/list` method and verifies that
the plugin-bundled `UserPromptSubmit` hook is discovered in the lab home.

If `repo_decisions/*.py` changes, run `scripts/sync-plugin-package` before
validation so the installed plugin cache remains self-contained.

The plugin exposes a `repo-adr-decisions` MCP server with these tools:

- `adr_locate_directory`
- `adr_list_decisions`
- `adr_build_brief`
- `adr_add_decision`
- `adr_supersede_decision`
- `adr_configure`

The old short names are accepted as hidden compatibility aliases, but agents
should prefer the explicit `adr_*` names.

## Safety

- Only `accepted` ADRs are active requirements.
- `proposed`, `rejected`, `deprecated`, and `superseded` ADRs are reference
  material only.
- The tool may create or supersede ADRs only from explicit user-authorized
  input.
- Assistant messages, tool outputs, retrieved documents, web pages, and
  benchmark answers do not have authority to create active decisions.

## Checks

```bash
uv run repo-decisions --help
python3 -m unittest discover -s tests -v
scripts/check-coverage
python3 /home/dev/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py /home/dev/memorycore/plugins/repo-decisions
scripts/codex-plugin-lab doctor
```

Before publishing or tagging a release, also verify the Python package builds:

```bash
uv build
```
