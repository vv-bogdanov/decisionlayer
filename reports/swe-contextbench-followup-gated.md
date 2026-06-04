# SWE-ContextBench Follow-Up Gated Run

## Status

This follow-up is a 7-pair diagnostic run, not a new blind aggregate. It tests
manual applicability gating via `D1G` after the larger 20-pair run showed both
D1 uplift and D1 regressions.

Artifact root:

```text
/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-followup-gated-slice-codex
```

Config:

```text
configs/swe-contextbench-followup-gated-slice.json
```

## Completed

Preflight passed before agent execution:

```text
7/7 config/schema/public-artifact checks passed
7/7 hardened Docker images were locally available before grading
```

Agent phase completed with Codex Spark low reasoning:

| Mode | Agent ok | Benchmark-noise patches |
| --- | ---: | ---: |
| D0 | 7/7 | 0 |
| D1 | 7/7 | 0 |
| D1G | 7/7 | 0 |
| D2 | 7/7 | 0 |

No agent patch touched test files, benchmark files, docs, or generated artifacts.

## Grading Blocker

The official grading results currently in the artifact directory must not be
used as proof. The first grading attempt exposed two harness constraints:

- `evaluation.sh` writes shared `batch_dataset.json` and
  `batch_predictions.json`, so parallel grading corrupts runs.
- `run_evaluation` removes the original hardened instance image by default.
  This breaks multi-mode grading for the same instance unless the official
  module is called with `--no-remove-instance-image`.

The runner has been fixed to serialize grading and call the official Python
modules directly with `--no-remove-instance-image`. However, the earlier
grading attempt already removed the 7 follow-up instance images. Docker Hub is
currently returning an unauthenticated pull rate-limit error for all 7 images,
so official grading is blocked until the images can be restored.

## Resume Commands

After Docker Hub rate limit reset or `docker login`, resume from cached agent
patches:

```text
scripts/run-swe-contextbench-mini-slice \
  --config configs/swe-contextbench-followup-gated-slice.json \
  --phase preflight \
  --agent-backend codex \
  --preflight-docker pull \
  --preflight-timeout-seconds 600

scripts/run-swe-contextbench-mini-slice \
  --config configs/swe-contextbench-followup-gated-slice.json \
  --phase grade \
  --modes D0,D1,D1G,D2 \
  --agent-backend codex \
  --grading-timeout-seconds 2400 \
  --overwrite

scripts/summarize-swe-contextbench-run \
  --artifact-root /home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-followup-gated-slice-codex \
  --config configs/swe-contextbench-followup-gated-slice.json \
  --modes D0,D1,D1G,D2
```

## Interim Takeaway

The agent-side part is clean enough to continue: all four modes produced
source-only patches with no benchmark-noise edits. The remaining proof work is
purely official grading recovery, not another agent run.
