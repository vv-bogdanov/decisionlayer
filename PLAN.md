# Current Plan: SlopCodeBench Agent-Lane Validation

## Goal

Use SlopCodeBench to test whether the Decision Layer helps on iterative coding
tasks, but only after the benchmark lane is valid enough to exercise memory.

The proof target is still:

```text
D0 = same agent/backend/model without Decision Brief
D1 = same agent/backend/model with Decision Brief from prior accepted checkpoints
```

Decision Layer value can only be claimed when a D1 checkpoint receives decisions
that were extracted from earlier accepted checkpoints. A run where checkpoint 1
never passes is not a Decision Layer test; it is an agent/benchmark fit test.

## Current Canary Result

Run root:

```text
/home/dev/benchmarks/slopcodebench-runs/canary-d0-d1
```

Pinned benchmark sources:

```text
runner=/home/dev/benchmarks/slop-code-bench @ 0a2e7bec9827a1c09c53beb8d76d854ea3c4befc
problems=/home/dev/benchmarks/scb-problems @ ef6a9dd13911566b6b01075ca121758c9f7b5c5f
```

Canary config:

```text
problems=file_backup,cfgpipe,etl_pipeline
agent=pi
model=codex_auth/gpt-5.3-codex-spark
thinking=low
pass_policy=all-cases
```

Summary after rootless workspace fixes:

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

Interpretation:

- The benchmark integration is now mostly valid: agents write into `/workspace`
  and snapshots contain solution files.
- The current `pi` + `gpt-5.3-codex-spark` lane does not pass any first
  checkpoint on the selected canary.
- D1 received zero decisions because no prior checkpoint was accepted.
- Therefore this canary gives no Decision Layer signal.
- D1 also exposed rootless cleanup noise from Python `__pycache__` files; the
  environment now sets `PYTHONDONTWRITEBYTECODE=1`, but that needs a rerun to
  confirm.

## Active Checklist

- [ ] Rerun a minimal smoke canary with the updated env to confirm that
  `PYTHONDONTWRITEBYTECODE=1` removes rootless cleanup errors.
- [ ] Find a valid agent lane before any larger D0/D1 run:
  test D0-only on a tiny slice until at least one checkpoint 1 passes.
- [ ] Prefer the simplest lane that works:
  first try fixing direct Codex CLI integration or using a stronger Codex model;
  only then try OpenCode, Hermes, PI variants, or local llama.cpp API.
- [ ] Record the chosen lane in config:
  agent, model, reasoning, timeout, problem slice, pass policy, runner commit,
  problems commit, and output root.
- [ ] Run a new 3-problem D0/D1 canary only after D0 passes checkpoint 1 on at
  least one selected problem.
- [ ] Verify that D1 has non-empty `decision_layer/prompt_decisions` for later
  checkpoints before interpreting any D1 result as memory signal.
- [ ] Manually inspect every D0/D1 delta:
  classify it as useful Decision Layer signal, variance, wrong transfer, or
  infra noise.
- [ ] Proceed to a 10-problem pilot only if the canary has at least one
  attributable D1-only win or regression-prevention case with no systematic D1
  harm.
- [ ] Write `reports/slopcodebench-d0-d1-pilot.md` only after a valid pilot.

## Stop Criteria

Stop SlopCodeBench work and choose another benchmark or task slice if:

- no practical agent lane can pass checkpoint 1 on small problems;
- D1 repeatedly receives empty briefs because no accepted prior checkpoints
  exist;
- runtime is dominated by agent hangs or tool-loop variance;
- rootless Docker cleanup errors continue after the bytecode guard;
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

The next useful result is not a bigger run. It is a clean agent lane where D0 can
advance far enough for D1 to carry accepted decisions into later checkpoints.
