# MemoryCore Architecture

## Position

MemoryCore is not another memory database. MemoryCore is a deterministic
coordination layer above memory systems.

The core owns memory semantics:

- what an atomic fact is;
- what a committed decision is;
- how decisions supersede older decisions;
- how evidence refs connect memories to source events;
- how a recall brief is assembled under a token budget;
- how conflicts, uncertainty, and unsupported answers are represented.

The core must not compete with storage, retrieval, vector search, full-text
search, or LLM vendors. Those capabilities belong behind plugins.

## Architectural Constraints

- The core is pure, deterministic, and side-effect free.
- The core does not read files, write files, call networks, call LLMs, or own a
  database connection.
- Extraction, persistence, indexing, retrieval engines, LLM calls, prompt
  enrichment adapters, source integrations, and judge/evaluation systems are
  plugins.
- Proof must use established external benchmarks. Local synthetic tasks are
  allowed only for development and regression tests.
- Decisions are first-class memory objects, not just facts with a tag.
- Facts are atomic, short, source-backed observations.
- Raw source events are immutable evidence, not the working memory itself.

## Core Contract

The pure core should be expressible as functions over explicit inputs:

```text
MemoryState + MemoryEvent + PolicyConfig -> MemoryDelta
MemoryState + RecallQuery + PolicyConfig -> RecallBrief
MemoryState + ValidationQuery -> ValidationResult
MemoryState + ConflictInput -> ConflictReport
```

The core can define types, invariants, scoring contracts, merge rules, decision
supersession, token budgeting, and trace formats. It cannot decide how storage,
embedding, full-text indexing, or model inference are implemented.

## Plugin Boundary

Plugins are replaceable organs around the core:

- `SourcePlugin`: reads conversation, files, terminal output, GitHub, browser,
  IDE, tickets, docs, or other external content.
- `ExtractorPlugin`: turns source content into candidate facts, decisions,
  task-state updates, and refs.
- `StorePlugin`: persists raw events, facts, decisions, task state, indexes, and
  traces.
- `IndexPlugin`: provides full-text, vector, graph, temporal, or hybrid search.
- `RecallPlugin`: proposes relevant memories for a query or task step.
- `ComposerPlugin`: turns a recall brief and task instruction into prompt
  enrichment or an answer draft.
- `MemoryToolPlugin`: exposes intentional memory operations to an agent through
  a controlled tool/proxy API.
- `JudgePlugin`: evaluates predictions when deterministic scoring is
  insufficient.

Plugins can use SQLite, Postgres, pgvector, Qdrant, LanceDB, Tantivy, llama.cpp,
OpenAI APIs, local files, or managed services. The core should only see their
typed outputs.

## Workflow

### 1. Observe

Source plugins collect raw content:

- chat turns;
- files and diffs;
- terminal output;
- issue or PR comments;
- docs;
- benchmark context.

These are stored as immutable raw events with source metadata.

### 2. Extract

Extractor plugins convert raw events into memory candidates:

- atomic facts;
- proposed decisions;
- explicit committed decisions;
- task-state updates;
- conflicts or uncertainty markers;
- evidence refs.

The core validates candidates before they become working memory. Decisions need
an explicit commit signal or an approved agent tool call.

### 3. Store And Index

Store and index plugins persist the accepted memory state and build retrieval
indexes. MemoryCore should support multiple storage backends rather than owning
one canonical database implementation.

### 4. Recall

For every task step, recall plugins retrieve candidate memories. The core
assembles a bounded recall brief:

- current committed decisions for the active scope;
- relevant atomic facts;
- task-state summary;
- conflict notes;
- source refs when needed;
- a small recent-context fallback for unprocessed content.

The result is prompt enrichment, not a replacement for the base task prompt.

### 5. Act Intentionally

Agents get explicit memory tools through a proxy:

- remember a fact;
- propose a decision;
- commit a decision;
- supersede a decision;
- forget or archive stale memory;
- request evidence for a memory;
- mark a memory as wrong or disputed.

This keeps accidental transcript summarization separate from intentional memory
work.

### 6. Audit

Every memory item and recall brief must be traceable back to raw evidence. This
is required for benchmark proof, debugging, and safe long-horizon operation.

## Proof Strategy

The proof target is external long-horizon benchmarks, not a benchmark designed
for this project.

The claim is supported only if MemoryCore improves the quality/cost/reliability
trade-off on known benchmarks by coordinating decisions, facts, refs, and
bounded recall over longer tasks. If a benchmark only tests plain retrieval or
classification, MemoryCore may match retrieval baselines rather than beat them;
that result should be reported honestly.

## Near-Term Implications

- Keep `memorycore.core` deterministic and move side effects toward plugin
  interfaces.
- Treat current rule-based extraction as one plugin, not as the architecture.
- Avoid benchmark-specific hacks; fix generic memory invariants instead.
- Add prepared memory/index caching because atomic facts are correct but more
  expensive than storing oversized document facts.
- Use existing retrieval and storage systems where possible.
