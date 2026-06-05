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

### Initial 3-Problem PI Canary

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

### Rootless Cleanup Smoke

```text
run=/home/dev/benchmarks/slopcodebench-runs/smoke-d1-file-backup-bytecode
mode=D1
problem=file_backup
result=checkpoint_1 failed, infra_errors=0, steps=75
```

This confirms that the current rootless cleanup guard removes the previous
Python `__pycache__` cleanup failure on the smoke case.

### Direct Codex Lane Smoke

```text
run=/home/dev/benchmarks/slopcodebench-runs/smoke-d0-codex-cfgpipe
mode=D0
problem=cfgpipe
result=invalid lane
```

The initial Codex command fails with `Permission denied (os error 13)`, and
SlopCodeBench retry/resume uses CLI arguments that are not compatible with the
old Codex image. Treat this as an infra lane issue, not a benchmark result.

### Stronger PI Lane Discovery

`codex_auth/gpt-5.3-codex` is not available through the current ChatGPT Codex
auth path:

```text
run=/home/dev/benchmarks/slopcodebench-runs/smoke-d0-pi-gpt53-cfgpipe-low
mode=D0
problem=cfgpipe
result=invalid model/auth lane
error=The 'gpt-5.3-codex' model is not supported when using Codex with a ChatGPT account.
```

Raising `cfgpipe` from low to medium reasoning with the supported Spark model is
not practical for the smoke lane:

```text
run=/home/dev/benchmarks/slopcodebench-runs/smoke-d0-pi-spark-cfgpipe-medium
mode=D0
problem=cfgpipe
result=checkpoint_1 failed, 33/37 tests, infra_errors=0, steps=49
```

OpenCode is currently blocked by missing local auth:

```text
~/.local/share/opencode/auth.json missing
```

### Accepted XJQ Lane Smoke

The first valid lane is:

```text
agent=pi
model=codex_auth/gpt-5.3-codex-spark
thinking=medium
problem=xjq
run=/home/dev/benchmarks/slopcodebench-runs/smoke-d0-pi-spark-xjq-medium
```

| Mode | Passed | Checkpoints | Infra Errors | Steps |
|---|---:|---:|---:|---:|
| D0 | 1 | 2 | 0 | 174 |
| D1 | 1 | 2 | 0 | 182 |

Checkpoint matrix:

| Mode | Problem | Checkpoint | Passed | Tests | Decisions |
|---|---|---|---:|---:|---:|
| D0 | xjq | checkpoint_1 | True | 23/23 | 0 |
| D0 | xjq | checkpoint_2 | False | 48/51 | 0 |
| D1 | xjq | checkpoint_1 | True | 23/23 | 6 |
| D1 | xjq | checkpoint_2 | False | 46/51 | 0 |

D1 checkpoint 2 received a non-empty Decision Brief from checkpoint 1:

```text
decision_layer/prompt_decisions/checkpoint_2.json = 6 decisions
```

This proves the SlopCodeBench D1 pipeline works end to end on at least one
external coding problem. It is not yet positive Decision Layer evidence because
D1 underperformed D0 on checkpoint 2.

## Interpretation

- The SlopCodeBench integration is valid enough to run a real D0/D1 canary:
  agents write into `/workspace`, snapshots contain solution files, rootless
  cleanup is fixed, and D1 prompt enrichment is visible in later checkpoints.
- The old PI + Spark low canary was too weak because no problem passed
  checkpoint 1.
- `xjq` with PI + Spark medium is a usable anchor problem for the next canary.
- The first D1 smoke did not improve results, so the next canary is for signal
  collection and regression classification, not for claiming value.

## Active Checklist

- [x] Pin SlopCodeBench runner and problem repository commits.
- [x] Add thin D0/D1 wrapper around the external SlopCodeBench CLI.
- [x] Add deterministic Decision Brief injection for D1.
- [x] Add rootless Docker workspace write guard.
- [x] Verify rootless cleanup smoke: D1 `file_backup`, `infra_errors=0`.
- [x] Test direct Codex lane smoke and classify it as invalid for now.
- [x] Commit the rootless cleanup fix once the diff is cleaned up.
- [x] Test stronger PI options on `cfgpipe` and classify them:
  full `gpt-5.3-codex` is unsupported through current auth, Spark medium is too
  slow and still fails checkpoint 1.
- [x] Check OpenCode lane availability; it is blocked by missing OpenCode auth.
- [x] Find a valid D0 agent lane before any larger D0/D1 run.
- [x] Accept a lane where D0 passes checkpoint 1 and reaches a later checkpoint:
  PI + `codex_auth/gpt-5.3-codex-spark` + medium on `xjq`.
- [x] Verify that a later D1 checkpoint has non-empty
  `decision_layer/prompt_decisions`.
- [x] Record the chosen lane in config: agent, model, reasoning, problem slice,
  pass policy, runner commit, problems commit, and output root.
- [ ] Run the updated 3-problem D0/D1 canary:
  `xjq`, `l2m`, `etl_pipeline`.
- [ ] Manually inspect every D0/D1 delta and classify it as useful Decision
  Layer signal, variance, wrong transfer, or infra noise.
- [ ] Proceed to a 10-problem pilot only if the canary has at least one
  attributable D1-only win or regression-prevention case with no systematic D1
  harm.
- [ ] Write `reports/slopcodebench-d0-d1-pilot.md` only after a valid pilot.

## Next Run Plan

1. Run `configs/slopcodebench-canary.json` with overwrite.
2. Confirm every D1 checkpoint after an accepted prior checkpoint has non-empty
   `decision_layer/prompt_decisions`.
3. Compare D0/D1 deltas by checkpoint.
4. If D1 loses, inspect whether the brief was too broad, incomplete, or simply
   noise from agent variance.
5. If at least one D1-only win or regression-prevention case appears without
   systematic harm, prepare the 10-problem pilot.

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
