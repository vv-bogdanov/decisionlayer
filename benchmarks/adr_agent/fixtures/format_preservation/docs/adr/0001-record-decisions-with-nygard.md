# 1. Record Decisions With Nygard ADRs

Date: 2026-06-05

## Status

Accepted

## Context and Problem Statement

The project needs lightweight architecture decision records.

## Considered Options

- Nygard ADRs
- Custom JSON decision files

## Decision

Use Nygard-style Markdown ADRs in `docs/adr`.

## Consequences

- Decisions are readable in plain Git history.
- Agents must preserve this format when adding ADRs.
