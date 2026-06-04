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
- [x] Select and run another fresh SWE-ContextBench pair:
  `django__django-11019 -> django__django-30153`.
- [x] Write `reports/swe-contextbench-django-canary.md`.
- [x] Harden the canary runner before another pair:
  `decision-layer run-opencode-canary` requires `opencode --dir`, uses
  permission-skip plus guard-bin, blocks git history regardless of option
  order, blocks install/venv commands, writes timeout-safe timing, saves the
  patch, and emits structured verifier JSON.
- [x] Update agent prompt guidance so local dependency failures do not trigger
  install loops; official Docker grading is the source of truth.
- [x] Select one more fresh SWE-ContextBench pair after runner hardening:
  `sphinx-doc__sphinx-10614 -> sphinx-doc__sphinx-865`.
- [x] Prepare D1 manual and D2 automatic Operational Decision Briefs for
  `sphinx-doc__sphinx-10614 -> sphinx-doc__sphinx-865` from base-task artifacts
  only.
- [x] Run the selected one-pair D0/D1/D2 canary with
  `decision-layer run-opencode-canary`, verifier JSON, guard audit, official
  grading, and a concise result report.
- [x] Add canary runner progress/audit logging for future long runs:
  `--progress-log` writes stage events, and `--audit-json` summarizes commands,
  blocked outputs, errors, and subagent mentions.
- [x] Tighten the D2 extractor prompt/schema so conditional implementation
  decisions survive summarization. The reusable prompt artifact is
  `configs/swe-contextbench-operational-extractor-prompt.md`.
- [x] Tighten counted-run audit rules: `decision-layer run-opencode-canary`
  supports `--fail-on-dirty-audit` so blocked install/venv/git-history attempts
  can make proof runs fail even if the patch later passes.
- [x] Run a diagnostic D2 retry on `sphinx-doc__sphinx-865` with the tightened
  extractor prompt. The standard retry produced no patch due an OpenCode
  subagent tool-call formatting failure; the direct/no-subagent retry resolved
  officially (F2P 1/1, P2P 5/5) with clean verifier and audit. This is
  extractor debugging, not proof evidence for that pair.
- [x] Select the next fresh SWE-ContextBench pair for proof-run:
  `psf__requests-1142 -> psf__requests-1144`.
- [x] Prepare D1 manual and D2 automatic Operational Decision Briefs for
  `psf__requests-1142 -> psf__requests-1144` from base-task artifacts only.
- [x] Run a gold/reference grading preflight for `psf__requests-1144`.
- [x] Run clean D0/D1/D2 on `psf__requests-1144` with sanitized single-commit
  workspaces, `decision-layer run-opencode-canary`, `--audit-json`,
  `--progress-log`, `--fail-on-dirty-audit`, verifier JSON, and official
  grading.
- [x] Write `reports/swe-contextbench-requests-canary.md`.
- [x] Satisfy the mini-slice gate with a clean D2 signal:
  D0 failed officially, D2 resolved officially, D2 verifier passed, D2 audit was
  clean, and P2P stayed 5/5.
- [x] Write `reports/swe-contextbench-sphinx865-canary.md`.

Next selected canary: `sphinx-doc__sphinx-10614 -> sphinx-doc__sphinx-865`.
Reason: the related task is small (F2P 1, P2P 5), the base accepted patch
touches only `sphinx/ext/inheritance_diagram.py`, and the reusable operational
decision is concrete: inheritance-diagram links must use the resolved `refuri`
without adding SVG-specific `../` prefixes, while external intersphinx refs use
the URI fragment as the graph node key. Related hidden patch/tests were not
inspected during selection.

Sphinx canary result: no clean Decision Layer signal. D0, D1, and D2 all
resolved `sphinx-doc__sphinx-8052`, but all non-gold variants regressed the same
PASS_TO_PASS test. D1 contained the right subscript-preservation decision, but
the agent ignored it; D2 attempted it but produced an over-broad patch. The
important protocol lesson is to sanitize repository history and keep structured
logs, timing, diffs, guard audits, and official grading reports for each run.

Django canary result: mixed but not clean proof. D0 timed out with no patch. D1
manual operational brief produced a partial patch that officially resolved the
target F2P tests, but the run timed out, failed the patch verifier, attempted
installs/history commands, and regressed one PASS_TO_PASS test. D2 used the
auto brief but produced an over-broad patch that broke verifier setup. This is a
promising direction signal, not publishable evidence.

Sphinx-865 canary result: useful manual D1 signal, but not enough to start the
mini-slice. D0 failed (F2P 0/1, P2P 5/5), D1 resolved (F2P 1/1, P2P 5/5), and
D2 failed (F2P 0/1, P2P 5/5). D1 was audit-dirty because guard-bin blocked
install/venv attempts; D2 failed because automatic extraction lost the
`internal is false -> URI fragment is graph key` decision. The verifier also
needs less brittle required-term matching because D1 used `split('#')[-1]`
instead of the literal `rsplit` term.

Next selected proof pair: `psf__requests-1142 -> psf__requests-1144`.
Reason: the related task is small (F2P 1, P2P 5), the base accepted patch
touches only `requests/models.py`, and the reusable operational decision is
compact: `prepare_content_length()` should not add `Content-Length: 0` for
bodyless `GET` or `HEAD` requests, while still setting it for bodyless methods
that can carry a body. Related hidden patch/tests were not inspected during
selection.

Requests canary result: clean D2 proof signal. D0 changed `requests/utils.py`
and failed (F2P 0/1, P2P 5/5). D1 and D2 both changed `requests/models.py`,
passed verifier/audit, and resolved officially (F2P 1/1, P2P 5/5). This is the
first canary that clears the gate for a preselected 5-pair mini-slice.

## Active Checklist

- [ ] Select a predeclared 5-pair SWE-ContextBench mini-slice and save only the
  small selection metadata in this repository.
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
- `reports/swe-contextbench-sphinx-canary.md`
- `reports/swe-contextbench-django-canary.md`
- `reports/swe-contextbench-sphinx865-canary.md`
- `reports/swe-contextbench-requests-canary.md`
- `docs/research-report.md`
- `docs/coding-benchmark-selection.md`
