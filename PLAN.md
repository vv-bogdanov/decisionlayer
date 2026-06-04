# Current Plan: SWE-ContextBench Mini-Slice

## Goal

Measure whether Decision Layer helps the same local coding agent/model solve
longer-horizon related coding tasks by reusing compact accepted decisions from
prior work.

This remains a POC. Do not build a product platform, REST API, UI, vector DB,
custom judge, or custom benchmark unless it is directly needed for D0/D1/D2
measurement.

## Benchmark

SWE-ContextBench, Verified subset.

Predeclared mini-slice metadata:

```text
configs/swe-contextbench-mini-slice.json
```

Selected base -> related pairs:

- `sympy__sympy-12419 -> sympy__sympy-12426`
- `matplotlib__matplotlib-24637 -> matplotlib__matplotlib-15087`
- `django__django-11239 -> django__django-28322`
- `django__django-16502 -> django__django-29343`
- `sphinx-doc__sphinx-7440 -> sphinx-doc__sphinx-7418`

## Protocol

For each selected pair:

- D0: related task with the same local agent/model and no Decision Brief.
- D1: related task with a manually reviewed Operational Decision Brief extracted
  only from the base task.
- D2: related task with an automatically extracted Operational Decision Brief
  from the same base-task artifacts.

The related public issue text is visible to all modes equally. The Decision
Brief must not be derived from the related hidden patch, hidden tests, final
answer, or post-hoc grading result.

## Logging and Resume

Each run must save enough state to inspect progress while it is running and
resume after failures:

- per-pair artifact directory under
  `/home/dev/benchmarks/swe-contextbench/agent-runs/mini-slice`
- prompt, brief, patch, JSONL opencode log, stderr, wall-clock time
- progress JSONL events for each agent run
- verifier JSON and audit JSON
- official grading log, timing, and report JSON
- skip completed agent/grading steps by default; use an explicit overwrite flag
  only when intentionally rerunning
- if OpenCode stalls, use `--agent-backend codex` as a separate measurement lane
  under `/home/dev/benchmarks/swe-contextbench/agent-runs/mini-slice-codex`;
  do not mix backends inside one reported D0/D1/D2 comparison

Hard agent rules stay in force:

- sanitized single-commit checkout
- no OpenCode subagents inside proof runs
- no `git log`, `git show`, or `git blame`
- no installs, virtualenvs, `pip`, `uv`, `sudo`, or `pkexec`
- official Docker grading is the source of truth when local deps are missing

## Active Checklist

- [x] Select a predeclared 5-pair SWE-ContextBench mini-slice and save only the
  small selection metadata in this repository.
- [x] Add a minimal resume-aware mini-slice preparation/run script with visible
  progress logging.
- [x] Prepare D1 and D2 Operational Decision Briefs for all five pairs from
  base-task artifacts only.
- [ ] Run the 5-pair D0/D1/D2 mini-slice with resume/cache so completed pairs
  are not rerun after failures.
- [ ] Write `reports/swe-contextbench-mini.md` with the result table, analysis,
  failure cases, and next recommendation.
