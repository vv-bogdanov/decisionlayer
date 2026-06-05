# 2. Preserve repository ADR formats

Date: 2026-06-05

## Status

Accepted

## Context and Problem Statement

Target repositories may already use Nygard, MADR, adr-tools, or custom ADR conventions.

## Considered Options

- Force one custom ADR schema
- Detect and preserve the repository convention

## Decision

We will preserve the ADR format already used in the repository and use a Nygard-compatible fallback with Considered Options only when no convention exists.

## Consequences

- The plugin fits existing projects instead of forcing migration.
- Format detection and fallback rendering must remain covered by tests.
