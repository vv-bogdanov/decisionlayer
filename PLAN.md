# Current Plan: SlopCodeBench Agent-Lane Validation

## Goal

Use SlopCodeBench as the next external coding benchmark for the POC.

The only proof that matters here is still:

```text
D0 = same agent/backend/model without Decision Brief
D1 = same agent/backend/model with Decision Brief from prior accepted checkpoints
```

Decision Layer value can only be claimed when D1 receives decisions extracted
from earlier accepted checkpoints. A run where checkpoint 1 never passes is not
a Decision Layer test; it is an agent/benchmark fit test.

## Fixed Inputs

Pinned benchmark sources:

```text
runner=/home/dev/benchmarks/slop-code-bench @ 0a2e7bec9827a1c09c53beb8d76d854ea3c4befc
problems=/home/dev/benchmarks/scb-problems @ ef6a9dd13911566b6b01075ca121758c9f7b5c5f
```

Current wrapper and configs:

```text
runner script=configs + scripts/run-slopcodebench-d0-d1
environment=configs/slopcodebench-docker-python3.12-uv-rootless.yaml
prompt=configs/slopcodebench-just-solve-workspace.jinja
canary=configs/slopcodebench-canary.json
pilot=configs/slopcodebench-pilot.json
pass_policy=all-cases
```

## Current Evidence

Initial 3-problem PI canary:

```text
run=/home/dev/benchmarks/slopcodebench-runs/canary-d0-d1
agent=pi
model=codex_auth/gpt-5.3-codex-spark
thinking=low
problems=file_backup,cfgpipe,etl_pipeline
```

| Mode | Passed | Checkpoints | Infra Errors | Steps |
|---|---:|---:|---:|---:|
| D0 | 0 | 3 | 0 | 110 |
| D1 | 0 | 3 | 2 | 145 |

Checkpoint matrix:

| Mode | Problem | Checkpoint | Passed | Tests | Decisions |
|---|---|---|---:|---:|---:|
| D0 | cfgpipe | checkpoint_1 | False | 36/37 | 0 |
| D0 | etl_pipeline | checkpoint_1 | False | 30/41 | 0 |
| D0 | file_backup | checkpoint_1 | False | 21/32 | 0 |
| D1 | cfgpipe | checkpoint_1 | False | 33/37 | 0 |
| D1 | etl_pipeline | checkpoint_1 | False | 35/41 | 0 |
| D1 | file_backup | checkpoint_1 | False | 21/32 | 0 |

Rootless cleanup smoke:

```text
run=/home/dev/benchmarks/slopcodebench-runs/smoke-d1-file-backup-bytecode
mode=D1
problem=file_backup
result=checkpoint_1 failed, infra_errors=0, steps=75
```

This confirms that the current rootless cleanup guard removes the previous
Python `__pycache__` cleanup failure on the smoke case.

Direct Codex lane smoke:

```text
run=/home/dev/benchmarks/slopcodebench-runs/smoke-d0-codex-cfgpipe
mode=D0
problem=cfgpipe
result=invalid lane
```

The initial Codex command fails with `Permission denied (os error 13)`, and
SlopCodeBench retry/resume uses CLI arguments that are not compatible with the
old Codex image. Treat this as an infra lane issue, not a benchmark result.

## Interpretation

- The SlopCodeBench integration is close enough to continue lane discovery:
  agents can write to `/workspace`, snapshots contain solution files, and the
  rootless cleanup noise is fixed on a smoke run.
- The current PI + `gpt-5.3-codex-spark` lane is too weak for the selected
  canary: D0 does not pass any first checkpoint.
- D1 currently receives zero decisions because no prior checkpoint is accepted.
- Bigger D0/D1 runs are not useful until D0 can pass checkpoint 1 on at least
  one selected problem.

## Active Checklist

- [x] Pin SlopCodeBench runner and problem repository commits.
- [x] Add thin D0/D1 wrapper around the external SlopCodeBench CLI.
- [x] Add deterministic Decision Brief injection for D1.
- [x] Add rootless Docker workspace write guard.
- [x] Verify rootless cleanup smoke: D1 `file_backup`, `infra_errors=0`.
- [x] Test direct Codex lane smoke and classify it as invalid for now.
- [ ] Commit the rootless cleanup fix once the diff is cleaned up.
- [ ] Find a valid D0 agent lane before any larger D0/D1 run.
- [ ] First try PI with a stronger Codex model or slightly higher reasoning on
  the near-miss problem `cfgpipe`.
- [ ] If PI still fails checkpoint 1, try OpenCode with the same backend/model.
- [ ] If OpenCode is blocked by auth or tooling, try Hermes/local llama.cpp only
  as a lane-discovery fallback.
- [ ] Accept a lane only if D0 passes checkpoint 1 on at least one small problem
  and reaches a later checkpoint where D1 can carry decisions.
- [ ] Record the chosen lane in config: agent, model, reasoning, timeout,
  problem slice, pass policy, runner commit, problems commit, and output root.
- [ ] Run a new 3-problem D0/D1 canary only after the D0 lane is valid.
- [ ] Verify that later D1 checkpoints have non-empty
  `decision_layer/prompt_decisions`.
- [ ] Manually inspect every D0/D1 delta and classify it as useful Decision
  Layer signal, variance, wrong transfer, or infra noise.
- [ ] Proceed to a 10-problem pilot only if the canary has at least one
  attributable D1-only win or regression-prevention case with no systematic D1
  harm.
- [ ] Write `reports/slopcodebench-d0-d1-pilot.md` only after a valid pilot.

## Next Run Plan

1. Clean the SlopCodeBench patch diff so only useful POC code remains.
2. Rerun unit checks for the SlopCodeBench patch and summary code.
3. Run D0-only smoke on `cfgpipe` with PI and a stronger lane:
   `codex_auth/gpt-5.3-codex`, starting with low reasoning.
4. If checkpoint 1 still fails, run one more D0-only smoke with the same model
   and medium reasoning.
5. If PI remains below the threshold, run an OpenCode D0-only smoke on `cfgpipe`
   using the same backend/model if auth is available.
6. Freeze the first lane that passes checkpoint 1 and rerun a 3-problem D0/D1
   canary.

## Stop Criteria

Stop SlopCodeBench work and choose another benchmark or task slice if:

- no practical agent lane can pass checkpoint 1 on small problems;
- D1 repeatedly receives empty briefs because no accepted prior checkpoints
  exist;
- runtime is dominated by agent hangs or tool-loop variance;
- rootless Docker cleanup errors return after the cleanup guard;
- D1 regressions are caused by wrong or over-broad decisions.

## Implementation Notes

Keep the integration thin:

- use SlopCodeBench's CLI and output format;
- wrap commands instead of forking the benchmark;
- keep Decision Brief extraction deterministic and conservative;
- cache completed checkpoints by default and require explicit overwrite;
- log enough per checkpoint to debug overnight runs;
- do not add REST APIs, UI, vector DBs, graph memory, rerankers, or custom
  benchmarks for this POC.

The next useful result is not a bigger run. It is a clean agent lane where D0
can advance far enough for D1 to carry accepted decisions into later
checkpoints.
