# SWE-ContextBench D0 vs D1G Large Diagnostic

Date: 2026-06-04

## Summary

This report tracks the larger `D0` vs `D1G` diagnostic after the 7-pair repeat
variance test. It now includes two 17-pair runs.

Config:

```text
configs/swe-contextbench-d0-d1g-large-slice.json
```

Primary artifact roots:

```text
/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-d0-d1g-large-slice-codex
/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-d0-d1g-large-slice-codex-repeat-02
```

Protocol:

- Codex Spark, low reasoning
- modes: `D0,D1G`
- 17 pairs derived from the prior SWE-ContextBench large slice
- three prior infrastructure-invalid Matplotlib pairs excluded
- local images rebuilt with official `build_instance.py`; diagnostic only

## Run 01 Checks

```text
public-artifact preflight: 17/17
local Docker image preflight: 17/17
agent phase: D0 17/17, D1G 17/17
benchmark-noise patches: 0
official grading: 34/34
infra errors: 0
```

## Totals

| Mode | Resolved | Agent ok | Benchmark-noise patches | Infra errors |
| --- | ---: | ---: | ---: | ---: |
| D0 | 10/17 | 17/17 | 0 | 0 |
| D1G | 10/17 | 17/17 | 0 | 0 |

## Result Table

| Pair | Gate | D0 | D1G | Classification |
| --- | --- | --- | --- | --- |
| `sympy__sympy-22908` | apply | yes | yes | baseline solved |
| `django__django-27914` | apply | no | no | both fail |
| `django__django-11858` | apply | no | no | both fail |
| `pytest-dev__pytest-7672` | apply | no | no | patch failed in both modes |
| `scikit-learn__scikit-learn-25763` | skip | yes | yes | baseline solved |
| `scikit-learn__scikit-learn-25365` | skip | yes | yes | baseline solved |
| `django__django-31640` | apply | no | no | both fail |
| `sympy__sympy-20795` | apply | yes | yes | baseline solved |
| `sympy__sympy-20567` | apply | yes | yes | baseline solved |
| `django__django-26193` | apply | no | no | both fail |
| `pytest-dev__pytest-7215` | apply | yes | yes | baseline solved |
| `django__django-26430` | apply | no | no | both fail |
| `django__django-33374` | apply | yes | yes | baseline solved |
| `psf__requests-2933` | apply | yes | yes | baseline solved |
| `psf__requests-2938` | apply | yes | yes | baseline solved |
| `sphinx-doc__sphinx-14215` | apply | yes | yes | baseline solved |
| `django__django-30903` | apply | no | no | both fail |

## Repeat 02

Artifact root:

```text
/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-d0-d1g-large-slice-codex-repeat-02
```

Checks:

```text
public-artifact preflight: 17/17
local Docker image preflight: 17/17
agent phase: D0 16/17, D1G 17/17
benchmark-noise patches: D0 1, D1G 0
official grading: 34/34
infra errors: 0
```

Official totals:

| Mode | Resolved | Agent ok | Benchmark-noise patches | Infra errors |
| --- | ---: | ---: | ---: | ---: |
| D0 | 10/17 | 16/17 | 1 | 0 |
| D1G | 11/17 | 17/17 | 0 | 0 |

The noisy D0 patch is `sphinx-doc__sphinx-14215`: it solved the benchmark but
edited `tests/test_quickstart.py`, so it should not be treated as a clean proof
trial.

Repeat-02 deltas:

| Pair | Gate | D0 | D1G | Classification |
| --- | --- | --- | --- | --- |
| `django__django-26193` | apply | no | yes | D1G-only by official resolved; P2P 33/35 caveat |
| `django__django-30903` | apply | no | yes | clean D1G-only |
| `pytest-dev__pytest-7215` | apply | yes | no | D0-only, D1G patch failed |
| `sphinx-doc__sphinx-14215` | apply | yes | yes | D0 noisy success |

Delta case notes:

- `django__django-26193`: D0 only changed trailing punctuation stripping from
  `if` to `while`, so the FAIL_TO_PASS test still failed. D1G used the decision
  about escaped/unescaped length handling and passed the target test, but also
  had two PASS_TO_PASS failures. Treat this as useful evidence for decision
  direction, not as a clean patch-quality win.
- `django__django-30903`: D0 tried to special-case `ASC`/`DESC`. D1G followed
  the decision to join quoted column, opclass, and suffix as separated parts.
  This is the cleanest larger-slice D1G win.
