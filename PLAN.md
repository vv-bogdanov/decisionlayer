# Current Plan: Next Coding Proof Iteration

## Goal

Tighten the Decision Layer coding proof after the completed 20-pair
SWE-ContextBench run. The goal is now to remove benchmark noise, avoid invalid
instances, and test applicability-gated Decision Briefs instead of blind prompt
injection.

This remains a POC. Do not build a product platform, REST API, UI, vector DB,
custom judge, or custom benchmark unless it is directly needed for D0/D1/D2
measurement.

## Current Evidence

Completed reports:

```text
reports/swe-contextbench-mini.md
reports/swe-contextbench-large.md
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

D1 produced two concrete uplift cases, but also three regressions. D2 produced
no uplift. The next iteration should test whether applicability gating can keep
the uplift while avoiding regressions.

## Rules

Keep these constraints for all next proof runs:

- predeclare the benchmark slice before running agents
- same backend/model/reasoning for D0, D1, and D2 inside a reported lane
- official SWE-ContextBench Docker grading is the source of truth
- no related hidden patch, hidden tests, final answer, or grading result in D1/D2
- skip completed agent/grading steps by default; overwrite only explicitly
- keep OpenCode and Codex as separate measurement lanes
- sanitized single-commit workspace checkout
- no OpenCode subagents inside proof runs
- no `git log`, `git show`, or `git blame`
- no installs, virtualenvs, `pip`, `uv`, `sudo`, or `pkexec`
- no product platform work unless it directly improves the proof

## Current Follow-Up Setup

The next run uses:

```text
configs/swe-contextbench-followup-gated-slice.json
```

This is a 7-pair diagnostic follow-up, not a new blind aggregate. It removes
the invalid Matplotlib pairs, excludes currently unavailable hardened Docker
images, and adds `d1_applicability` labels for `D1G`.

Preflight status:

```text
scripts/run-swe-contextbench-mini-slice \
  --config configs/swe-contextbench-followup-gated-slice.json \
  --phase preflight \
  --agent-backend codex \
  --preflight-docker local

Result: 7/7 pairs passed.
Artifact root:
/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-followup-gated-slice-codex
```

Agent status:

```text
D0  7/7 agent ok, 0 benchmark-noise patches
D1  7/7 agent ok, 0 benchmark-noise patches
D1G 7/7 agent ok, 0 benchmark-noise patches
D2  7/7 agent ok, 0 benchmark-noise patches
```

Grading status:

The first grading attempt exposed two SWE-ContextBench harness constraints:

- `evaluation.sh` is not safe to run concurrently because it writes shared
  `batch_dataset.json` and `batch_predictions.json` files.
- `run_evaluation` removes the original hardened instance image by default,
  which breaks grading multiple modes for the same instance unless
  `--no-remove-instance-image` is used.

The local runner now serializes grading and calls the official Python modules
with `--no-remove-instance-image`. The 7 hardened images had already been
removed by the earlier grading attempt, and Docker Hub currently returns an
unauthenticated pull rate-limit error. Do not interpret the current official
follow-up totals until images are restored and grading is rerun.

## Active Checklist

- [ ] Restore the 7 follow-up hardened Docker images after Docker Hub rate limit
  reset or after `docker login`.
- [ ] Rerun follow-up official grading with cached agent patches:
  `scripts/run-swe-contextbench-mini-slice --config configs/swe-contextbench-followup-gated-slice.json --phase grade --modes D0,D1,D1G,D2 --agent-backend codex --grading-timeout-seconds 2400 --overwrite`.
- [ ] Summarize the run with `--modes D0,D1,D1G,D2`.
- [ ] Write the next report comparing blind D1 vs gated D1 vs D2, with strict
  clean and official metrics separated.
- [ ] Decide after the report whether a D2 automatic scope gate is worth adding;
  do not implement it before the D1G diagnostic signal is clear.
