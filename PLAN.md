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
reports/swe-contextbench-repeat-variance.md
reports/swe-contextbench-d0-d1g-large.md
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

Three-run D0 vs D1G repeat diagnostic:

```text
config=configs/swe-contextbench-followup-gated-slice.json

D0  resolved trials:  3/21
D1G resolved trials:  9/21

D0  per-run resolved:  1/7, 2/7, 0/7
D1G per-run resolved:  3/7, 3/7, 3/7

apply-only:
D0  2/18
D1G 6/18
```

Next larger D0 vs D1G slice:

```text
config=configs/swe-contextbench-d0-d1g-large-slice.json
pairs=17
d1_applicability: apply=15, skip=2
public-artifact preflight: 17/17
local Docker image preflight: 17/17 after local diagnostic image rebuild
```

Larger D0 vs D1G diagnostic:

```text
config=configs/swe-contextbench-d0-d1g-large-slice.json
artifact_root=/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-d0-d1g-large-slice-codex

run-01:
D0  10/17
D1G 10/17

agent_ok=17/17 for both modes
benchmark-noise patches=0
infra_errors=0

repeat-02:
D0  10/17
D1G 11/17

agent_ok: D0 16/17, D1G 17/17
benchmark-noise patches: D0 1, D1G 0
infra_errors=0

two-run aggregate:
D0  20/34
D1G 21/34

clean paired view, dropping the noisy repeat-02 Sphinx pair:
D0  19/33
D1G 20/33

publishable run:
D0  9/17
D1G 9/17

authenticated remote Docker pull preflight: 17/17
agent_ok=17/17 for both modes
benchmark-noise patches=0
infra_errors=0

three-run aggregate:
D0  29/51
D1G 30/51

clean paired view, dropping only the noisy repeat-02 Sphinx pair:
D0  28/50
D1G 29/50
```

Important caveat: run-01 and repeat-02 used local images rebuilt with the
official SWE-ContextBench `build_instance.py` module after Docker Hub
rate-limited prebuilt image pulls. Treat them as diagnostic recovery runs. The
publishable run used authenticated remote Docker pulls and is the cleanest
headline lane.

## Interpretation

The Decision Layer signal is narrower than the 7-pair repeat made it look. The
publishable run is neutral on the headline metric: `D0 9/17`, `D1G 9/17`.
Across all three larger runs the aggregate is only `D1G 30/51` vs `D0 29/51`,
or clean paired `D1G 29/50` vs `D0 28/50`.

The repeat diagnostic also confirms agent variance clearly. On
`scikit-learn__scikit-learn-25763`, `D0` and `D1G` had the same effective prompt
because the gate skipped the Decision Brief, but `D1G` solved 3/3 while `D0`
solved 1/3. Do not count that pair as memory value.

The cleanest positive signal is still exact decision transfer. In the
publishable run, `sympy__sympy-20567` is a clean D1G-only win and
`django__django-11858` is D1G-only with a P2P `44/45` caveat. The strongest
counterexamples are `pytest-dev__pytest-7215`, where D1G failed to apply a patch
that D0 solved, and `django__django-33374`, where D1G followed the related
decision into the wrong layer.

A narrow guarded lane now exists for canary testing:

```text
D1GA = D1G decisions + explicit application guard
```

The guard asks the agent to map each decision to the target issue's concrete
failing behavior and source area before editing, and to ignore decisions that do
not map cleanly. This keeps the old `D1G` results comparable.

First `D1GA` delta canary:

```text
config=configs/swe-contextbench-d1ga-delta-canary.json
artifact_root=/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-d1ga-delta-canary-codex

D1GA 1/3

agent_ok=3/3
benchmark-noise patches=0
infra_errors=0
```

Do not widen `D1GA` as-is. It preserved the clean `django__django-30903` win,
but lost `django__django-26193` by becoming too conservative and did not recover
the `pytest-dev__pytest-7215` patch-application failure.

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

## Publishable Metric Contract

Use this contract for the next wider run before looking at its grading results:

- headline comparison: `D0` vs `D1G`
- headline score: official SWE-ContextBench resolved count after excluding
  infrastructure-error rows
- hygiene exclusion: any agent patch that touches tests, fixtures, benchmark
  files, docs, or generated artifacts must be reported separately and excluded
  from the clean paired view
- variance report: include per-run totals and pair matrix, not only aggregate
  totals
- gate report: split `D1G` pairs into `apply` and `skip`; do not count skipped
  pairs as memory value
- P2P caveats: report any official resolved row whose PASS_TO_PASS count is not
  full, but do not silently change the official headline score after results are
  known
- model control: same backend, model, reasoning effort, timeout, and runner
  version inside each compared lane
- image control: publishable lane should use prebuilt or authenticated-pulled
  SWE-ContextBench images; local rebuilt images are diagnostic only

## Publishable Run Command

The publishable lane is prepared as:

```text
scripts/run-swe-contextbench-publishable-d0-d1g
```

Defaults:

```text
config=configs/swe-contextbench-d0-d1g-large-slice.json
run_name=swe-contextbench-d0-d1g-publishable-codex
modes=D0,D1G
agent_backend=codex
codex_model=gpt-5.3-codex-spark
codex_reasoning_effort=low
preflight_docker=pull
```

The script ran remote Docker pull preflight first. If preflight fails, agents
and grading do not start. It writes:

```text
/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-d0-d1g-publishable-codex/publishable-run.log
/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-d0-d1g-publishable-codex/summary.md
```

Publishable run result:

```text
artifact_root=/home/dev/benchmarks/swe-contextbench/agent-runs/swe-contextbench-d0-d1g-publishable-codex
phase=preflight, agents, grade, summary
modes=D0,D1G
preflight_docker=pull
preflight=17/17
agent_phase=D0 17/17, D1G 17/17
official_grading=34/34
infra_errors=0
benchmark_noise=0
D0=9/17
D1G=9/17
```

## Completed Checklist

- [x] User ran `docker login`; authenticated remote Docker pulls work.
- [x] Ran `scripts/run-swe-contextbench-publishable-d0-d1g`.
- [x] Generated publishable `summary.md`.
- [x] Updated `reports/swe-contextbench-d0-d1g-large.md` with the publishable
  result and analysis.

## Recommendation

Do not claim net uplift on the broader SWE-ContextBench slice. The proof now
supports a narrower claim: the Decision Layer can transfer exact reusable
decisions, but the current prompt-level D1G injection is not reliably better
than D0 across mixed coding tasks.

Next work should focus on one of two paths:

- narrow the benchmark slice to cases with demonstrably applicable prior
  decisions before measuring lift
- improve the decision application mechanism so the agent must connect each
  decision to the target fix point before editing code
