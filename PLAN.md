# Codex ADR Decision Plugin POC Plan

## Goal

Build a minimal Codex CLI plugin that automatically keeps repository decisions
visible to the agent and exposes explicit tools to add and supersede ADRs.

The plugin is a Decision Layer, not a memory system. It reads plain markdown
ADRs from the repository, injects active accepted decisions into the prompt, and
lets the user manage decisions through tools.

## Current Decisions

- The source of truth is repository ADR markdown files.
- The plugin must preserve the ADR format already used in a repository.
- If no ADR convention exists, the fallback format is Nygard-compatible with
  the useful MADR addition of `Considered Options`.
- Accepted ADRs are immutable through the tool. Changes happen only through
  `supersede`.
- Only active `accepted` ADRs become prompt requirements.
- `proposed`, `rejected`, `deprecated`, and `superseded` ADRs stay visible via
  tools but are not injected as active requirements.
- No custom ADR schema, database, vector index, graph memory, RAG, REST API, UI,
  or custom benchmark for this POC.

## Done

- [x] Reset `main` to a minimal baseline and save the old repo state in
      `backup/pre-adr-plugin-reset-20260605`.
- [x] Study ADR practices and templates: Nygard, MADR, adr-tools, arc42, AWS,
      Y-Statements, and template comparison notes.
- [x] Save ADR research notes in `research/adr-standards/README.md`.
- [x] Simplify the plan around immutable accepted ADRs and `supersede`.

## Active Plan

### Phase 1: Hook Feasibility

- [ ] Create a tiny temporary `UserPromptSubmit` command hook.
- [ ] Use `codex debug prompt-input` to verify whether hook output can mutate
      the model-visible prompt.
- [ ] Record the result in `research/codex-hooks/README.md`.
- [ ] Choose the enrichment path:
      hook if prompt mutation works, wrapper fallback if it does not.

### Phase 2: ADR Core CLI

- [ ] Implement `repo-decisions locate`.
- [ ] Implement fast ADR directory discovery:
      local config, global config, existing ADR templates/examples, common ADR
      directories, then default `docs/adr`.
- [ ] Implement ADR format profiling from existing files:
      filename numbering, date/status placement, heading names, section order,
      and template file detection.
- [ ] Implement `repo-decisions list`.
- [ ] Implement `repo-decisions brief` that emits a compact requirements block
      from active accepted ADRs only.
- [ ] Implement `repo-decisions add` using the repository's current template or
      nearest recent ADR as the structural example.
- [ ] Implement `repo-decisions supersede`:
      create a replacement ADR, mark the old ADR as superseded, and backlink
      both records.
- [ ] Implement `repo-decisions config` for local/global defaults and prompt
      size limits.

### Phase 3: Tests

- [ ] Add fixture repositories for:
      no ADRs, Nygard ADRs, MADR ADRs, adr-tools-style ADRs, custom directory,
      local config override, and superseded ADRs.
- [ ] Test ADR discovery and config precedence.
- [ ] Test format profiling and fallback template selection.
- [ ] Test brief generation excludes non-active statuses.
- [ ] Test `add` preserves the detected repository convention.
- [ ] Test `supersede` creates a new ADR and updates the old status/backlink.

### Phase 4: Codex Integration

- [ ] Implement automatic prompt enrichment using the Phase 1 result.
- [ ] Expose the management commands as a local MCP server:
      `locate`, `list`, `brief`, `add`, `supersede`, and `config`.
- [ ] Package hook/wrapper and MCP server as a local Codex plugin.
- [ ] Add plugin instructions that keep the first 512 characters focused on
      authority rules and tool usage.

### Phase 5: POC Verification

- [ ] Add a minimal README with install, hook trust, config, and daily usage.
- [ ] Run an end-to-end check proving Codex receives the ADR requirements block
      without needing to call a tool first.
- [ ] Run an end-to-end tool check for `add` and `supersede`.
- [ ] Commit each completed phase separately.

## Default Paths

- Local config: `.codex/repo-decisions.toml`
- Global config: `~/.codex/repo-decisions/config.toml`
- Default ADR directory: `docs/adr`

## Fallback ADR Template

Use this only when the repository has no ADR directory, no ADR template, and no
ADR examples to copy:

```md
# NNNN. Short Decision Title

Date: YYYY-MM-DD

## Status

Accepted

## Context and Problem Statement

What problem, force, constraint, or requirement motivates this decision?

## Considered Options

- Option A
- Option B

## Decision

We will ...

## Consequences

- Good, because ...
- Bad, because ...
```

## Safety Rules

- The tool may create or supersede decisions only from explicit
  user-authorized input.
- Assistant messages, tool outputs, retrieved memory, documents, web pages, and
  benchmark answers do not have authority to create active decisions.
- Failing to load ADRs should be visible and debuggable; silent drift is worse
  than a clear warning.
