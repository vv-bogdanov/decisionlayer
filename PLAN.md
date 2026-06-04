# Current Plan: Coding Proof Variance And Publishable Lane

## Goal

Turn the current Decision Layer coding evidence into a cleaner proof. The next
objective is not to build more product surface. It is to measure whether
applicability-gated decisions (`D1G`) beat no decisions (`D0`) under the same
backend/model despite agent variance.

This remains a POC. Do not build REST APIs, UI, vector DBs, graph memory,
custom judges, or a custom benchmark unless they are directly needed for the
proof.

## Current Evidence

Completed reports:

```text
reports/swe-contextbench-mini.md
reports/swe-contextbench-large.md
reports/swe-contextbench-followup-gated.md
reports/swe-contextbench-repeat-variance.md
```

Mini-slice:

```text
D0 1/5
D1 3/5
D2 1/5
```

Large slice, excluding three infrastructure-invalid Matplotlib pairs:

```text
D0 9/17
D1 8/17
D2 7/17
```

Follow-up gated diagnostic:

```text
config=configs/swe-contextbench-followup-gated-slice.json
artifact_root=/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-followup-gated-slice-codex

D0  1/7
D1  2/7
D1G 3/7
D2  1/7

agent_ok=7/7 for every mode
benchmark-noise patches=0 for every mode
infra_errors=0
```

Three-run D0 vs D1G repeat diagnostic:

```text
config=configs/swe-contextbench-followup-gated-slice.json

D0  resolved trials:  3/21
D1G resolved trials:  9/21

D0  per-run resolved:  1/7, 2/7, 0/7
D1G per-run resolved:  3/7, 3/7, 3/7

apply-only:
D0  2/18
D1G 6/18
```

Next larger D0 vs D1G slice:

```text
config=configs/swe-contextbench-d0-d1g-large-slice.json
pairs=17
d1_applicability: apply=15, skip=2
public-artifact preflight: 17/17
local Docker image preflight: 7/17 available, 10/17 missing
```

Important caveat: the follow-up official grading used local images rebuilt with
the official SWE-ContextBench `build_instance.py` module after Docker Hub
rate-limited prebuilt image pulls. Treat it as a diagnostic recovery run, not a
publishable prebuilt-image lane.

## Interpretation

The Decision Layer signal is still plausible, and `D1G` is now the best
headline lane for the next coding proof. The repeat diagnostic also confirms
agent variance clearly. On `scikit-learn__scikit-learn-25763`, `D0` and `D1G`
had the same effective prompt because the gate skipped the Decision Brief, but
`D1G` solved 3/3 while `D0` solved 1/3. Do not count that pair as memory value.

The cleanest positive signal is still exact decision transfer. In
`django__django-11858` and `sympy__sympy-20567`, D1G solved 3/3 while D0 solved
1/3. The decisions were short, actionable, and mapped directly to the target
failure mode.

D2 should not be the headline lane yet. The extractor often produced reasonable
decisions, but the coding agent misapplied them to the wrong target fix point.
The next D2 work, if any, should be an application guard, not a larger memory
system.

## Proof Rules

Keep these constraints for all next proof runs:

- predeclare the benchmark slice before running agents
- same backend/model/reasoning inside a reported lane
- official SWE-ContextBench Docker grading is the source of truth
- no related hidden patch, hidden tests, final answer, or grading result in D1/D2
- skip completed agent/grading steps by default; overwrite only explicitly
- keep OpenCode and Codex as separate measurement lanes
- sanitized single-commit workspace checkout
- no OpenCode subagents inside proof runs
- no `git log`, `git show`, or `git blame`
- no installs, virtualenvs, `pip`, `uv`, `sudo`, or `pkexec`
- no edits to tests, fixtures, benchmark files, docs, or generated artifacts
- no product platform work unless it directly improves the proof

## Active Checklist

- [ ] Prefer authenticated/prebuilt SWE-ContextBench image pulls for the
  publishable lane. If local rebuilt images are used again, label the run as
  diagnostic only.
- [ ] Restore or build the 10 missing Docker images for
  `configs/swe-contextbench-d0-d1g-large-slice.json`:
  `sympy__sympy-22908`, `pytest-dev__pytest-7672`,
  `scikit-learn__scikit-learn-25365`, `sympy__sympy-20795`,
  `pytest-dev__pytest-7215`, `django__django-33374`, `psf__requests-2933`,
  `psf__requests-2938`, `sphinx-doc__sphinx-14215`, `django__django-30903`.
- [ ] Rerun Docker preflight for the larger slice and require 17/17 before any
  agent execution.
- [ ] Run the larger slice as `D0` vs `D1G` with repeat variance. Do not include
  `D1` or `D2` in the headline lane.
- [ ] If `D2` is revisited, add a narrow application guard that forces extracted
  decisions to map to the target fix point before prompt injection.
