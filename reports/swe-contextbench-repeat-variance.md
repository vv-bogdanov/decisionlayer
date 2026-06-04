# SWE-ContextBench D0 vs D1G Repeat Variance

Date: 2026-06-04

## Summary

This diagnostic repeats the 7-pair follow-up slice for the two lanes that matter
next: `D0` and `D1G`.

Config:

```text
configs/swe-contextbench-followup-gated-slice.json
```

Artifact roots:

```text
/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-followup-gated-slice-codex
/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-followup-gated-slice-codex-repeat-02
/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-followup-gated-slice-codex-repeat-03
```

Protocol:

- same backend/model/reasoning: Codex Spark, low reasoning
- same benchmark config
- separate artifact roots per repeat
- only `D0,D1G` for repeats 02 and 03
- official SWE-ContextBench grading for every trial
- local instance images rebuilt with official `build_instance.py`; diagnostic,
  not publishable prebuilt-image proof

## Totals

| Run | D0 | D1G |
| --- | ---: | ---: |
| baseline | 1/7 | 3/7 |
| repeat-02 | 2/7 | 3/7 |
| repeat-03 | 0/7 | 3/7 |

Aggregate:

| Mode | Resolved trials | Per-run resolved | Min-Max | Infra errors | Noise |
| --- | ---: | --- | ---: | ---: | ---: |
| D0 | 3/21 | 1/7, 2/7, 0/7 | 0-2 | 0 | 0 |
| D1G | 9/21 | 3/7, 3/7, 3/7 | 3-3 | 0 | 0 |

Pair matrix:

| Pair | Gate | D0 | D1G |
| --- | --- | ---: | ---: |
| `django__django-11858` | apply | 1/3 | 3/3 |
| `django__django-26193` | apply | 0/3 | 0/3 |
| `django__django-26430` | apply | 0/3 | 0/3 |
| `django__django-27914` | apply | 0/3 | 0/3 |
| `django__django-31640` | apply | 0/3 | 0/3 |
| `scikit-learn__scikit-learn-25763` | skip | 1/3 | 3/3 |
| `sympy__sympy-20567` | apply | 1/3 | 3/3 |

Apply-only aggregate:

```text
D0  2/18
D1G 6/18
```

## Interpretation

`D1G` is more stable than `D0` on this diagnostic slice: it solved exactly 3/7
in every run, while `D0` moved between 0/7 and 2/7.

The strongest decision-layer signal is apply-only:

- `django__django-11858`: D1G solved 3/3, D0 solved 1/3.
- `sympy__sympy-20567`: D1G solved 3/3, D0 solved 1/3.

The `scikit-learn__scikit-learn-25763` result must not be counted as a Decision
Brief win. Its gate is `skip`, and the `D0` and `D1G` prompts are byte-for-byte
identical. `D1G` solved 3/3 while `D0` solved 1/3, so this pair shows sampling
variance or execution-order variance, not memory value.

The hard-transfer failures are also stable:

- `django__django-27914`
- `django__django-31640`
- `django__django-26193`
- `django__django-26430`

The decision brief did not hurt these pairs, but it did not make the agent find
the missing target fix point either.

## Conclusion

This is a better signal than the single follow-up run, but still not enough for
a publishable claim. It supports the next experiment:

- move the headline lane from blind `D1` to gated `D1G`
- compare `D0` vs `D1G` first
- keep `D2` as secondary until application-guard work exists
- use prebuilt/authenticated images for publishable numbers, or clearly label
  local rebuilt-image runs as diagnostics

The next slice should be larger than 7 pairs, predeclared before execution, and
reported with repeat variance rather than a single total.
