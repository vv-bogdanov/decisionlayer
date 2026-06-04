# SWE-ContextBench Large Slice Result

Date: 2026-06-04

## Summary

This run tested the next predeclared coding slice after the 5-pair mini-slice.
It used the same agent/backend/model across D0, D1, and D2.

```text
benchmark=SWE-ContextBench Verified subset
config=configs/swe-contextbench-large-slice.json
pairs=20 predeclared related coding tasks
valid_official_pairs=17
agent=codex exec
model=gpt-5.3-codex-spark
reasoning_effort=low
artifact_root=/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-large-slice-codex
```

Three Matplotlib pairs could not be evaluated because the hardened Docker image
was not available/pullable. They are excluded from the valid denominator.

Headline official result on valid pairs:

```text
D0 no Decision Brief:          9/17 resolved
D1 manual Decision Brief:      8/17 resolved
D2 automatic Decision Brief:   7/17 resolved
```

Strict-clean result, excluding patches that touched test files:

```text
D0 strict-clean: 7/12
D1 strict-clean: 6/12
D2 strict-clean: 6/15
```

Conclusion: the larger slice confirms that D1 can produce real uplift on
individual coding tasks, but it does not show net improvement yet. Decision
Briefs need applicability gating; wrong or merely adjacent decisions can hurt.
D2 did not produce any uplift in this run.

## Protocol

Modes:

- D0: related public issue only, no Decision Brief.
- D1: related public issue plus manually reviewed Decision Brief from base
  public problem, base hints, and base accepted patch.
- D2: related public issue plus automatically extracted Decision Brief from the
  same base artifacts via local llama.cpp.

The run used the predeclared config committed before agent execution:

```text
configs/swe-contextbench-large-slice.json
```

Run commands:

```text
scripts/run-swe-contextbench-mini-slice --config configs/swe-contextbench-large-slice.json --agent-backend codex --phase prepare --extract-timeout-seconds 240
scripts/run-swe-contextbench-mini-slice --config configs/swe-contextbench-large-slice.json --agent-backend codex --phase agents --timeout-seconds 300
scripts/run-swe-contextbench-mini-slice --config configs/swe-contextbench-large-slice.json --agent-backend codex --phase grade --grading-timeout-seconds 1800
```

Machine summary command:

```text
scripts/summarize-swe-contextbench-run --artifact-root /home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-large-slice-codex --config configs/swe-contextbench-large-slice.json
```

## Result Table

| Related task | D0 | D1 | D2 | Classification |
| --- | --- | --- | --- | --- |
| `sympy__sympy-22908` | yes | yes | yes | baseline solved |
| `django__django-27914` | no | no | no | all fail |
| `django__django-11858` | no | yes | no | D1 uplift |
| `matplotlib__matplotlib-26319` | infra | infra | infra | excluded: image unavailable |
| `matplotlib__matplotlib-26468` | infra | infra | infra | excluded: image unavailable |
| `pytest-dev__pytest-7672` | no | no | no | patch failed in all modes |
| `scikit-learn__scikit-learn-25763` | yes | no | no | D1/D2 regression |
| `scikit-learn__scikit-learn-25365` | yes | yes | yes | baseline solved |
| `django__django-31640` | no | no | no | all fail |
| `sympy__sympy-20795` | yes | yes | yes | baseline solved |
| `sympy__sympy-20567` | yes | no | yes | D1 regression |
| `django__django-26193` | no | no | no | all fail |
| `pytest-dev__pytest-7215` | no | no | no | patch failed in all modes |
| `django__django-26430` | no | no | no | all fail; D2 produced no patch |
| `django__django-33374` | yes | no | no | D1/D2 regression |
| `psf__requests-2933` | yes | yes | yes | baseline solved |
| `psf__requests-2938` | yes | yes | yes | baseline solved |
| `sphinx-doc__sphinx-14215` | yes | yes | yes | baseline solved, but patches touched tests |
| `matplotlib__matplotlib-22864` | infra | infra | infra | excluded: image unavailable |
| `django__django-30903` | no | yes | no | D1 uplift |

