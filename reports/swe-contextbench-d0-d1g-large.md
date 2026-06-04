# SWE-ContextBench D0 vs D1G Large Diagnostic

Date: 2026-06-04

## Summary

This run is the first larger `D0` vs `D1G` diagnostic after the 7-pair repeat
variance test.

Config:

```text
configs/swe-contextbench-d0-d1g-large-slice.json
```

Artifact root:

```text
/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-d0-d1g-large-slice-codex
```

Protocol:

- Codex Spark, low reasoning
- modes: `D0,D1G`
- 17 pairs derived from the prior SWE-ContextBench large slice
- three prior infrastructure-invalid Matplotlib pairs excluded
- local images rebuilt with official `build_instance.py`; diagnostic only

## Checks

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

## Interpretation

The larger single run does not show net Decision Layer improvement. `D1G`
matched `D0` on every pair: no uplift, no regression.

This does not erase the 7-pair repeat signal, but it narrows the claim. The
current gated decision brief helps only when the agent is already near the right
fix point. On this broader slice, most outcomes were either baseline-obvious or
hard failures where the decision did not change the search path enough.

Two cases are especially useful for variance tracking:

- `django__django-11858`: `D1G` solved 3/3 in the smaller repeat diagnostic, but
  failed here. This is another variance warning.
- `sympy__sympy-20567`: the smaller repeat showed D1G advantage over D0, but in
  this larger run both modes solved.

## Next Step

Run at least one more larger `D0` vs `D1G` repeat before making an aggregate
claim. If the second larger run also shows no delta, the next engineering work
should shift from prompt-level gating to application guidance: make the agent
prove how a decision maps to the target fix point before editing.
