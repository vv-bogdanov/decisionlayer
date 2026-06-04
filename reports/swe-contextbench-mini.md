# SWE-ContextBench Mini-Slice Result

Date: 2026-06-04

## Summary

This run tested whether a compact Decision Brief from a prior related coding
task helps the same agent/model solve a later related task.

Benchmark lane:

```text
benchmark=SWE-ContextBench Verified subset
pairs=5 predeclared base -> related pairs
agent=codex exec
model=gpt-5.3-codex-spark
reasoning_effort=low
official_grader=SWE-ContextBench Docker harness
artifact_root=/home/dev/benchmarks/swe-contextbench/agent-runs/mini-slice-codex
```

Headline result:

```text
D0 no Decision Brief:          1/5 resolved
D1 manual Decision Brief:      3/5 resolved
D2 automatic Decision Brief:   1/5 resolved
```

The mini-slice supports the narrow claim that an accepted operational decision
can help coding agents on related longer-horizon tasks. It does not yet support
the claim that the current automatic extractor is good enough.

## Protocol

Modes:

- D0: related task only, no Decision Brief.
- D1: related task plus a manually reviewed Decision Brief extracted only from
  the base task public problem, hints, and accepted patch.
- D2: related task plus an automatically extracted Decision Brief from the same
  base-task artifacts.

The related public issue text was visible to all modes equally. Hidden patches,
hidden tests, grading results, and related final answers were not used to write
D1 or D2 briefs.

Run command:

```text
scripts/run-swe-contextbench-mini-slice --agent-backend codex --phase all --timeout-seconds 300 --grading-timeout-seconds 900
```

OpenCode was tried first as a diagnostic lane, but stalled/timed out on this
slice. Its partial artifacts were not mixed into the reported D0/D1/D2 numbers.

## Official Results

| Related task | D0 | D1 | D2 | Signal |
| --- | ---: | ---: | ---: | --- |
| `sympy__sympy-12426` | no | yes | no | D1 uplift |
| `matplotlib__matplotlib-15087` | no | yes | yes | D1 and D2 uplift |
| `django__django-28322` | yes | yes | no | D0 already solves; D2 patch failed to apply |
| `django__django-29343` | no | no | no | no solve |
| `sphinx-doc__sphinx-7418` | no | no | no | no solve |

Resolved totals:

| Mode | Resolved | Notes |
| --- | ---: | --- |
| D0 | 1/5 | Baseline solved only the Django MySQL SSL case. |
| D1 | 3/5 | Manual decisions fixed SymPy symbolic equality and Matplotlib SVG gid propagation. |
| D2 | 1/5 | Automatic extraction helped Matplotlib, but failed or overfit elsewhere. |

Detailed grader outcomes:

| Related task | Mode | Agent s | Patch applied | F2P | P2P | Official resolved |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| `sympy__sympy-12426` | D0 | 10.33 | yes | 0/1 | 2/2 | no |
| `sympy__sympy-12426` | D1 | 28.46 | yes | 1/1 | 2/2 | yes |
| `sympy__sympy-12426` | D2 | 20.75 | yes | 0/1 | 2/2 | no |
| `matplotlib__matplotlib-15087` | D0 | 53.96 | yes | 0/1 | 4/4 | no |
| `matplotlib__matplotlib-15087` | D1 | 89.82 | yes | 1/1 | 4/4 | yes |
| `matplotlib__matplotlib-15087` | D2 | 73.49 | yes | 1/1 | 4/4 | yes |
| `django__django-28322` | D0 | 10.83 | yes | 1/1 | 4/4 | yes |
| `django__django-28322` | D1 | 16.39 | yes | 1/1 | 4/4 | yes |
| `django__django-28322` | D2 | 16.04 | no | n/a | n/a | no |
| `django__django-29343` | D0 | 36.87 | yes | 0/1 | 4/4 | no |
| `django__django-29343` | D1 | 74.90 | yes | 0/1 | 4/4 | no |
| `django__django-29343` | D2 | 27.61 | yes | 0/1 | 4/4 | no |
| `sphinx-doc__sphinx-7418` | D0 | 87.17 | yes | 0/1 | 12/12 | no |
| `sphinx-doc__sphinx-7418` | D1 | 51.29 | yes | 0/1 | 12/12 | no |
| `sphinx-doc__sphinx-7418` | D2 | 68.43 | yes | 0/1 | 12/12 | no |

## Case Notes

SymPy produced the cleanest D1 signal. D0 made a direct diagonal-entry fix that
failed on symbolic equality. D1 gave the agent the transferable decision:
unknown symbolic equality must remain symbolic through `KroneckerDelta`, and the
official F2P passed.

Matplotlib produced the cleanest D2 signal. The automatic extractor captured the
operational pattern: wrap draw bodies in renderer groups using the artist gid.
D0 failed, while both D1 and D2 passed.

Django MySQL SSL is not useful as uplift evidence because D0 already solved it.
D2 overfit the base PostgreSQL decision and generated a patch that did not apply
cleanly in official grading.

Django HEAD did not solve in any mode. D1/D2 moved the agent toward the right
area, but the resulting patch still missed official behavior. This is a good
diagnostic case for brief completeness and agent compliance.

Sphinx glossary did not solve in any mode. D2 contained both relevant decisions,
but the generated patch implemented only part of them. This looks more like
agent compliance/application failure than pure extraction failure.

## Runner Notes

The full Codex run exited non-zero because the local audit marked three agent
runs dirty due ordinary Codex stderr text being parsed as JSONL. Official
grading still completed for all 15 variants. The audit bug was fixed after this
run in commit `f4bc35b`; future runs keep stderr diagnostics without treating
non-JSON stderr lines as malformed JSONL.

No reported official result depends on OpenCode output.

## Interpretation

The D1 result is the important signal: 3/5 versus D0 1/5 on a predeclared
external coding benchmark slice, with the same backend/model. This is small and
not statistically publishable by itself, but it is enough to justify a larger
coding-focused run.

D2 is currently the weak link. The extractor can find useful decisions, but it
also overfits to base-task implementation details or produces briefs that the
agent only partially follows. The next milestone should measure whether D2 can
recover toward D1 after tightening the extraction/brief format, not whether we
can hand-tune individual related tasks.

## Recommendations

Next practical steps:

- Keep Codex Spark low-reasoning as the primary measurement lane for now.
- Treat OpenCode as diagnostic only until it is more stable on this benchmark.
- Add a stricter patch policy for proof runs: benchmark submissions should avoid
  test-file edits unless explicitly allowed by the task.
- Add a compact report generator so result tables are reproducible from artifact
  JSON, not hand-copied.
- Build a larger predeclared coding slice, preferably 20 verified related pairs,
  and run D0/D1/D2 under the same Codex lane.
- Improve the D2 extractor against the five completed cases without using
  related hidden patches/tests: favor transferable operational decisions, include
  applicability scope, and reject base-specific implementation trivia.

