# 3. Change accepted ADRs only by superseding

Date: 2026-06-05

## Status

Accepted

## Context and Problem Statement

Accepted decisions are durable requirements and direct edits make history ambiguous for agents and humans.

## Considered Options

- Allow direct edits to accepted ADRs
- Create replacement ADRs and mark old ones superseded

## Decision

Accepted ADRs are immutable through the tool; changes must create a new accepted ADR with supersede links and mark the old ADR superseded.

## Consequences

- Decision history remains auditable.
- The tool must reject superseding non-accepted ADRs.
