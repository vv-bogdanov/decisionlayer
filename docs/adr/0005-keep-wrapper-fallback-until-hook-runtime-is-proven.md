# 5. Keep wrapper fallback until hook runtime is proven

Date: 2026-06-05

## Status

Accepted

## Context and Problem Statement

Codex source confirms UserPromptSubmit additionalContext, but local non-interactive codex exec smoke tests did not execute project-local hooks.

## Considered Options

- Depend only on automatic hook enrichment
- Keep a deterministic wrapper fallback

## Decision

The repo-decisions codex wrapper remains supported until an isolated interactive Codex session proves the plugin-bundled UserPromptSubmit hook writes hook-context events.

## Consequences

- Benchmarks can use deterministic prompt enrichment before hook runtime is fully trusted.
- Automatic hook enrichment becomes default only after lab evidence is recorded.