- `pytest-dev__pytest-7215`: D0 solved with a skip-state flag around teardown.
  D1G generated a plausible skip precheck, but its patch failed to apply.
  This is a counterexample where the decision lane did not preserve baseline
  patchability.

## Two-Run Aggregate

Official aggregate:

| Mode | Resolved trials | Per-run resolved | Infra errors | Noise |
| --- | ---: | --- | ---: | ---: |
| D0 | 20/34 | 10/17, 10/17 | 0 | 1 |
| D1G | 21/34 | 10/17, 11/17 | 0 | 0 |

Clean paired view, dropping only the noisy repeat-02 Sphinx pair from both
lanes:

| Mode | Resolved trials |
| --- | ---: |
| D0 | 19/33 |
| D1G | 20/33 |

Pair matrix after two runs:

| Pair | Gate | D0 | D1G |
| --- | --- | ---: | ---: |
| `django__django-11858` | apply | 0/2 | 0/2 |
| `django__django-26193` | apply | 0/2 | 1/2 |
| `django__django-26430` | apply | 0/2 | 0/2 |
| `django__django-27914` | apply | 0/2 | 0/2 |
| `django__django-30903` | apply | 0/2 | 1/2 |
| `django__django-31640` | apply | 0/2 | 0/2 |
| `django__django-33374` | apply | 2/2 | 2/2 |
| `psf__requests-2933` | apply | 2/2 | 2/2 |
| `psf__requests-2938` | apply | 2/2 | 2/2 |
| `pytest-dev__pytest-7215` | apply | 2/2 | 1/2 |
| `pytest-dev__pytest-7672` | apply | 0/2 | 0/2 |
| `scikit-learn__scikit-learn-25365` | skip | 2/2 | 2/2 |
| `scikit-learn__scikit-learn-25763` | skip | 2/2 | 2/2 |
| `sphinx-doc__sphinx-14215` | apply | 2/2 | 2/2 |
| `sympy__sympy-20567` | apply | 2/2 | 2/2 |
| `sympy__sympy-20795` | apply | 2/2 | 2/2 |
| `sympy__sympy-22908` | apply | 2/2 | 2/2 |

## D1GA Delta Canary

Config:

```text
configs/swe-contextbench-d1ga-delta-canary.json
```

Artifact root:

```text
/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-d1ga-delta-canary-codex
```

`D1GA` is `D1G` plus an explicit application guard that asks the agent to map
each decision to the target issue's concrete failing behavior and source area
before editing.

Checks:

```text
local Docker image preflight: 3/3
agent phase: 3/3
benchmark-noise patches: 0
official grading: 3/3
infra errors: 0
```

| Pair | D0 repeat-02 | D1G repeat-02 | D1GA canary | Notes |
| --- | --- | --- | --- | --- |
| `django__django-26193` | no | yes | no | Guard overcorrected; D1GA made the same incomplete `while middle.endswith(...)` patch as D0. |
| `pytest-dev__pytest-7215` | yes | no | no | D1GA still failed patch application. |
| `django__django-30903` | no | yes | yes | Guard preserved the clean D1G-style fix. |

Result: do not widen `D1GA` as-is. It reduced the delta canary from D1G's
official `2/3` to `1/3`.

## Interpretation

The larger diagnostic shows only a small `D1G` edge after two runs:
officially `21/34` vs `20/34`, or `20/33` vs `19/33` in the clean paired view.
This is not yet a publishable uplift claim.

The result does not erase the 7-pair repeat signal, but it narrows the claim.
The current gated decision brief appears mostly low-risk, but the larger
delta cases do not justify a strong uplift claim: one D1G-only result has a
P2P caveat, one D1G-only result is clean, and one D0-only result is a patch
application failure in D1G. The first guarded prompt canary did not improve
this balance.

Two cases are especially useful for variance tracking:

- `django__django-26193`: repeat-02 is an official D1G-only success with a P2P
  caveat.
- `django__django-30903`: repeat-02 is a clean D1G-only success.
- `pytest-dev__pytest-7215`: repeat-02 is a D0-only success because D1G patch
  application failed.
- `sphinx-doc__sphinx-14215`: repeat-02 D0 solved but edited a test file, so it
  is useful as a hygiene failure, not as signal.

## Next Step

Do not claim a large uplift from the broader slice yet. Do not widen `D1GA`
without a different guard design; the first canary made one useful D1G transfer
too conservative. The next practical step is a publishable lane: authenticated
or prebuilt images, predeclared metrics, and the existing `D0` vs `D1G`
headline comparison.
