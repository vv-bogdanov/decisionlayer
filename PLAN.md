# Codex ADR Decision Plugin POC Plan

## Goal

Build a minimal Codex CLI plugin that keeps repository architectural decisions
visible to the agent automatically, while exposing explicit tools to add and
supersede those decisions.

The plugin is a Decision Layer, not a general memory system. It stores only
accepted goals, commitments, and constraints from ADR files. Prompt enrichment
must happen automatically so the agent does not need to remember to call a tool.

## Non-Goals

- No custom benchmark.
- No vector database, RAG, graph memory, or reranker.
- No REST API, UI, production storage, or SDK.
- No custom ADR schema imposed on existing repositories.
- No content editing of accepted ADRs; accepted decisions change only by
  superseding them with a new ADR.
- No hidden decision creation from assistant messages, tool output, retrieved
  documents, or benchmark answers.

## Checklist

- [ ] Verify whether `UserPromptSubmit` command hooks can mutate the
      model-visible prompt by using `codex debug prompt-input`.
- [ ] If hook prompt mutation works, implement ADR prompt enrichment through a
      Codex hook.
- [ ] If hook prompt mutation does not work, implement a minimal Codex wrapper
      fallback and keep hooks for refresh/logging.
- [ ] Implement fast ADR location and format discovery:
      local config, global config, existing templates/examples, common ADR
      directories, then default path.
- [ ] Support existing repository ADR formats by profiling current ADR files:
      filename numbering, date/status style, heading names, and section order.
- [ ] Use the repository's existing ADR template or nearest recent ADR as the
      structural example when adding a new ADR.
- [ ] Use a fallback template only when no existing ADR format is found.
- [ ] Implement a compact decision brief builder that includes only active
      accepted decisions.
- [ ] Implement management commands/tools:
      locate, list, brief, add, supersede, and config.
- [ ] Make `supersede` the only tool path that changes an accepted ADR:
      create a new ADR and mark the old ADR as superseded with a backlink.
- [ ] Expose the management surface as a local MCP server for Codex.
- [ ] Package the hook and MCP server as a local Codex plugin.
- [ ] Add fixture tests for ADR discovery, format profiling, config precedence,
      brief generation, add, and supersede.
- [ ] Add a short README with installation, trust, and daily usage flow.
- [ ] Run an end-to-end check that proves new Codex prompts include the compact
      ADR requirements block.

## Default Paths

- Local config: `.codex/repo-decisions.toml`
- Global config: `~/.codex/repo-decisions/config.toml`
- Default ADR directory: `docs/adr`

## Fallback ADR Template

Use this only when the repository has no ADR directory, no ADR template, and no
ADR examples to copy:

- Title
- Date
- Status
- Context and Problem Statement
- Considered Options
- Decision
- Consequences

This is intentionally close to Nygard ADRs, with the useful MADR addition of
considered options.

## Practical Constraints

- Source of truth is plain markdown ADR files in the repository.
- Active prompt context must stay compact and deterministic.
- The tool may create or update decisions only from explicit user-authorized
  input.
- Proposed, rejected, deprecated, and superseded ADRs are not active prompt
  requirements.
- Failing to load ADRs should be visible and debuggable; silent drift is worse
  than a clear warning.
