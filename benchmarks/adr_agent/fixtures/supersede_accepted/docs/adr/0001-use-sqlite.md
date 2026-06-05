# 1. Use SQLite

Date: 2026-06-05

## Status

Accepted

## Context and Problem Statement

The project needs a simple durable persistence store.

## Considered Options

- SQLite
- PostgreSQL

## Decision

Use SQLite as the primary persistence store.

## Consequences

- Local development has no external database dependency.
- Concurrent writers are limited.
