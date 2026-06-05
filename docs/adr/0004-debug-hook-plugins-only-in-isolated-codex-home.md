# 4. Debug hook plugins only in isolated Codex home

Date: 2026-06-05

## Status

Accepted

## Context and Problem Statement

Codex hook sessions can retain versioned plugin cache paths; reinstalling a hook plugin in the main Codex home during an active session can leave stale hook commands that block prompts before our code can fail open.

## Considered Options

- Debug directly in the main ~/.codex
- Use an isolated lab CODEX_HOME

## Decision

Hook and MCP plugin changes must be tested under .codex-lab/home before touching the main ~/.codex; the main repo-decisions plugin stays disabled until lab runtime verification passes.

## Consequences

- Development cannot break the main Codex environment.
- Lab checks must cover MCP listing and installed hook smoke tests.
