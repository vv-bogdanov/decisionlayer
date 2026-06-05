# 1. Use SQLite

Date: 2026-06-05

## Status

Accepted

## Context and Problem Statement

The service needs a local persistence store for the first release.

## Considered Options

- SQLite
- PostgreSQL

## Decision

Use SQLite for persistence in the first release.

## Consequences

- No external database service is required.
- Switching to PostgreSQL requires superseding this ADR.
