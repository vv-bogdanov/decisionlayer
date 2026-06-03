# Decision Layer Next Run Plan

## Current Context

Full deterministic LongMemEval-V2 run artifacts:

```text
/tmp/decision-layer-overnight-20260603212552/full
```

Current result is useful as a pipeline and baseline check, but not as a full
Decision Layer proof. The current D1 oracle contains only a few accepted
commitments, so D1 is not yet a real upper bound.

Key current metrics:

| Mode | Correct | Accuracy | Non-empty Briefs |
| --- | ---: | ---: | ---: |
| D0 | 21/295 | 0.071186 | 0 |
| D1 | 24/295 | 0.081356 | 4 |
| D2 | 25/295 | 0.084746 | 6 |

Main signal: `procedure` improved from `1/74` in D0 to `6/74` in D2, but this
is based on sparse commitment coverage.

Decision Briefs should contain only accepted decisions, explicit requirements,
constraints, procedures, and stable operating rules. They should not contain
plain environment facts, UI state, answer keys, or transient observations.

## Active Checklist

- [ ] Fix the final shell quoting error in `scripts/run-overnight-poc`:
  `unexpected EOF while looking for matching "`.
- [ ] Add streaming artifacts during benchmark runs so each completed example is
  saved immediately, not only at the end of a full mode.
- [ ] Write `metrics.partial.json` during long runs so progress can be inspected
  while the benchmark is still running.
- [ ] Keep resume/cache as the default behavior; keep `OVERWRITE=1` /
  `--no-resume` as the explicit clean-rerun path.
- [ ] Prepare a cheap blind D1 labeling input that hides final `question`,
  `answer`, and `eval_function`.
- [ ] Run subagent draft labeling in small chunks with low/medium reasoning.
- [ ] Extract only commitment-like statements from trajectories: decisions,
  requirements, constraints, procedures, stable operating rules, and gotchas as
  rules.
- [ ] Audit the subagent draft manually: remove facts, answer-like statements,
  UI state, long observations, weak guesses, and duplicates.
- [ ] Save the audited blind oracle as
  `configs/longmemeval-v2-full-blind-oracle-decisions.json`.
- [ ] Run D1-only with the blind oracle and the same local reader/settings.
- [ ] Compare blind D1 against the existing D0 baseline from
  `/tmp/decision-layer-overnight-20260603212552/full/D0`.
- [ ] Inspect D1 regressions where D0 was correct but D1 was wrong.
- [ ] Inspect cases with non-empty Decision Briefs where D1 still failed.
- [ ] Use the blind D1 oracle as the gold target for D2 extraction audit.
- [ ] Run D2 against the blind oracle after the D1 ceiling is established.
- [ ] Improve the extractor using concrete D2 missing-decision cases.
- [ ] Re-run D2 and track `decision_recall`, `false_decision_rate`, `D2-D1 gap`,
  and `procedure D2-D0`.

## Next D1 Command

After the blind oracle is ready:

```bash
uv run decision-layer run-poc \
  --data-root data/longmemeval-v2 \
  --output-dir /tmp/decision-layer-d1-blind-full \
  --mode D1 \
  --tier small \
  --question-id-file configs/longmemeval-v2-full-deterministic-subset.txt \
  --reader openai-chat \
  --reader-base-url http://127.0.0.1:18080/v1 \
  --reader-model qwen36-35b-a3b-udiq3s \
  --reader-max-tokens 128 \
  --context-max-chars 96000 \
  --oracle-decisions configs/longmemeval-v2-full-blind-oracle-decisions.json
```
