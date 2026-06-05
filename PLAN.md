# Current Plan: SlopCodeBench Decision Layer Pilot

## Goal

Run a focused SlopCodeBench proof to test whether the Decision Layer helps an
agent work longer on iterative coding tasks.

The claim to test is narrower than "memory improves agents":

```text
When a coding task evolves through multiple checkpoints, carrying forward
accepted goals, commitments, and constraints should improve checkpoint progress,
reduce regressions, or reduce code erosion versus the same agent without a
Decision Brief.
```

This remains a POC. Do not build REST APIs, UI, production storage, vector DBs,
graph memory, custom judges, or a custom benchmark unless directly needed for
this proof.

## Why SlopCodeBench

SWE-ContextBench gave a clean but neutral publishable headline:

```text
D0  9/17
D1G 9/17
infra_errors=0
benchmark_noise=0
```

The strongest conclusion from that run is that prompt-level decision injection
is not reliably better on mixed one-shot issue fixing. SlopCodeBench is a better
fit for the main hypothesis because it evaluates iterative specification
refinement: an agent implements checkpoint 1, then extends its own code through
later checkpoints. Early design decisions become real constraints on future
work.

Use SWE-ContextBench only as a regression/canary lane for exact transfer. The
next primary proof lane is SlopCodeBench.

## Benchmark Source

Target benchmark:

```text
runner=https://github.com/SprocketLab/slop-code-bench
problems=https://github.com/gabeorlanski/scb-problems
site=https://www.scbench.ai/
```

Relevant benchmark properties:

- iterative multi-checkpoint problems
- black-box CLI/API contracts, with no prescribed internal architecture
- correctness via pytest-based checkpoint tests
- regression tests from prior checkpoints
- optional erosion and verbosity metrics
- supported agents include Codex, OpenCode, Claude Code, MiniSWE, and Gemini

## Experimental Lanes

Use the same backend, model, reasoning effort, timeout, runner version, problem
set, and checkpoint budget inside each comparison.

```text
D0 = baseline agent, no Decision Brief
D1 = same agent + Decision Brief from prior accepted checkpoints
```

D1 decision source rules:

- checkpoint specs are authoritative input
- a checkpoint can update active decisions only after its solution passes the
  benchmark pass policy
- extract only goals, commitments, and constraints
- do not extract ordinary facts, docs, tool output, raw assistant messages, or
  unaccepted implementation guesses
- prefer skipping an uncertain decision over creating a false decision
- one decision must be one short statement

Initial D1 delivery can be prompt-level injection. Do not build a new memory
system first.

## Metrics

Primary metrics:

- checkpoints passed
- end-to-end problems solved
- regressions against prior checkpoints
- D1-only and D0-only deltas

Secondary metrics:

- erosion score
- verbosity score
- lines changed per checkpoint
- cost, time, and token usage
- patch/application failures
- infrastructure failures

Interpretation rules:

- D1 wins only count as Decision Layer signal if the relevant decision was
  present before the winning checkpoint
- skip/no-brief checkpoints must not be counted as memory value
- regressions matter as much as forward progress
- quality metrics are supporting evidence, not a replacement for correctness

## Active Checklist

- [x] Clone/pin SlopCodeBench runner and problem repos under
  `/home/dev/benchmarks`.
- [x] Run local preflight: `uv sync`, Docker check, one reference-test check,
  and SlopCodeBench agent config dry-run.
- [x] Inspect available agents and choose the first practical lane:
  prefer Codex with low reasoning; try OpenCode/local agent only if setup is
  clean.
- [x] Select a small canary slice of 3 problems with 3-6 checkpoints each.
- [x] Predeclare canary config: problems, agent, model, reasoning, timeout,
  pass policy, and output root.
- [x] Implement the minimal wrapper needed to run `D0` and `D1` with resume,
  per-checkpoint logs, and per-checkpoint result files.
