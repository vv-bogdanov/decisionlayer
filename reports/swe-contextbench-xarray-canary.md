# SWE-ContextBench Xarray Canary

Date: 2026-06-04

## Summary

Replacement canary pair:

- Related task: `pydata__xarray-4141`
- Base experience task: `pydata__xarray-4687`
- Relationship: both are about preserving attrs in global `xr.where`.

The official harness is reproducible and the related task is solvable. Standard
D1 and D2 briefs did not resolve the case, even though they contained the
semantic decision that attrs must come from `x`. A post-hoc diagnostic with an
operational implementation decision did resolve the case.

This is not clean benchmark evidence for Decision Layer yet, because the
operational diagnostic was run after inspecting the failed results. It is useful
design evidence: our current Decision Brief format is too lossy for coding
tasks. For coding, the layer must preserve compact implementation decisions, not
only high-level requirements.

## Artifacts

All generated repositories, logs, predictions, and official reports are outside
this repository:

```text
/home/dev/benchmarks/swe-contextbench/agent-runs/pydata__xarray-4141
/home/dev/benchmarks/swe-contextbench/SWEContextBench/predictions
/home/dev/benchmarks/swe-contextbench/SWEContextBench/logs/run_evaluation
```

Representative run artifacts:

```text
briefs/d1_manual_decision_brief.md
briefs/d2_auto_decision_brief.md
prompts/d0_task.md
prompts/d1_task.md
prompts/d2_task.md
prompts/d1_operational_task.md
logs/d0_guarded_opencode.jsonl
logs/d1_guarded_opencode.jsonl
logs/d2_guarded_opencode.jsonl
logs/d1_operational_opencode.jsonl
logs/*_grading.log
```

Command safety:

- Runs used `opencode run --format json` for structured event logs.
- Runs used wall-clock logs through `/usr/bin/time`.
- A local `guard-bin` wrapper blocked `pip`, `apt`, `sudo`, `pkexec`, `npm`,
  `brew`, and `curl`.
- `PIP_REQUIRE_VIRTUALENV=1` and `PYTHONNOUSERSITE=1` were set for guarded agent
  runs.

Caveat: one invalid early D0 retry violated the prompt and ran `pip3 install`
before the guard wrapper was added. That run is not counted. Later guarded runs
used `PYTHONNOUSERSITE=1`, so the agent did not benefit from that accidental
host user-site install.

## Decision Briefs

D1 manual brief, written from base artifacts before grading the related task:

```text
- xr.where(cond, x, y) should preserve attrs through the same keep_attrs policy used by xarray computation helpers.
- Add a keep_attrs argument to global xr.where; when omitted, resolve it with xarray's global keep_attrs option.
- When keep_attrs is True, global xr.where should keep attrs from x, matching DataArray.where and Dataset.where.
- Pass the resolved keep_attrs value through to the underlying apply_ufunc call instead of dropping attrs at the wrapper.
```

D2 automatic brief from direct llama.cpp extraction:

```text
- Add keep_attrs parameter to xr.where to control attribute preservation
- Default keep_attrs behavior should respect global OPTIONS["keep_attrs"] setting
- When keep_attrs is True, preserve attributes from the second argument (x) to match DataArray.where behavior
- Pass keep_attrs to apply_ufunc to enable attribute propagation
```

Both were compact and materially correct at the semantic level. Both were still
too weak for the local agent: it implemented `keep_attrs=keep_attrs` but missed
the required callable conversion for `keep_attrs is True`.

The operational diagnostic added this implementation decision:

```text
When keep_attrs is True, convert it before calling apply_ufunc into a callable
that selects attrs from the second xarray input, x, not from cond.
```

That diagnostic prompt is post-hoc for this canary and is not counted as clean
D1 proof.

## Results

| Mode | Patch | Resolved | F2P | P2P | Notes |
| --- | --- | --- | --- | --- | --- |
| Gold preflight | official patch | yes | 1/1 | 150/150 | Harness sanity check passed. |
| D0 guarded | no valid patch | no | n/a | n/a | Agent stalled; empty fallback report says no patch found. |
| D1 guarded | add parameter/pass `keep_attrs` | no | 0/1 | 150/150 | Missed `keep_attrs is True -> attrs[1]` callable. |
| D2 guarded | add default policy/pass `keep_attrs` | no | 0/1 | 150/150 | Extractor captured semantic decision, but agent lost the operational detail. |
| D1 operational diagnostic | callable selects `attrs[1]` | yes | 1/1 | 150/150 | Post-hoc diagnostic, not clean proof. |

Timing:

```text
D0 guarded agent: manually stopped after stalling; exact time was not captured
D0 empty fallback grading: 0.56s
D1 guarded agent: 115.08s
D2 guarded agent: 106.27s
D1 operational diagnostic agent: 93.40s
D1 grading: 24.28s
D2 grading: 23.52s
D1 operational diagnostic grading: 24.01s
```

## Diagnosis

The current format loses critical implementation decisions. The phrase "preserve
attrs from x" is correct, but in xarray's local API it must be implemented by
turning `keep_attrs=True` into a callable selecting `attrs[1]`. Passing
`keep_attrs=True` through looks plausible but preserves attrs from the wrong
input path.

This is exactly the kind of detail a coding-oriented Decision Layer should keep:

- not a full patch;
- not raw history;
- not hidden test information;
- but a compact accepted implementation commitment.

The D2 extractor actually saw the base accepted patch in its allowed source, but
compressed away the callable/index detail. That is a concrete extractor failure.

## Policy Decision

Accepted diagnostic observations can be stored only when their authority comes
from the base task's accepted solution, explicit user instruction, or a trusted
manual API/tool call. Post-hoc related-task failures can be used for local
diagnosis and report writing, but not as Decision Brief content for proof.

## Recommendation

Do not start the 5-pair mini-slice yet.

Next step:

1. Define `Operational Decision Brief v0`: compact bullets that preserve
   implementation-critical operator choices, argument mapping, invariants, and
   failure-derived constraints when they are authorized by the base task.
2. Update the D2 extractor prompt/schema so it keeps those details instead of
   summarizing them away.
3. Run a fresh one-pair canary with the revised policy. The xarray pair can
   remain a regression/diagnostic fixture, but it should not be reused as clean
   proof after this post-hoc analysis.
