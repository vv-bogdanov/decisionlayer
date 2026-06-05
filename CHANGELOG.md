# Changelog

## 0.1.0 - Unreleased

- Add the `repo-decisions` CLI for locating, listing, briefing, adding, and
  superseding repository ADRs.
- Add a Codex plugin bundle with a `UserPromptSubmit` hook and
  `repo-adr-decisions` MCP server.
- Preserve existing ADR formats and use a Nygard-compatible fallback when a
  repository has no convention.
- Add debug JSONL evidence for hook/tool/write events.
- Add isolated Codex plugin lab checks under `.codex-lab/home`.
- Add deterministic ADR-agent fixture canaries for format preservation,
  supersede behavior, ADR compliance, conflict detection, and false decision
  prevention.
