# 1. Use JSON Lines For Event Log

Date: 2026-06-05

## Status

Accepted

## Context and Problem Statement

The application needs an append-only event log that is easy to inspect and
stream.

## Considered Options

- CSV rows
- JSON array file
- Newline-delimited JSON

## Decision

Application event logs are newline-delimited JSON. Do not use CSV for event
logs.

## Consequences

- Each event can be appended independently.
- Each line must be valid JSON.