- [x] Implement minimal Decision Brief generation for D1 from prior accepted
  checkpoints only.
- [ ] Run canary: `D0` and `D1` on the same selected problems.
- [ ] Generate a canary summary with checkpoint matrix, regressions, D1-only,
  D0-only, erosion/verbosity if available, cost/time/tokens, and infra errors.
- [ ] Manually inspect every delta case and classify it as useful signal,
  variance, wrong transfer, or infra noise.
- [ ] Decide stop/go for a larger pilot.
- [ ] If canary passes stop/go, run a 10-problem pilot with the same protocol.
- [ ] Write `reports/slopcodebench-d0-d1-pilot.md`.

## Stop/Go Criteria

Stop and rethink if any of these happen:

- runner or Docker infra is unstable after preflight
- D1 causes repeated wrong-transfer regressions
- D1 decisions cannot be kept short and clearly authorized
- results are dominated by agent variance or patch/application failures

Proceed to a 10-problem pilot if canary shows:

- no systematic D1 harm
- at least one clear D1-only checkpoint or regression-prevention case
- per-checkpoint artifacts are sufficient for manual audit
- runtime is acceptable for an overnight run

Proceed beyond the pilot only if:

- D1 improves checkpoint progress or regressions on the predeclared slice
- wins are attributable to decisions that existed before the relevant checkpoint
- the result remains visible after excluding infra/noise cases

## Expected Artifacts

Repository artifacts:

```text
configs/slopcodebench-docker-python3.12-uv-rootless.yaml
configs/slopcodebench-canary.json
configs/slopcodebench-pilot.json
scripts/run-slopcodebench-d0-d1
scripts/summarize-slopcodebench-run
scripts/slopcodebench_patch/
reports/slopcodebench-d0-d1-pilot.md
```

External benchmark artifacts:

```text
/home/dev/benchmarks/slop-code-bench/
/home/dev/benchmarks/scb-problems/
/home/dev/benchmarks/slopcodebench-runs/
```

Each run should save:

- raw agent logs
- per-checkpoint workspace or patch
- per-checkpoint Decision Brief for D1
- checkpoint test results
- summary JSON/Markdown
- exact git commits for runner and problems

## Implementation Notes

Keep the integration thin:

- prefer SlopCodeBench's existing CLI and output format
- wrap commands instead of forking the benchmark
- add only the minimum adapter needed to inject the Decision Brief
- cache completed checkpoints by default; require an explicit overwrite flag
- log every phase clearly enough to debug overnight runs
- do not add product abstractions around storage, retrieval, or plugins yet

The first useful result is not a full leaderboard. It is a clean, auditable
answer to whether accepted decisions help an agent survive iterative checkpoint
growth.

## Current Run Setup

Pinned sources:

```text
runner=/home/dev/benchmarks/slop-code-bench @ 0a2e7bec9827a1c09c53beb8d76d854ea3c4befc
problems=/home/dev/benchmarks/scb-problems @ ef6a9dd13911566b6b01075ca121758c9f7b5c5f
```

Canary config:

```text
config=configs/slopcodebench-canary.json
problems=file_backup,cfgpipe,etl_pipeline
agent=pi
model=codex_auth/gpt-5.3-codex-spark
thinking=low
pass_policy=all-cases
output_root=/home/dev/benchmarks/slopcodebench-runs/canary-d0-d1
```

Run canary:

```sh
./scripts/run-slopcodebench-d0-d1 --config configs/slopcodebench-canary.json
```

Resume is the default when lane output already has `config.yaml`. Use
`--overwrite` only for an intentional fresh rerun.

Direct SlopCodeBench `codex` agent was rejected during canary preflight because
its retry command is incompatible with the installed Codex CLI
(`codex exec resume` rejects `--skip-git-repo-check`). Use `pi` with the same
`codex_auth/gpt-5.3-codex-spark` backend for the first practical lane.
