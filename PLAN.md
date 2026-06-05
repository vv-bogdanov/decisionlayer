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
- Target automatic enrichment is the plugin-bundled `UserPromptSubmit` hook
  returning Codex `additionalContext`.
- The `repo-decisions codex` wrapper remains a fallback for cases where hooks
  are disabled, not trusted, unavailable, or not yet runtime-verified.
- Hook and MCP plugin changes must be tested in an isolated lab `CODEX_HOME`
  before touching the main `~/.codex`.
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
- [x] Test Codex hook prompt-enrichment feasibility and record initial results
      in `research/codex-hooks/README.md`.
- [x] Inspect Codex CLI source and confirm `UserPromptSubmit` can inject
      model-visible `additionalContext`.

## Active Plan

### Phase 1: ADR Core CLI

- [x] Implement `repo-decisions locate`.
- [x] Implement fast ADR directory discovery:
      local config, global config, existing ADR templates/examples, common ADR
      directories, then default `docs/adr`.
- [x] Implement ADR format profiling from existing files:
      filename numbering, date/status placement, heading names, section order,
      and template file detection.
- [x] Implement `repo-decisions list`.
- [x] Implement `repo-decisions brief` that emits a compact requirements block
      from active accepted ADRs only.
- [x] Implement `repo-decisions add` using the repository's current template or
      nearest recent ADR as the structural example.
- [x] Implement `repo-decisions supersede`:
      create a replacement ADR, mark the old ADR as superseded, and backlink
      both records.
- [x] Implement `repo-decisions config` for local/global defaults and prompt
      size limits.

### Phase 2: Tests

- [x] Add fixture repositories for:
      no ADRs, Nygard ADRs, MADR ADRs, adr-tools-style ADRs, custom directory,
      local config override, and superseded ADRs.
- [x] Test ADR discovery and config precedence.
- [x] Test format profiling and fallback template selection.
- [x] Test brief generation excludes non-active statuses.
- [x] Test `add` preserves the detected repository convention.
- [x] Test `supersede` creates a new ADR and updates the old status/backlink.

### Phase 3: Codex Integration

- [x] Implement automatic prompt enrichment through a plugin-bundled
      `UserPromptSubmit` hook that returns the accepted ADR brief as
      `additionalContext`.
- [x] Keep `repo-decisions codex ...` as a wrapper fallback that prepends
      `repo-decisions brief` to the user prompt before invoking Codex.
- [x] Expose the management commands as a local MCP server:
      `locate`, `list`, `brief`, `add`, `supersede`, and `config`.
- [x] Package wrapper and MCP server as a local Codex plugin.
- [x] Package the hook in `plugins/repo-decisions/hooks/hooks.json`.
- [x] Add plugin instructions that keep the first 512 characters focused on
      authority rules and tool usage.

### Phase 4: POC Verification

- [x] Add a minimal README with install, hook trust, config, and daily usage.
- [x] Add a direct hook test proving the ADR requirements block is emitted as
      Codex hook `additionalContext` without needing a tool call first.
- [x] Add an isolated Codex plugin lab workflow that installs and debugs the
      plugin under `.codex-lab/home` instead of the main `~/.codex`.
- [x] Make the plugin bundle self-contained so installed cache copies can run
      the hook and CLI without importing from the source checkout.
- [x] Run `codex exec` smoke attempts with inline and project-local hooks;
      record that this local non-interactive path did not execute the hook.
- [x] Run an end-to-end tool check for `add` and `supersede`.
- [x] Commit each completed phase separately.

### Phase 5: Runtime Hook Verification

- [x] Add `scripts/codex-plugin-lab doctor` to install the plugin in an
      isolated `CODEX_HOME`, list MCP servers, and smoke-test the installed
      `UserPromptSubmit` hook.
- [ ] Open a separate lab Codex session with
      `scripts/codex-plugin-lab interactive`, verify the bundled
      `UserPromptSubmit` hook is discovered, trust/bypass only inside the lab,
      and confirm its command hash is stable.
