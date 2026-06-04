# Decision Layer Design

## Scope

Decision Layer is a small side-effect-free core plus pluggable extraction and
benchmark adapters. It is not a general memory system.

The core stores accepted decisions:

- goals
- commitments
- constraints
- procedures
- stable operating rules

The core does not store:

- raw chat history
- documents
- retrieved snippets
- observations
- UI state
- embeddings
- vector database rows
- benchmark answers
- tool outputs

Those are external systems or plugins.

## Core Rules

The core should remain deterministic and side-effect free. Given the same state
and command, it should produce the same new state and trace.

Decision authority is narrow:

- explicit user commit
- user-confirmed agent proposal
- trusted manual API/tool call

These sources do not have authority to change active decisions by themselves:

- assistant messages
- retrieved memory
- tool outputs
- documents
- webpages
- benchmark answers

Safety rule:

```text
Better skip a decision than create a false decision.
```

## D0, D1, D2

D0:

- no Decision Layer
- baseline context only

D1:

- oracle decisions injected from a trusted config
- used as an upper-bound/reference condition

D2:

- decisions extracted automatically from authorized sources
- used as the real POC condition

## Decision Brief

The Decision Brief is a compact prompt prefix containing active decisions. It is
only included when decisions exist.

The brief should be short, stable, and actionable. It should not contain raw
evidence, long observations, or answer-like facts.

## Plugin Boundary

Allowed plugin responsibilities:

- extraction
- storage
- retrieval
- benchmark runners
- judges
- tracing
- memory backends

Core responsibilities:

- represent decisions
- add/replace/remove/list decisions
- render a Decision Brief
- emit deterministic traces

## Why Facts Are Not Decisions

A fact can be true but still not be a commitment. Example:

```text
The incident page has a Short description field.
```

That belongs to memory or retrieval.

A decision tells the agent what accepted path or constraint to follow. Example:

```text
For problem requests created from incident-report results, use Impact, Urgency,
Problem statement, and Assigned to; Subcategory, Assignment Group, and State are
present but unused.
```

That belongs in Decision Layer because it constrains future behavior.

## Current POC Boundary

The current POC intentionally excludes:

- REST API
- UI
- production storage
- SDK
- vector DB
- graph memory
- reranker
- custom benchmark

This keeps the proof focused on whether compact accepted decisions improve an
external benchmark under the same backend/model.
