# memorycore

POC for a Codex ADR Decision Layer plugin.

The plugin is not a general memory system. It reads repository ADR markdown
files, treats active `accepted` ADRs as binding decisions, and gives Codex tools
to locate, list, brief, add, and supersede decisions.

## CLI

Run from the repository root:

```bash
scripts/repo-decisions --root . locate
scripts/repo-decisions --root . list
scripts/repo-decisions --root . brief
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

## Codex Wrapper

Use the wrapper when you want Codex to receive the accepted ADR brief without
remembering to call a tool first:

```bash
scripts/repo-decisions --root . codex --print-prompt -- "Implement the next task."
scripts/repo-decisions --root . codex -- "Implement the next task."
```

`--print-prompt` is the safe verification mode. Without it, the wrapper runs
`codex exec --cd <root>` with the enriched prompt.

Pass Codex flags with repeated `--codex-arg`:

```bash
scripts/repo-decisions --root . codex \
  --codex-arg "--sandbox" \
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
the tool instead of editing ADR files directly:

```bash
REPO_DECISIONS_DEBUG_LOG=/tmp/repo-decisions-debug.jsonl \
scripts/repo-decisions --root . add ...
```

The MCP server also writes `mcp-tool-call` events when the environment variable
is set. Write operations include file paths and SHA-256 hashes before and after
the tool action. A benchmark checker can fail any run where ADR files changed
but the debug log has no matching `write` event.

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

The plugin exposes an MCP server with these tools:

- `locate`
- `list`
- `brief`
- `add`
- `supersede`
- `config`

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
python3 -m unittest discover -s tests -v
python3 /home/dev/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py /home/dev/memorycore/plugins/repo-decisions
```