- [ ] Run one lab interactive CLI task with an accepted ADR marker and
      `.codex-lab/repo-decisions-debug.jsonl`; verify a `hook-context` event is
      written.
- [ ] Use app-server `hooks/list` as a non-interactive discovery check if CLI
      `/hooks` is hard to automate.
- [ ] Only after this passes, treat hook enrichment as the default runtime path
      for benchmarks; otherwise keep using the wrapper for non-interactive runs.

## Next Plan: ADR-Agent Integration Test Harness

This is not a replacement for an external benchmark. It is a small regression
and prompt-selection harness that checks whether coding agents actually respect
repository ADRs during realistic tasks.

### Test Repositories

- [ ] Create two small local fixture projects under
      `benchmarks/adr-agent/fixtures` with exact deterministic oracle checks.
- [ ] Clone a small set of public ADR-bearing repositories into a temporary
      workspace, pinned by commit SHA.
- [ ] Start with these candidates:
      `asyncapi/studio`, `adr/e-adr`, `thomvaill/log4brains`, and optionally
      `sbomify/sbomify` as a heavier later-stage case.
- [ ] Record each repo's ADR directory, ADR format, install/test commands, and
      known constraints in `benchmarks/adr-agent/repos.yaml`.

### Modes To Compare

- [ ] `D0`: baseline Codex without repo-decisions enrichment.
- [ ] `D1`: automatic accepted-ADR brief from the repo-decisions hook or wrapper
      fallback.
- [ ] `D2`: automatic enrichment plus repo-decisions MCP tools available.
- [ ] Prompt variants:
      strict bullet brief, compact Y-statement brief, and fuller ADR excerpt
      brief.

### Canary Task Types

- [ ] Format preservation:
      ask the agent to add an ADR and verify it uses the existing repo
      directory, numbering, status style, headings, and template.
- [ ] Supersede behavior:
      ask the agent to change an accepted ADR and verify it creates a new ADR,
      marks the old ADR superseded, and keeps only the new ADR active.
- [ ] Code follows ADR:
      create a task where the easiest implementation violates an accepted ADR,
      and verify the diff follows the ADR instead.
- [ ] Conflict detection:
      ask for a change that contradicts an accepted ADR and verify the agent
      asks for explicit supersede/confirmation instead of silently violating it.
- [ ] No false decision creation:
      include non-authoritative text that looks decision-like and verify no
      accepted ADR is created without explicit user authorization.

### Harness Shape

- [ ] Add `benchmarks/adr-agent/cases.yaml` with repo, pinned ref, task, mode,
      expected checks, and allowed commands.
- [ ] Add `benchmarks/adr-agent/run_case.py` to clone/copy repos into a temp
      workspace, run one mode, capture prompt/brief/final answer/diff, and
      write results under `benchmarks/adr-agent/runs/`.
- [ ] Add `benchmarks/adr-agent/checks.py` with deterministic checks:
      changed paths, ADR status, backlinks, active brief include/exclude,
      forbidden files, required grep patterns, and optional project tests.
- [ ] Enable `REPO_DECISIONS_DEBUG_LOG` for each agent run and fail if ADR files
      changed without matching `repo-decisions` `mcp-tool-call` and `write`
      events.
- [ ] Keep LLM judging out of the first version; use it only later for
      secondary qualitative review.

### Metrics

- [ ] `task_success`: the requested coding/documentation task is completed.
- [ ] `adr_compliance`: no active ADR is violated by the diff.
- [ ] `format_preservation`: new ADRs match the repository convention.
- [ ] `unwanted_adr_mutation`: accepted ADRs are not directly edited except
      for supersede status/backlink.
- [ ] `conflict_handling`: contradictory requests trigger confirmation or
      supersede flow.
- [ ] `tokens`, `duration`, `diff_size`, and `tool_calls`.

### Initial Run

- [ ] Run fixture canaries first for `D0`, `D1`, and `D2`.
- [ ] Run one real repo canary on `asyncapi/studio`.
- [ ] Compare prompt variants on the same pinned case before expanding the
      suite.
- [ ] Save a short analysis report with examples of where ADR enrichment helped,
      failed, or made no difference.

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
