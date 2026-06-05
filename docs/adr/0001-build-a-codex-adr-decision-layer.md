# 1. Build a Codex ADR decision layer

Date: 2026-06-05

## Status

Accepted

## Context and Problem Statement

The project goal is to keep durable repository decisions visible to coding agents without building a general-purpose memory database.

## Considered Options

- Build a broad memory system
- Build a repository ADR decision layer

## Decision

We will build a Codex plugin that treats accepted repository ADRs as binding decision context and exposes tools to inspect, add, and supersede decisions.

## Consequences

- The POC stays narrow and can prove whether decision retention improves long-horizon coding work.
- General memory extraction, vector search, and benchmark-specific memory systems stay outside this repository for now.
