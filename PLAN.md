# Decision Layer Overnight Run Plan

## Goal

Prepare a reproducible overnight LongMemEval-V2 run that expands the first POC
without weakening the proof.

The run should compare the same local reader in three modes:

- `D0`: baseline context only.
- `D1`: baseline context plus audited oracle Decision Briefs.
- `D2`: baseline context plus automatic Decision Briefs.

Decision Briefs can contain accepted decisions, explicit requirements,
constraints, and procedures. They should not contain plain environment facts or
UI state.

## Scope

- [x] Use LongMemEval-V2 only; do not introduce a custom proof benchmark.
- [x] Prepare the full deterministic all-topics run as the main overnight
  profile.
- [x] Exclude `llm_abstention_checker` and `llm_gotchas_checker` questions for
  the overnight run unless an evaluator backend is added first.
- [x] Treat all deterministic scorable LongMemEval-V2 questions as the default
  overnight target: currently 295 questions.
- [x] Cover all deterministic question types: `static-environment`,
  `dynamic-environment`, `procedure`, and the single deterministic
  `errors-gotchas` case.
- [x] Expected deterministic counts: 134 `static-environment`, 86
  `dynamic-environment`, 74 `procedure`, and 1 `errors-gotchas`.
- [x] Keep judge-only question types as a later profile, because they are not
  proof-ready until evaluator support exists.
- [x] Keep all generated run artifacts outside stable POC artifacts, preferably
  in a timestamped `/tmp/decision-layer-overnight-*` directory.

## Data Preparation

- [x] Create `configs/longmemeval-v2-full-deterministic-subset.txt` with all
  deterministic scorable question IDs.
- [x] Create `configs/longmemeval-v2-canary-deterministic-subset.txt` from the
  full deterministic subset.
- [x] Include the 3 already verified POC question IDs as sanity cases.
- [x] Include at least one canary case from each deterministic question type
  where available.
- [x] Keep the full deterministic subset fixed before canary and overnight runs.

## D1 Preparation

- [x] Generate a draft D1 decision file from the selected questions and
  trajectories.
- [x] Store the draft outside final config, for example in
  `/tmp/decision-layer-d1-draft.json`.
- [x] Review the generated D1 draft for launch readiness.
- [x] Reject broad automatic acceptance of candidates that look like answer keys,
  environment facts, weak guesses, or long action-count answers.
- [x] Allow an empty D1 entry for questions where the evidence is factual memory,
  not a decision, commitment, constraint, or procedure.
- [x] Treat explicit requirements and constraints as accepted commitments, while
  still rejecting plain facts, UI state, and one-off information needs.
- [x] Write accepted oracle decisions to
  `configs/longmemeval-v2-full-deterministic-oracle-decisions.json`.
- [x] Write an initial D2 audit allowlist to
  `configs/longmemeval-v2-full-deterministic-accepted-d2-decisions.json`.
- [x] Add the canary D1 requirement label for `07ffeedf` so D1 measures the
  useful upper bound and D2 exposes the extractor gap.

## Canary Gate

- [x] Create a canary subset with 13 IDs from the full deterministic subset.
- [x] Run the canary through `D0`, `D1`, and `D2` using the local llama.cpp
  reader.
- [x] Confirm the run writes `suite_metrics.json`, `report.md`,
  `predictions.jsonl`, `decision_trace.jsonl`, and `brief_trace.jsonl`.
- [x] Check that `D1` Decision Briefs are non-empty on cases with accepted oracle
  decisions.
- [x] Check that `D2` does not create obvious false decisions.
- [x] Check cases where `D1` or `D2` is worse than `D0` before starting the full
  deterministic overnight run.
- [x] Estimate overnight wall-clock time from the measured canary runtime.
- [x] Include an oversized-context canary case so the gate catches local reader
  context-window failures before the full run.

## Full Overnight Run

- [x] Add one command/script for the full deterministic overnight run so the
  operator only needs to start it.
- [x] Make the command run the canary first and stop if the canary fails.
- [x] Use a timestamped output directory.
- [x] Tee stdout/stderr to a log file in the same output directory.
- [x] Make the script run all 295 deterministic scorable questions in `D0`,
  `D1`, and `D2`.
- [x] Cap retrieved context with `CONTEXT_MAX_CHARS` so full runs stay inside the
  local reader context window.
- [x] Resume incomplete benchmark runs by default and cache reader responses by
  request hash; use `OVERWRITE=1` / `--no-resume` for a clean rerun.
- [x] Save all traces and reports for morning audit.

## Manual Launch

- [x] Use this command for the real overnight run:

```bash
scripts/run-overnight-poc
```

- [x] Use this command to re-run only the canary gate:

```bash
CANARY_ONLY=1 scripts/run-overnight-poc
```

- [x] The full run artifacts will be under
  `/tmp/decision-layer-overnight-*/full`.
- [x] The script prints the exact output directory and writes
  `/tmp/decision-layer-overnight-*/run.log`.

## Runtime Estimate

Current measured speed on the local llama.cpp reader:

```text
3 questions x D0/D1/D2 ~= 3.1-3.3 minutes
1 question x D0/D1/D2 ~= 60-65 seconds
```

Measured all-topic canary:

- [x] 12 question canary: about 9.1 minutes for `D0` + `D1` + `D2`.
- [x] Canary evidence:
  `/tmp/decision-layer-overnight-canary-d1-expanded/canary/canary_gate.json`.
- [x] Latest canary result: `D0=0.083333`, `D1=0.416667`,
  `D2=0.333333`, `D2_false_decision_rate=0.0`, `D2_decision_recall=0.75`.

Approximate wall-clock estimates:

- [x] full 295-question deterministic all-topics overnight run: 4-5 hours based
  on the measured canary.
- [x] full 74-question deterministic `procedure` overnight run: 80-100 minutes.
- [x] all 451 LongMemEval-V2 questions without judge support: 8-10 hours, but
  not proof-ready until evaluator support exists.

These are estimates for the current local server configuration. The canary
runtime is the source of truth before leaving the machine overnight.

## Morning Audit

- [ ] Compare `D1-D0` and `D2-D0` overall.
- [ ] Compare deltas by question type.
- [ ] Review false decision rate and missing expected decisions.
- [ ] Inspect all cases where `D2` is worse than `D0`.
- [ ] Inspect the longest Decision Briefs.
- [ ] Decide whether the next step is larger coverage, better extraction, or a
  stronger reader/backend.
