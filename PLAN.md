# Current Plan: Coding Proof Variance And Publishable Lane

## Goal

Turn the current Decision Layer coding evidence into a cleaner proof. The next
objective is not to build more product surface. It is to measure whether
applicability-gated decisions (`D1G`) beat no decisions (`D0`) under the same
backend/model despite agent variance.

This remains a POC. Do not build REST APIs, UI, vector DBs, graph memory,
custom judges, or a custom benchmark unless they are directly needed for the
proof.

## Current Evidence

Completed reports:

```text
reports/swe-contextbench-mini.md
reports/swe-contextbench-large.md
reports/swe-contextbench-followup-gated.md
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

Follow-up gated diagnostic:

```text
config=configs/swe-contextbench-followup-gated-slice.json
artifact_root=/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-followup-gated-slice-codex

D0  1/7
D1  2/7
D1G 3/7
D2  1/7

agent_ok=7/7 for every mode
benchmark-noise patches=0 for every mode
infra_errors=0
```

Important caveat: the follow-up official grading used local images rebuilt with
the official SWE-ContextBench `build_instance.py` module after Docker Hub
rate-limited prebuilt image pulls. Treat it as a diagnostic recovery run, not a
publishable prebuilt-image lane.

## Interpretation

The Decision Layer signal is still plausible, but the latest follow-up exposed
agent variance clearly. On `scikit-learn__scikit-learn-25763`, `D0` and `D1G`
had the same effective prompt because the gate skipped the Decision Brief, but
they produced different outcomes. A small single-run slice is therefore not
enough for a causal claim.

The cleanest positive signal is still exact decision transfer. In
`sympy__sympy-20567`, D1 and D1G solved while D0 and D2 failed. The decision was
short, actionable, and mapped directly to the target failure mode.

D2 should not be the headline lane yet. The extractor often produced reasonable
decisions, but the coding agent misapplied them to the wrong target fix point.
The next D2 work, if any, should be an application guard, not a larger memory
system.

## Proof Rules

Keep these constraints for all next proof runs:

- predeclare the benchmark slice before running agents
- same backend/model/reasoning inside a reported lane
- official SWE-ContextBench Docker grading is the source of truth
- no related hidden patch, hidden tests, final answer, or grading result in D1/D2
- skip completed agent/grading steps by default; overwrite only explicitly
- keep OpenCode and Codex as separate measurement lanes
- sanitized single-commit workspace checkout
- no OpenCode subagents inside proof runs
- no `git log`, `git show`, or `git blame`
- no installs, virtualenvs, `pip`, `uv`, `sudo`, or `pkexec`
- no edits to tests, fixtures, benchmark files, docs, or generated artifacts
- no product platform work unless it directly improves the proof

## Active Checklist

- [ ] Add a minimal repeat-run protocol for the 7-pair follow-up diagnostic:
  separate artifact roots, same config, same backend/model/reasoning, and a
  compact aggregate table by pair and mode.
- [ ] Run repeated `D0` vs `D1G` first; include `D1` and `D2` only if the extra
  cost is useful for diagnosis.
- [ ] Prefer authenticated/prebuilt SWE-ContextBench image pulls for the
  publishable lane. If local rebuilt images are used again, label the run as
  diagnostic only.
- [ ] Summarize repeat results with variance, not just one resolved total.
- [ ] If `D1G` still beats `D0`, prepare the next larger predeclared coding
  slice around `D0` vs `D1G`.
- [ ] If `D2` is revisited, add a narrow application guard that forces extracted
  decisions to map to the target fix point before prompt injection.
