# Current Plan: Publishable Coding Proof

## Goal

Turn the current Decision Layer POC into a clean, publishable coding-benchmark
proof: same backend/model, known external benchmark, transparent artifacts, and
clear D0 vs D1 vs D2 comparisons.

This remains a POC. Do not build a product platform, REST API, UI, vector DB,
custom judge, or custom benchmark unless it is directly needed for D0/D1/D2
measurement.

## Current Evidence

The 5-pair SWE-ContextBench mini-slice is complete. Report:

```text
reports/swe-contextbench-mini.md
```

D1 showed signal on the mini-slice: D0 resolved 1/5, D1 resolved 3/5, and D2
resolved 1/5. This supports a larger coding-focused run, but D2 extraction is
not yet good enough to claim automatic Decision Layer quality.

## Rules

Keep these constraints for all next proof runs:

- predeclare the benchmark slice before running agents
- same backend/model/reasoning for D0, D1, and D2 inside a reported lane
- official SWE-ContextBench Docker grading is the source of truth
- no related hidden patch, hidden tests, final answer, or grading result in D1/D2
- skip completed agent/grading steps by default; overwrite only explicitly
- keep OpenCode and Codex as separate measurement lanes
- sanitized single-commit workspace checkout
- no OpenCode subagents inside proof runs
- no `git log`, `git show`, or `git blame`
- no installs, virtualenvs, `pip`, `uv`, `sudo`, or `pkexec`
- no product platform work unless it directly improves the proof

## Active Checklist

- [ ] Add a machine-generated summary command for mini/larger SWE-ContextBench
  artifact directories so tables are reproducible from JSON.
- [ ] Tighten proof patch verification to flag test-file edits and other
  benchmark-noise changes before official grading.
- [ ] Improve the D2 extractor prompt using only base-task artifacts and the five
  completed mini-slice diagnoses; target transferable operational decisions,
  explicit scope, and less base-specific trivia.
- [ ] Predeclare a larger SWE-ContextBench coding slice, about 20 Verified
  related pairs, with metadata committed before agent runs.
- [ ] Prepare D1 manual briefs for the larger slice without looking at related
  hidden patches/tests or grading outcomes.
- [ ] Run D0/D1/D2 on the larger slice with Codex Spark low-reasoning as the
  primary lane and resume/cache enabled.
- [ ] Write the publishable research artifact with methodology, artifact paths,
  full tables, limitations, and the D1-vs-D2 interpretation.
