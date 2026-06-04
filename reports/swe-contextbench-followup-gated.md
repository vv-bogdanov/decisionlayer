# SWE-ContextBench Follow-Up Gated Run

Date: 2026-06-04

## Status

This follow-up is complete as a diagnostic run. It tested a 7-pair
SWE-ContextBench slice with `D1G`, an applicability-gated variant of manual
Decision Brief injection.

Artifact root:

```text
/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-followup-gated-slice-codex
```

Config:

```text
configs/swe-contextbench-followup-gated-slice.json
```

The run used Codex Spark with low reasoning for all modes.

## Protocol

Modes:

- D0: related public issue only, no Decision Brief.
- D1: related public issue plus the manually reviewed reusable decision.
- D1G: same as D1 only when `d1_applicability=apply`; otherwise no Decision
  Brief.
- D2: related public issue plus the automatically extracted Decision Brief from
  local llama.cpp.

Agent patches were generated before grading and then reused from cache for the
final official grading run.

The first grading attempt exposed two SWE-ContextBench harness constraints:

- `evaluation.sh` is not concurrency-safe because it writes shared
  `batch_dataset.json` and `batch_predictions.json` files.
- `run_evaluation` removes original instance images by default, which breaks
  multi-mode grading unless `--no-remove-instance-image` is used.

The local runner now serializes grading and calls the official Python modules
directly with `--no-remove-instance-image`.

Because the first attempt had already removed the instance images and Docker Hub
was rate-limiting unauthenticated pulls, the 7 instance images were rebuilt
locally with the official SWE-ContextBench `build_instance.py` module and tagged
as the expected `jiayuanz3/swecontextbench:*` images. Treat this as a diagnostic
recovery run. For a publishable lane, rerun after authenticated/prebuilt image
pulls are available.

## Completed Checks

Preflight:

```text
7/7 config/schema/public-artifact checks passed
7/7 local instance images available
```

Agent phase:

| Mode | Agent ok | Benchmark-noise patches |
| --- | ---: | ---: |
| D0 | 7/7 | 0 |
| D1 | 7/7 | 0 |
| D1G | 7/7 | 0 |
| D2 | 7/7 | 0 |

Official grading:

```text
28/28 grading jobs completed
0 infra errors
```

## Totals

| Mode | Resolved | Agent ok | Benchmark-noise patches | Infra errors |
| --- | ---: | ---: | ---: | ---: |
| D0 | 1/7 | 7/7 | 0 | 0 |
| D1 | 2/7 | 7/7 | 0 | 0 |
| D1G | 3/7 | 7/7 | 0 | 0 |
| D2 | 1/7 | 7/7 | 0 | 0 |

## Result Table

| Related task | Gate | D0 | D1 | D1G | D2 | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `django__django-27914` | apply | no | no | no | no | Same nested-class decision, still hard transfer. |
| `django__django-11858` | apply | yes | no | yes | no | D1G produced the broader serializer fix; D1 was too narrow. |
| `scikit-learn__scikit-learn-25763` | skip | no | yes | yes | yes | D1G and D0 had no Decision Brief, so this mainly shows agent variance. |
| `django__django-31640` | apply | no | no | no | no | Timezone truncation decision did not transfer. |
| `sympy__sympy-20567` | apply | no | yes | yes | no | Clear D1/D1G uplift; D2 extracted the right decision but applied it at the wrong layer. |
| `django__django-26193` | apply | no | no | no | no | urlize punctuation decision did not transfer. |
| `django__django-26430` | apply | no | no | no | no | EmptyResultSet decision did not transfer. |

## Observations

The run is encouraging but not yet causal proof. `D1G` has the best total
(`3/7`), but one solved skip-labeled case had the same effective prompt as D0
and still diverged. That means single-run variance is large enough to move the
headline result.

The strongest useful signal remains narrow and practical: a compact decision can
make the agent solve a related coding task when the decision maps exactly to the
target failure mode. The `sympy__sympy-20567` result is the cleanest example in
this run.

`D2` is still not the bottleneck we first expected. In at least two failures the
automatic extractor produced a reasonable decision, but the coding agent applied
it incorrectly:

- `django__django-11858`: D2 used `__qualname__` only for non-builtin
  `TypeSerializer` paths and missed the passing broader fix.
- `sympy__sympy-20567`: D2 extracted `__slots__ = ()` correctly, but added it
  around `DefaultPrinting` instead of the actual mixin class used by the target
  hierarchy.

So the next improvement should be an application/gating protocol, not a larger
custom memory system.

## Conclusion

`D1G` is the best candidate lane to continue testing, but the next step should
measure variance before scaling the benchmark. A publishable claim needs either
repeat trials or a deterministic backend; otherwise one lucky or unlucky Codex
sample can dominate a small slice.

Recommended next proof work:

- Repeat this 7-pair diagnostic with separate artifact roots to estimate
  D0/D1G variance before claiming net uplift.
- Keep D2 out of the headline until it has an application guard that forces the
  agent to map extracted decisions to the correct target fix point.
- For the next broader coding proof, compare D0 vs D1G first. Add D2 only as a
  secondary diagnostic lane.