## Signals

D1 uplift cases:

- `django__django-11858`: D0 failed with `0/1` F2P and a test-file edit. D1
  passed with a source-only patch. The accepted decision was exactly useful:
  nested class serialization must use `__qualname__`, not `__name__`.
- `django__django-30903`: D0 failed with `0/2` F2P. D1 passed with `2/2` F2P.
  The useful decision was about composing index SQL fragments with explicit
  spaces only when optional suffixes are non-empty.

D1 regressions:

- `scikit-learn__scikit-learn-25763`: D0 passed; D1/D2 failed. The selected
  decision about `set_output` propagation was adjacent but not the right fix for
  `IsotonicRegression.predict`.
- `sympy__sympy-20567`: D0 and D2 passed; D1 failed. The manual brief was
  correct in substance, but the agent placed `__slots__ = ()` inside the class
  docstring instead of as a class attribute.
- `django__django-33374`: D0 passed by changing `WhereNode`; D1/D2 followed the
  base `CASE WHEN` direction and missed the related task's better fix point.

D2 outcome:

- D2 had no uplift over D0.
- D2 matched D1 on some base decisions but failed to drive correct application
  in the two D1-uplift cases.
- The richer D2 prompt helped artifact clarity, but automatic extraction plus
  agent application is still weaker than manual D1.

## Hygiene

Strict patch verifier found benchmark-noise patches:

```text
D0 test-file edits: 5/20
D1 test-file edits: 5/20
D2 test-file edits: 2/20
```

Official grading can still pass patches that touch tests because the model patch
is applied after the benchmark test patch. For publishable claims, report both:

- official resolved, because the external benchmark says so;
- strict-clean resolved, because test edits are not acceptable proof hygiene.

Patch application failures:

- `pytest-dev__pytest-7672`: patch failed in all modes.
- `pytest-dev__pytest-7215`: patch failed in all modes.
- `django__django-26430` D2: no patch.

Infrastructure exclusions:

- `matplotlib__matplotlib-26319`
- `matplotlib__matplotlib-26468`
- `matplotlib__matplotlib-22864`

The Docker harness reported hardened image unavailable/pull failure for these
instances. They should be replaced before a publishable aggregate claim.

## Interpretation

The Decision Layer idea remains plausible but narrower than the mini-slice made
it look.

What the run proves:

- Compact accepted decisions can change a coding agent outcome from fail to pass
  on external benchmark tasks.
- Manual D1 is useful for analyzing the upper bound of the idea.
- Strict patch hygiene is necessary; local `agent_ok` caught test-file edits that
  official grading alone would not make obvious.

What the run does not prove:

- It does not prove net improvement on a broad slice.
- It does not prove the current automatic extractor is good enough.
- It does not prove every related task should receive a Decision Brief.

Main architectural implication: Decision Layer should not be a blind prompt
append. It needs an applicability gate. A decision should be injected only when
the current task clearly matches the decision's scope and failure mode.

## Recommendations

Next work should be focused rather than larger:

- Add preflight validation for selected benchmark pairs: hardened image
  availability, no prior diagnostic contamination, and expected grading support.
- Add a hard prompt rule for proof agents: do not edit test files.
- Add source-only patch enforcement before grading, while still saving noisy
  patches for diagnostics.
- Build an applicability classifier/gate for D1/D2 instead of always injecting
  any related decision.
- Improve D2 against the observed failures: preserve ordering of operations
  (`opclass` before suffix in Django index SQL), avoid adding fallback code not
  present in the accepted decision, and separate "same fix point" from "adjacent
  subsystem".
- Rerun a smaller replacement slice with invalid Matplotlib pairs removed before
  claiming aggregate numbers.

