# Decision Layer Development Plan

## Goal

Build a minimal POC that tests one claim:

```text
same benchmark backend + Decision Layer
performs better than
the same benchmark backend without Decision Layer.
```

The first proof target is LongMemEval-V2. Do not create a custom benchmark for
the proof. Local synthetic cases are allowed only for unit tests and regression
tests.

## Product Position

Decision Layer is not a memory system.

Decision Layer is a commitment layer above existing memory systems:

```text
Memory remembers facts.
Decision Layer remembers commitments.
```

The project should not compete with RAG, vector databases, graph memory,
episodic memory, or long-term memory backends. Those systems can be plugged in
later. The first POC only needs to prove that adding a compact list of current
accepted decisions can improve long-horizon task performance.

## Architecture Constraints

- [x] Core logic is deterministic and side-effect free.
- [x] Core owns only decision semantics and Decision Brief construction.
- [x] Extraction is a plugin boundary.
- [x] Storage is a plugin boundary.
- [x] Retrieval / memory backend is a plugin boundary.
- [x] LLM calls are outside the pure core.
- [x] Benchmarks and judges are outside the pure core.
- [x] No custom proof benchmark.
- [x] No production API, UI, database, vector store, or SDK in the first POC.

## Minimal Core

The first core model is intentionally small:

```text
Decision:
  id
  text
  meta?
```

Core operations:

- [x] `decision.add`
- [x] `decision.replace`
- [x] `decision.remove`
- [x] `decision.list`
- [x] `decision.brief`

Core invariants:

- [x] A decision is a short accepted statement.
- [x] A decision must be understandable without metadata.
- [x] Active context contains only current decisions.
- [x] Replaced or removed decisions are not included in the active brief.
- [x] History can be logged for traceability, but history is not active
  context.

## Authority Rules

Only user-authorized input can create, replace, or remove decisions.

Allowed authority sources:

- [x] Explicit user commit signal.
- [x] User confirmation of an agent proposal.
- [x] Manual API/tool call made by the user or trusted application layer.

Disallowed authority sources:

- [x] Assistant messages without user confirmation.
- [x] Tool outputs.
- [x] Retrieved memory.
- [x] Documents.
- [x] Web pages.
- [x] Benchmark answers.
- [x] External sources.

Safety rule:

```text
It is better to miss a decision than to create a false decision.
```

## POC Modes

Run the same benchmark subset in three modes:

- [ ] `D0`: baseline backend without Decision Layer.
- [ ] `D1`: baseline backend + oracle/manual Decision Layer.
- [ ] `D2`: baseline backend + automatic Decision Layer.
- [x] Fixture smoke suite can run `D0`, `D1`, and `D2` with one command and
  write comparison artifacts.

Interpretation:

- [ ] `D1` measures the upper bound: does a good Decision Brief help at all?
- [ ] `D2` measures the practical system: can automatic extraction recover
  enough useful decisions without adding false commitments?
- [ ] If `D1` does not help, do not overbuild extraction. Analyze whether
  LongMemEval-V2 is the wrong proof surface for this hypothesis.

## Workflow

### 1. Benchmark Setup

- [x] Locate the official LongMemEval-V2 repository, dataset, and runner.
- [x] Confirm license and dataset accessibility.
- [x] Download or prepare the dataset outside the runner.
- [x] Inspect schema and task categories.
- [ ] Select a small reproducible subset.
- [x] Save dataset path, row count, subset IDs, and hash in a manifest.

### 2. Baseline Run: D0

- [x] Implement the simplest compatible benchmark adapter.
- [ ] Run baseline on the selected subset.
- [x] Save predictions, metrics, trace logs, and report.
- [x] Record prompt tokens, latency, and score.

### 3. Oracle Decision Layer: D1

- [ ] Create a manual/oracle decision file for the same subset.
- [ ] Build `Decision Brief` from oracle decisions.
- [ ] Run the same backend with the same subset and same scoring.
- [ ] Compare `D1` against `D0`.
- [ ] Inspect targeted categories: updates, conflicts, instruction following,
  goal adherence, workflow state, and long-horizon consistency.

### 4. Automatic Decision Extraction: D2

- [x] Implement conservative trigger detection for user messages.
- [ ] Add structured extraction only for candidate messages.
- [x] Ignore assistant messages, tool outputs, retrieved memory, and external
  content.
- [x] Add no decision when the extractor is uncertain.
- [ ] Run `D2` on the same subset.
- [ ] Compare `D2` against `D0` and `D1`.

### 5. Decision Brief

- [x] Define the minimal brief format.
- [x] Include relevant current decisions.
- [x] Include an instruction to treat decisions as current commitments.
- [x] Include an instruction to ask for clarification if decisions conflict or
  look outdated.
