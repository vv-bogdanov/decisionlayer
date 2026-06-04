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

## Completed Canary

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

## Active Checklist

- [ ] Do not start the 5-pair mini-slice until a replacement canary or revised
  brief policy shows D1 signal.
- [ ] Select a replacement base -> related pair where the base artifact contains
  all decisions needed by the related task, not only a partial parser-side
  decision.
- [ ] Add structured event logging for future agent runs:
  `opencode run --format json`, wall-clock timing, diff snapshots, and official
  grading logs per variant.
- [ ] Decide whether "accepted diagnostic observations" are allowed Decision
  Brief content, and define the authority rule before using them.
- [ ] Rerun a one-pair canary with D0/D1/D2 and the improved logging policy.
- [ ] If D1 shows signal and D2 has no false decisions, select a 5-pair
  mini-slice and save only the small selection metadata in this repository.
- [ ] Prepare D1 manual Decision Briefs from base-task artifacts only; do not
  inspect related-task answers while writing them.
- [ ] Prepare D2 automatic Decision Briefs from the same base-task artifacts.
- [ ] Run the 5-pair D0/D1/D2 mini-slice with resume/cache so completed pairs
  are not rerun after failures.
- [ ] Audit D1/D2 briefs for false decisions and related-task leakage.
- [ ] Write `reports/swe-contextbench-mini.md` with the result table, analysis,
  failure cases, and next recommendation.
- [ ] Continue to a larger run only if the mini-slice shows primary or secondary
  signal without false decisions.

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
- `docs/research-report.md`
- `docs/coding-benchmark-selection.md`
