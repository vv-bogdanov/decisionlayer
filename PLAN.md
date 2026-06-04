# Current Plan: SWE-ContextBench Canary Follow-Up

## Goal

Test whether Decision Layer helps a local coding agent work on longer-horizon
coding tasks by reusing compact accepted decisions from prior related work.

This is still a POC. Do not build a product platform, REST API, UI, vector DB,
custom judge, or custom benchmark unless it is directly needed for the
D0/D1/D2 measurement.

## Selected Test

Next benchmark: **SWE-ContextBench**.

Source:

```text
https://arxiv.org/abs/2602.08316
```

Reason: SWE-ContextBench is a SWE-bench-family external benchmark focused on
whether coding agents reuse prior experience across related tasks. That is a
closer fit to Decision Layer than isolated issue fixing.

Before running, verify the official dataset/harness location, license, schema,
and grading path locally.

## Protocol

For each selected base -> related pair:

- D0: run the related task with the same local agent/model and no prior
  Decision Brief.
- D1: run the related task with a manually reviewed Decision Brief extracted
  only from the base task. This is the upper-bound oracle.
- D2: run the related task with an automatically extracted Decision Brief from
  the same base-task artifacts.

The related task issue text is visible to all modes equally. The Decision Brief
must not be derived from the related task's hidden patch, hidden tests, final
answer, or post-hoc benchmark result.

## Decision Scope

Allowed Decision Brief content:

- accepted requirements and constraints
- implementation commitments
- stable conclusions from observed failed attempts
- project-specific procedures learned in the base task

Not allowed:

- raw history
- full patches
- full test logs
- arbitrary facts
- retrieved file contents
- related-task answer information

## Metrics

Record per mode and per pair:

- official resolved/unresolved
- wall-clock time
- tool-call count
- prompt/completion tokens, if available from agent logs
- generated patch size and touched files
- number of accepted decisions
- Decision Brief token size
- false-decision audit result

Primary signal:

- D2 resolves at least one related task that D0 misses, with no audited false
  decisions.

Secondary signal:

- if D0 and D2 resolve the same tasks, D2 reduces average wall time or tool
  calls by at least 20% without adding false decisions.

## Completed Canary Work

- [x] Verify the official SWE-ContextBench dataset/harness location, license,
  schema, and grading path.
- [x] Create an external workspace under
  `/home/dev/benchmarks/swe-contextbench`; keep generated repos, logs, patches,
  and official reports out of this repository.
- [x] Select one base -> related pair for an infrastructure canary and document
  why it has reusable context.
- [x] Run a gold or official-reference grading preflight for that pair.
- [x] Run D0/D1/D2 on the one-pair canary with local OpenCode + llama.cpp and
  strict no-install command rules.
- [x] Add diagnostic logs/variants for the canary, including alternative local
  agents and a self/gold-informed sanity check.
- [x] Write `reports/swe-contextbench-canary.md` with commands, artifacts,
  Decision Briefs, patches, grading, and caveats.

Canary result: stop rule triggered. D1 had no signal on
`sympy__sympy-24661 -> sympy__sympy-20571`, because the manual brief led agents
to a parser-only fix while the resolving patch also required `sign.doit()`.

- [x] Select and run a replacement canary:
  `pydata__xarray-4687 -> pydata__xarray-4141`.
- [x] Add structured event logging for agent runs:
  `opencode run --format json`, wall-clock timing, diff snapshots, guard-bin
  command blocking, and official grading logs per variant.
- [x] Run D0/D1/D2 on the replacement canary.
- [x] Run a post-hoc operational-decision diagnostic on the replacement canary.
- [x] Decide diagnostic-observation authority rule: observations can become
  Decision Brief content only when authorized by the base task accepted
  solution, explicit user instruction, or trusted manual API/tool call.
  Related-task post-hoc failures are allowed for analysis, not for proof.
- [x] Write `reports/swe-contextbench-xarray-canary.md`.

Replacement canary result: standard D1/D2 had no clean signal, but a post-hoc
operational-decision diagnostic resolved `pydata__xarray-4141`. The useful
lesson is that high-level requirements are too lossy for coding tasks; briefs
must preserve compact implementation decisions.

- [x] Define `Operational Decision Brief v0`: compact bullets that preserve
  implementation-critical operator choices, argument mapping, invariants, and
  authorized failure-derived constraints without storing raw history or full
  patches.
- [x] Update the D2 extractor prompt/schema so it keeps implementation-critical
  details instead of summarizing them away.
- [x] Select a fresh SWE-ContextBench pair:
  `sphinx-doc__sphinx-8265 -> sphinx-doc__sphinx-8052`.
- [x] Write the D1 manual operational brief from base-task artifacts only.
- [x] Generate the D2 automatic operational brief from the same base-task
  artifacts and audit it for false decisions.
- [x] Run a clean one-pair D0/D1/D2 canary with structured logs, guard-bin,
  official grading, and resume/cache artifacts.
- [x] Add the proof-run hygiene rule: coding proof workspaces must be sanitized
  single-commit repos so agents cannot use future git history.
- [x] Write `reports/swe-contextbench-sphinx-canary.md`.
- [x] Add a lightweight patch/brief verifier for canaries:
  `decision-layer verify-patch` checks required patch terms, required touched
  files, and unexpected files before expensive official grading.

Sphinx canary result: no clean Decision Layer signal. D0, D1, and D2 all
resolved `sphinx-doc__sphinx-8052`, but all non-gold variants regressed the same
PASS_TO_PASS test. D1 contained the right subscript-preservation decision, but
the agent ignored it; D2 attempted it but produced an over-broad patch. The
important protocol lesson is to sanitize repository history and keep structured
logs, timing, diffs, guard audits, and official grading reports for each run.

## Active Checklist

- [ ] Do not start the 5-pair mini-slice until a fresh canary shows clean D1 or
  D2 signal under the revised operational-brief policy.
- [ ] Select one more fresh SWE-ContextBench base -> related pair only after the
  verifier/logging protocol is ready.
- [ ] Run another clean one-pair D0/D1/D2 canary in sanitized single-commit
  workspaces with structured JSONL logs, stderr, wall-clock timing, diff
  snapshots, guard audits, and official grading.
- [ ] If a clean canary shows signal and D2 has no false decisions, select a
  5-pair mini-slice and save only the small selection metadata in this
  repository.
- [ ] Run the 5-pair D0/D1/D2 mini-slice with resume/cache so completed pairs
  are not rerun after failures.
- [ ] Write `reports/swe-contextbench-mini.md` with the result table, analysis,
  failure cases, and next recommendation.

## Stop Rules

- Stop if the official dataset or grading path is not locally reproducible.
- Stop if the benchmark requires building a custom judge.
- Stop if D1 has no signal; that means the selected slice does not fit the
  Decision Layer hypothesis.
- Stop if D2 introduces false decisions; fix authority/extraction before
  running more tasks.

## Archived Context

Completed and historical work is recorded outside this active plan:

- `reports/current-poc-result.md`
- `reports/swebench-canary.md`
- `reports/swebench-d0-d2-canary.md`
- `reports/swe-contextbench-canary.md`
- `reports/swe-contextbench-xarray-canary.md`
- `docs/research-report.md`
- `docs/coding-benchmark-selection.md`
