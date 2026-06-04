# SWE-ContextBench Sphinx Canary

This report records the clean Sphinx canary after switching to Operational
Decision Brief v0.

Pair:

```text
base:    sphinx-doc__sphinx-8265
related: sphinx-doc__sphinx-8052
```

Generated artifacts live outside this repository:

```text
/home/dev/benchmarks/swe-contextbench/agent-runs/sphinx-doc__sphinx-8052
/home/dev/benchmarks/swe-contextbench/SWEContextBench/predictions
/home/dev/benchmarks/swe-contextbench/SWEContextBench/logs/run_evaluation
```

## Protocol

The initial D0 attempt used a full Sphinx git checkout and is invalid for proof:
the agent found a future upstream fix through `git show`. It is kept only as a
leakage diagnostic.

The counted runs used sanitized single-commit workspaces created from the target
base commit. Agent prompts explicitly forbade `git log`, `git show`, and
`git blame`. A guard-bin blocked installs and privilege escalation commands.

Saved run artifacts include:

```text
briefs/d1_manual_operational_brief.md
briefs/d2_auto_operational_brief.md
prompts/d0_task.md
prompts/d1_task.md
prompts/d2_task.md
prompts/d2_extract_operational*.md
logs/*_opencode.jsonl
logs/*_opencode.stderr
logs/*_opencode_time.txt
logs/*_grading_time.txt
```

Clean runs used the same executor and backend:

```text
opencode run --format json --model llama.cpp/qwen36-35b-a3b-udiq3s
```

## Decision Briefs

D1 manual brief was written from the base task only and preserved these
operational commitments:

- tuple defaults must render with parentheses;
- `sphinx/pycode/ast.py` is the accepted extension point;
- `visit_Tuple()` should parenthesize tuples;
- `visit_Subscript()` must preserve Python subscript display rules;
- simple tuple slices are non-empty tuples without starred elements.

D2 automatic extraction used llama.cpp at temperature 0. The first response had
useful content but invalid JSON, so it was retried with a stricter JSON-only
prompt. The accepted D2 brief preserved the same tuple/subscript decisions and
rejected out-of-scope generalizations.

## Results

| Variant | Counted? | Resolved | F2P | P2P | Agent time | Notes |
| --- | --- | --- | --- | --- | ---: | --- |
| Gold preflight | yes | yes | 1/1 | 37/37 | n/a | Confirms harness and image are usable. |
| D0 full-history | no | n/a | n/a | n/a | 45.03s | Invalid: agent used future git history. |
| D0 clean | yes | yes | 1/1 | 36/37 | 38.02s | Fixed target issue but regressed tuple annotation rendering. |
| D1 clean | yes | yes | 1/1 | 36/37 | 20.71s | Faster, but same regression; did not apply subscript-preservation decision. |
| D2 clean | yes | yes | 1/1 | 36/37 | 36.63s | Applied subscript idea but over-broadened patch and kept same regression. |

Official grading reports:

```text
/home/dev/benchmarks/swe-contextbench/SWEContextBench/decision-layer-contextbench-sphinx-gold-canary.json
/home/dev/benchmarks/swe-contextbench/SWEContextBench/decision-layer-contextbench-sphinx-d0-clean.json
/home/dev/benchmarks/swe-contextbench/SWEContextBench/decision-layer-contextbench-sphinx-d1-clean.json
/home/dev/benchmarks/swe-contextbench/SWEContextBench/decision-layer-contextbench-sphinx-d2-clean.json
```

All clean non-gold variants failed the same PASS_TO_PASS test:

```text
tests/test_pycode_ast.py::test_unparse[Tuple[int, int]-Tuple[int, int]]
```

Patch footprint:

| Variant | Touched files |
| --- | --- |
| D0 clean | `sphinx/pycode/ast.py` |
| D1 clean | `sphinx/pycode/ast.py` |
| D2 clean | `sphinx/pycode/ast.py`, `sphinx/domains/python.py` |

The clean JSONL logs and stderr audit did not show forbidden history commands.

Structured log sizes:

| Log | JSONL lines | stderr |
| --- | ---: | --- |
| D0 full-history | 111 | 0 bytes |
| D0 clean | 59 | 0 bytes |
| D1 clean | 28 | 0 bytes |
| D2 clean | 62 | 0 bytes |

A read-only local OpenCode helper was used as a diagnostic log-audit subagent.
The first absolute-path attempt hit an external-directory permission block, so
the helper was rerun from the Sphinx artifact directory. It confirmed the
aggregate grading results, log presence, empty stderr, and that D1 had a much
shorter event log than D0/D2. The exact failing test above comes from the
official JSON reports inspected by the main session.

## Diagnosis

This canary does not show a positive Decision Layer signal. D0, D1, and D2 all
resolve the target F2P test, and D1/D2 do not improve the official P2P score.

The D1 brief contained the right subscript-preservation decision, but the agent
ignored it and made only the tuple-rendering change. D2 extracted a more
operational brief and the agent attempted to use it, but the implementation was
too broad and still missed the existing P2P expectation.

After adding `decision-layer verify-patch`, the generated Sphinx patches were
checked post-hoc with this narrow rule:

```text
--require-term visit_Subscript
--require-term is_simple_tuple
--require-file sphinx/pycode/ast.py
--allow-file sphinx/pycode/ast.py
```

The verifier flags D1 as missing both required terms, and flags D2 for touching
`sphinx/domains/python.py` outside the allowlist. This would not prove a patch is
correct, but it would have caught both observed brief-adherence failures before
official grading.

The useful result is methodological: proof runs must sanitize git history and
record structured logs, timings, diffs, and grading output per variant. Without
that, a local coding agent can accidentally use repository history as hidden
memory.

## Recommendation

Do not start the 5-pair mini-slice yet. The next step should be one smaller
protocol improvement before another fresh canary:

- require sanitized single-commit workspaces for every coding proof run;
- keep structured logs, timing, diff snapshots, guard audits, and grading
  reports as mandatory artifacts;
- add a lightweight action verifier that checks whether critical brief decisions
  appear in the generated patch before expensive official grading;
- use alternative local agents or subagents only as diagnostics unless the same
  runner/model is predeclared for the whole comparison.
