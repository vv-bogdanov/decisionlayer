# Codex ADR Decision Plugin POC Plan

## Goal

Build a minimal Codex CLI plugin that keeps repository architectural decisions
visible to the agent automatically, while exposing explicit tools to add and
manage those decisions.

The plugin is a Decision Layer, not a general memory system. It stores only
accepted goals, commitments, and constraints from ADR files. Prompt enrichment
must happen automatically so the agent does not need to remember to call a tool.

## Non-Goals

- No custom benchmark.
- No vector database, RAG, graph memory, or reranker.
- No REST API, UI, production storage, or SDK.
- No hidden decision creation from assistant messages, tool output, retrieved
  documents, or benchmark answers.

## Checklist

- [ ] Verify whether `UserPromptSubmit` command hooks can mutate the
      model-visible prompt by using `codex debug prompt-input`.
- [ ] If hook prompt mutation works, implement ADR prompt enrichment through a
      Codex hook.
- [ ] If hook prompt mutation does not work, implement a minimal Codex wrapper
      fallback and keep hooks for refresh/logging.
- [ ] Implement fast ADR location discovery:
      local config, global config, common ADR directories, then default path.
- [ ] Support a small ADR file format compatible with common ADR conventions:
      status, context, decision, consequences, tags, and supersession.
- [ ] Implement a compact decision brief builder that includes only active
      accepted decisions.
- [ ] Implement management commands/tools:
      locate, list, brief, add, edit, and supersede.
- [ ] Expose the management surface as a local MCP server for Codex.
- [ ] Package the hook and MCP server as a local Codex plugin.
- [ ] Add fixture tests for ADR discovery, config precedence, brief generation,
      add, edit, and supersede.
- [ ] Add a short README with installation, trust, and daily usage flow.
- [ ] Run an end-to-end check that proves new Codex prompts include the compact
      ADR requirements block.

## Default Paths

- Local config: `.codex/repo-decisions.toml`
- Global config: `~/.codex/repo-decisions/config.toml`
- Default ADR directory: `docs/adr`
- Optional generated brief cache: `.codex/decision-brief.md`

## Practical Constraints

- Source of truth is plain markdown ADR files in the repository.
- Active prompt context must stay compact and deterministic.
- The tool may create or update decisions only from explicit user-authorized
  input.
- Failing to load ADRs should be visible and debuggable; silent drift is worse
  than a clear warning.
