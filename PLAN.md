# Decision Layer Overnight Run Plan

## Goal

Prepare a reproducible overnight LongMemEval-V2 run that expands the first POC
without weakening the proof.

The run should compare the same local reader in three modes:

- `D0`: baseline context only.
- `D1`: baseline context plus audited oracle Decision Briefs.
- `D2`: baseline context plus automatic Decision Briefs.

## Scope

- [ ] Use LongMemEval-V2 only; do not introduce a custom proof benchmark.
- [ ] Prepare the full deterministic all-topics run as the main overnight
  profile.
- [ ] Exclude `llm_abstention_checker` and `llm_gotchas_checker` questions for
  the overnight run unless an evaluator backend is added first.
- [ ] Treat all deterministic scorable LongMemEval-V2 questions as the default
  overnight target: currently 295 questions.
- [ ] Cover all deterministic question types: `static-environment`,
  `dynamic-environment`, `procedure`, and the single deterministic
  `errors-gotchas` case.
- [ ] Expected deterministic counts: 134 `static-environment`, 86
  `dynamic-environment`, 74 `procedure`, and 1 `errors-gotchas`.
- [ ] Keep judge-only question types as a later profile, because they are not
  proof-ready until evaluator support exists.
- [ ] Keep all generated run artifacts outside stable POC artifacts, preferably
  in a timestamped `/tmp/decision-layer-overnight-*` directory.

## Data Preparation

- [ ] Create `configs/longmemeval-v2-full-deterministic-subset.txt` with all
  deterministic scorable question IDs.
- [ ] Create `configs/longmemeval-v2-canary-deterministic-subset.txt` from the
  full deterministic subset.
- [ ] Include the 3 already verified POC question IDs as sanity cases.
- [ ] Include at least one canary case from each deterministic question type
  where available.
- [ ] Keep the full deterministic subset fixed before canary and overnight runs.

## D1 Preparation

- [ ] Generate a draft D1 decision file from the selected questions and
  trajectories.
- [ ] Store the draft outside final config, for example in
  `/tmp/decision-layer-d1-draft.json`.
- [ ] Review every candidate manually before accepting it.
- [ ] Reject candidates that are answer keys, environment facts, weak guesses, or
  longer than one short operational statement.
- [ ] Allow an empty D1 entry for questions where the evidence is factual memory,
  not a decision, commitment, constraint, or procedure.
- [ ] Write accepted oracle decisions to
  `configs/longmemeval-v2-full-deterministic-oracle-decisions.json`.
- [ ] Use the same accepted set as the initial D2 audit allowlist in
  `configs/longmemeval-v2-full-deterministic-accepted-d2-decisions.json`.

## Canary Gate

- [ ] Create a canary subset with 8-12 IDs from the full deterministic subset.
- [ ] Run the canary through `D0`, `D1`, and `D2` using the local llama.cpp
  reader.
- [ ] Confirm the run writes `suite_metrics.json`, `report.md`,
  `predictions.jsonl`, `decision_trace.jsonl`, and `brief_trace.jsonl`.
- [ ] Check that `D1` Decision Briefs are non-empty on cases with accepted oracle
  decisions.
- [ ] Check that `D2` does not create obvious false decisions.
- [ ] Check cases where `D1` or `D2` is worse than `D0` before starting the full
  deterministic overnight run.
- [ ] Estimate overnight wall-clock time from the measured canary runtime.

## Full Overnight Run

- [ ] Add one command/script for the full deterministic overnight run so the
  operator only needs to start it.
- [ ] Make the command run the canary first and stop if the canary fails.
- [ ] Use a timestamped output directory.
- [ ] Tee stdout/stderr to a log file in the same output directory.
- [ ] Run all 295 deterministic scorable questions in `D0`, `D1`, and `D2`.
- [ ] Save all traces and reports for morning audit.

## Runtime Estimate

Current measured speed on the local llama.cpp reader:

```text
3 questions x D0/D1/D2 ~= 3.1-3.3 minutes
1 question x D0/D1/D2 ~= 60-65 seconds
```

Approximate wall-clock estimates:

- [ ] 8-12 question canary: 10-15 minutes.
- [ ] full 74-question deterministic `procedure` overnight run: 80-100 minutes.
- [ ] full 295-question deterministic all-topics overnight run: 5-7 hours.
- [ ] all 451 LongMemEval-V2 questions without judge support: 8-10 hours, but
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