- [x] Enforce a token budget.
- [x] Log the exact brief used for each example.

### 6. Traceability

- [ ] Log processed messages.
- [ ] Log decision candidates.
- [ ] Log added, replaced, and removed decisions.
- [ ] Log skipped candidates and reasons when possible.
- [ ] Log the final decision list before each answer.
- [ ] Log the exact Decision Brief injected into the prompt.
- [ ] Link each decision to source message metadata.

### 7. Tests

- [x] Add unit tests for add, replace, remove, and list.
- [x] Add unit tests for Decision Brief rendering.
- [x] Add unit tests for strong commit signals.
- [x] Add unit tests for weak non-commit signals.
- [x] Add unit tests that assistant/tool/retrieved content cannot create
  decisions.
- [x] Add a smoke test for D0/D1/D2 on a tiny fixture.

Golden cases:

- [x] `"Maybe SQLite"` -> no decision.
- [x] `"SQLite looks interesting"` -> no decision.
- [x] `"Let's commit: use SQLite for the MVP"` -> add decision.
- [x] `"Change the decision: use PostgreSQL for the MVP"` -> replace decision.
- [x] `"Goal: test Decision Layer on the benchmark"` -> add decision.

## Metrics

Benchmark metrics:

- [ ] Accuracy / QA score.
- [ ] Evidence quality if available.
- [x] Prompt tokens.
- [x] Latency.
- [ ] Cost estimate if model pricing is known.

Decision Layer metrics:

- [ ] Number of extracted decisions.
- [ ] Number of non-empty Decision Briefs.
- [ ] Decision Brief token overhead.
- [ ] False decision rate.
- [ ] Decision update correctness.
- [ ] Decision persistence across examples or turns.
- [ ] Category-level effect on updates, conflicts, instruction following, goal
  adherence, workflow state, and long-horizon consistency.

## Artifacts

Every run should write:

- [x] `config.json`
- [x] `manifest.json`
- [x] `metrics.json`
- [x] `predictions.jsonl`
- [x] `decision_trace.jsonl`
- [x] `brief_trace.jsonl`
- [x] `report.md`

The final POC report must answer:

- [ ] Which LongMemEval-V2 subset was used?
- [ ] Which backend/model was used?
- [ ] What is the `D0` score?
- [ ] What is the `D1` score?
- [ ] What is the `D2` score?
- [ ] What is the delta?
- [ ] How many decisions were used?
- [ ] How often was Decision Brief non-empty?
- [ ] Did Decision Layer show a measurable signal?
- [ ] If not, do traces suggest the issue is benchmark fit, extractor quality,
  brief construction, or the hypothesis itself?

## Milestones

### M1: Repository Skeleton

- [x] Create Python project skeleton with `uv`.
- [x] Add package structure.
- [x] Add pytest.
- [x] Add linting and formatting.
- [x] Add a minimal CLI entrypoint.

### M2: Pure Decision Core

- [x] Implement Decision model.
- [x] Implement in-memory state object.
- [x] Implement add, replace, remove, list.
- [x] Implement Decision Brief rendering.
- [x] Add unit tests.

### M3: LongMemEval-V2 Adapter

- [x] Locate and document official dataset source.
- [x] Implement adapter for a small subset.
- [ ] Run D0 baseline.
- [ ] Save metrics and report.

### M4: Oracle Decision Layer

- [ ] Create oracle decisions for the subset.
- [ ] Run D1.
- [ ] Compare D1 vs D0.
- [ ] Decide whether the benchmark has enough Decision Layer signal.

### M5: Automatic Decision Layer

- [ ] Implement conservative trigger detector.
- [ ] Implement structured extraction for candidate user messages.
- [ ] Run D2.
- [ ] Compare D2 vs D0 and D1.

### M6: POC Report

- [ ] Aggregate all artifacts.
- [ ] Write final `report.md`.
- [ ] State whether the hypothesis is supported, partially supported, or not
  supported on the selected subset.
- [ ] Recommend the next step based on evidence.

## Definition Of Done

The POC is done when one documented command can:

- [ ] create the environment;
- [ ] run tests;
- [x] run a fixture-level `D0` / `D1` / `D2` smoke suite;
- [ ] run the selected LongMemEval-V2 subset;
- [ ] produce D0 metrics;
- [ ] produce D1 metrics;
- [ ] produce D2 metrics;
- [ ] save trace logs;
- [ ] save a final report.

The decision question is:

```text
Did Decision Layer improve the same backend on a known external benchmark?
```

If the answer is yes, expand benchmark size and test with a stronger backend.

If the answer is no, use traces to decide whether the failure is caused by
benchmark fit, extraction, brief selection, or the Decision Layer hypothesis.
