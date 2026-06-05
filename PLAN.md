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

### Updated 3-Problem Canary

```text
run=/home/dev/benchmarks/slopcodebench-runs/canary-xjq-lane-d0-d1
agent=pi
model=codex_auth/gpt-5.3-codex-spark
thinking=medium
problems=xjq,l2m,etl_pipeline
```

| Mode | Passed | Checkpoints | Infra Errors | Steps |
|---|---:|---:|---:|---:|
| D0 | 0 | 3 | 0 | 186 |
| D1 | 1 | 4 | 0 | 327 |

Checkpoint matrix:

| Mode | Problem | Checkpoint | Passed | Tests | Decisions |
|---|---|---|---:|---:|---:|
| D0 | etl_pipeline | checkpoint_1 | False | 26/41 | 0 |
| D0 | l2m | checkpoint_1 | False | 32/52 | 0 |
| D0 | xjq | checkpoint_1 | False | 22/23 | 0 |
| D1 | etl_pipeline | checkpoint_1 | False | 35/41 | 0 |
| D1 | l2m | checkpoint_1 | False | 39/52 | 0 |
| D1 | xjq | checkpoint_1 | True | 23/23 | 6 |
| D1 | xjq | checkpoint_2 | False | 47/51 | 0 |

Delta classification:

- `xjq` checkpoint 1 D1-only pass is variance, not memory signal. Checkpoint 1
  has no prior decisions in the prompt.
- `l2m` and `etl_pipeline` D1 improved pass rate on checkpoint 1, but those are
  also no-memory checkpoints and cannot prove Decision Layer value.
- `xjq` checkpoint 2 is the only memory-exposed checkpoint in this canary. It
  received 6 decisions from checkpoint 1 and still failed.
- The canary gives no positive Decision Layer evidence and shows high agent
  variance around first-checkpoint acceptance.

### XJQ Repeat Variance Check

```text
runs=/home/dev/benchmarks/slopcodebench-runs/repeat-xjq-medium-r{1,2,3}
agent=pi
model=codex_auth/gpt-5.3-codex-spark
thinking=medium
problem=xjq
```

| Repeat | Mode | Checkpoint | Passed | Tests | Steps | Memory-Exposed |
|---|---|---|---:|---:|---:|---:|
| r1 | D0 | checkpoint_1 | True | 23/23 | 148 | No |
| r1 | D0 | checkpoint_2 | False | 46/51 | 117 | No |
| r1 | D1 | checkpoint_1 | False | 22/23 | 63 | No |
| r2 | D0 | checkpoint_1 | True | 23/23 | 57 | No |
| r2 | D0 | checkpoint_2 | False | 45/51 | 83 | No |
| r2 | D1 | checkpoint_1 | True | 23/23 | 59 | No |
| r2 | D1 | checkpoint_2 | False | 47/51 | 125 | Yes |
| r3 | D0 | checkpoint_1 | True | 23/23 | 131 | No |
| r3 | D0 | checkpoint_2 | False | 46/51 | 79 | No |
| r3 | D1 | checkpoint_1 | False | 22/23 | 49 | No |

Repeat interpretation:

- D0 reached checkpoint 2 in all three repeats.
- D1 reached checkpoint 2 in only one of three repeats.
- The only memory-exposed paired observation is `r2/checkpoint_2`: D1 scored
  47/51 vs D0 45/51, but both failed.
- This is a weak positive test-count delta, not an accepted checkpoint win.
- The variance is still dominated by checkpoint-1 acceptance, where D1 has no
  prior decisions and therefore cannot prove Decision Layer value.

### Paired XJQ Checkpoint-2 Comparison

```text
run=/home/dev/benchmarks/slopcodebench-runs/paired-xjq-cp2-from-d0r2
base_snapshot=/home/dev/benchmarks/slopcodebench-runs/repeat-xjq-medium-r2/D0/xjq/checkpoint_1
agent=pi
model=codex_auth/gpt-5.3-codex-spark
thinking=medium
problem=xjq
```

Dry-run resume preview confirmed both modes start from `checkpoint_2` with the
same accepted `checkpoint_1` snapshot:

```text
Resume from: checkpoint_2
Completed: checkpoint_1
```

| Mode | Checkpoint | Passed | Tests | Steps | Prompt Decisions |
|---|---|---:|---:|---:|---:|
| D0 | checkpoint_1 | True | 23/23 | 57 | 0 |
| D0 | checkpoint_2 | False | 46/51 | 111 | 0 |
| D1 | checkpoint_1 | True | 23/23 | 57 | 0 |
| D1 | checkpoint_2 | False | 48/51 | 149 | 6 |

Checkpoint-2 pass-count delta:

| Group | D0 | D1 |
|---|---:|---:|
| checkpoint_1-Regression | 22/23 | 23/23 |
| checkpoint_2-Functionality | 10/13 | 11/13 |
| checkpoint_2-Error | 2/2 | 2/2 |
| checkpoint_2-Core | 12/13 | 12/13 |

D1 avoided two D0 failures:

- `checkpoint_1-Regression/test_xpath_multiple_xml_nodes_default_to_first_only`
- `checkpoint_2-Functionality/test_css_without_text_returns_only_first_matching_xml_node`

Paired interpretation:

- This is the first controlled positive Decision Layer signal on
  SlopCodeBench: D1 had the same starting snapshot and received 6 prior
  decisions only at checkpoint 2.
- The result is positive but not sufficient for a claim: D1 improved from
  46/51 to 48/51, but checkpoint 2 still failed.
- The strongest signal is regression prevention: D1 preserved one checkpoint-1
  behavior that D0 lost while extending the solution.
- Runtime cost increased in this sample: D1 used 149 checkpoint-2 steps vs D0
  111.

## Interpretation

- The SlopCodeBench integration is valid enough to run a real D0/D1 canary:
  agents write into `/workspace`, snapshots contain solution files, rootless
  cleanup is fixed, and D1 prompt enrichment is visible in later checkpoints.
- The old PI + Spark low canary was too weak because no problem passed
  checkpoint 1.
- `xjq` with PI + Spark medium can pass checkpoint 1, but it is not stable
  enough to support a single-run D0/D1 claim.
- Repeated `xjq` confirms that uncontrolled D0/D1 launches are too noisy:
  checkpoint-1 acceptance variance hides the actual layer effect.
- The initial canary evidence did not justify a 10-problem pilot by itself.
- A single paired checkpoint-2 run now justifies an exploratory pilot, but not a
  publication claim.
- The next experiment should check whether the positive controlled signal
  survives more problems or more paired checkpoint-2 samples.

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
- [x] Run the updated 3-problem D0/D1 canary:
  `xjq`, `l2m`, `etl_pipeline`.
- [x] Manually inspect every current canary D0/D1 delta and classify it.
- [x] Run repeated `xjq` D0/D1 checks and classify checkpoint-level variance.
- [x] Design the next variance-controlled `xjq` experiment before any pilot.
- [x] Run paired `xjq` checkpoint-2 comparison from an identical accepted
  checkpoint-1 snapshot.
- [x] Check the pilot gate: paired `xjq` has a D1 regression-prevention case
  with no infra errors and no observed pass-count harm in this sample.
- [ ] Run an exploratory 10-problem SlopCodeBench pilot with the current PI +
  Spark medium lane.
- [ ] Write `reports/slopcodebench-d0-d1-pilot.md` only after a valid pilot.

## Next Run Plan

1. Run the current 10-problem pilot as exploratory, not as final proof.
2. Keep the lane fixed:
   PI + `codex_auth/gpt-5.3-codex-spark` + medium + `all-cases`.
3. Classify only memory-exposed D1 checkpoints as Decision Layer evidence.
4. Treat checkpoint-1 deltas as agent variance because no prior decisions are
   available there.
5. After the pilot, write `reports/slopcodebench-d0-d1-pilot.md` with:
   setup, pinned commits, per-checkpoint matrix, prompt-decision counts,
   D1-only wins/regressions, runtime cost, and a clear claim/no-claim verdict.

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
