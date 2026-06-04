# SWE-ContextBench Canary

Date: 2026-06-04

## Summary

Canary pair:

- Related task: `sympy__sympy-20571`
- Base experience task: `sympy__sympy-24661`
- Relationship: both are about `parse_expr(..., evaluate=False)` behavior in SymPy.

Result: the official harness is reproducible and the task is solvable, but this
pair did not produce a Decision Layer signal. D0, D1, and D2 all failed.

The useful diagnosis is that agents consistently found a parser-only fix, while
the resolving patch also needs a `sign.doit()` fix in
`sympy/functions/elementary/complexes.py`.

## Official Sources

Verified locally:

- Dataset: `https://huggingface.co/datasets/jiayuanz3/SWEContextBench`
- Harness: `https://github.com/jiayuanz3/SWEContextBench`
- External workspace: `/home/dev/benchmarks/swe-contextbench`
- Official repo clone: `/home/dev/benchmarks/swe-contextbench/SWEContextBench`
- Clone commit: `31bb04155f52b184bf31b220e3cff0607ac9c953`
- Dataset metadata reports license tag `mit`.

The official `environment.yml` in the cloned repository appears to be an HTML
page, not a usable Conda environment. The harness itself ran from the cloned
Python package plus Docker.

Docker image used:

- `jiayuanz3/swecontextbench:base`
- `jiayuanz3/swecontextbench:sympy.sympy-20571`

Docker access used:

```text
DOCKER_HOST=unix:///run/user/1000/docker.sock
```

## Artifacts

All generated repositories, predictions, logs, and benchmark reports are outside
this repository:

```text
/home/dev/benchmarks/swe-contextbench/agent-runs/sympy__sympy-20571
/home/dev/benchmarks/swe-contextbench/SWEContextBench/predictions
/home/dev/benchmarks/swe-contextbench/SWEContextBench/logs/run_evaluation
```

Representative logs:

```text
logs/d0_opencode.log
logs/d0_grading.log
logs/d1_opencode_retry2.log
logs/d1_grading.log
logs/d2_opencode_retry.log
logs/d2_empty_grading.log
logs/hermes_d1_grading.log
logs/self_gold_diag_grading.log
```

For future runs, prefer `opencode run --format json` for event logs. `pi -p`
and `hermes -z` did not stream useful progress to stdout in this canary, even
when explicitly prompted to print progress.

## Decision Briefs

D1 manual brief, written only from the base task:

```text
- parse_expr(..., evaluate=False) must preserve unevaluated syntax by transforming relevant AST nodes before SymPy constructors evaluate them.
- EvaluateFalseTransformer in sympy/parsing/sympy_parser.py is the parser-side extension point for adding more evaluate=False behavior.
- When parser-created SymPy calls would simplify by default, the transformer should pass evaluate=False into the constructed SymPy object.
```

D2 automatic brief from direct llama.cpp extraction was valid JSON but too
base-specific to relationals:

```text
- parse_expr must respect evaluate=False for relational operators by constructing unevaluated Lt, Le, Gt, Ge, Ne, and Eq instances.
- sympify must delegate to parse_expr and inherit its evaluate=False behavior for relationals.
- Implement support for relationals in EvaluateFalseTransformer by adding a visit_Compare method that maps AST comparison nodes to sympy relational classes with evaluate=False.
- Map ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE to their corresponding sympy classes within the transformer.
```

Audit result: no related hidden patch/tests were used to create D1/D2 briefs.
D2 has no leakage, but it is not a good reusable brief for this related task.

## Results

| Mode | Patch | Resolved | F2P | P2P | Notes |
| --- | --- | --- | --- | --- | --- |
| Gold preflight | official patch | yes | 2/2 | 50/50 | Harness sanity check passed. |
| D0 OpenCode | parser-only, 1 file | no | 0/2 | 49/50 | Added broad `visit_Call`; introduced one regression. |
| D1 OpenCode | parser-only, 1 file | no | 0/2 | 49/50 | Manual brief did not lead to the missing `sign.doit()` fix. |
| D2 OpenCode | no patch | no | n/a | n/a | Automatic brief was irrelevant/noisy; agent produced no patch before timeout. |
| Hermes diagnostic | parser-only, 1 file | no | 0/2 | 50/50 | Alternative local agent avoided regression but still missed `sign.doit()`. |
| Self/gold diagnostic | parser + `sign.doit()` | yes | 2/2 | 50/50 | Not benchmark evidence; confirms the missing second fix. |

Timing:

```text
D0 agent: 156.07s
D0 grading: 25.11s
D1 useful retry: interrupted after about 4.5m
D1 grading: 25.12s
D2 retry: interrupted after about 3m with no patch
Hermes grading: 24.36s
Self/gold diagnostic grading: 24.52s
```

## Diagnosis

This pair is runnable but not a good positive canary for the current Decision
Layer design.

What happened:

- The base task teaches a parser-side decision about `EvaluateFalseTransformer`.
- The related task requires that parser decision, but also needs a separate
  library-behavior fix in `sign.doit()`.
- D1 did not include any accepted decision about function `doit()` propagation,
  `sign`, or `Pow` forcing evaluation through function internals.
- D2 was worse: it overfit to relationals from the base patch.
- Multiple agents converged on the same parser-only fix, so this is not only an
  OpenCode issue.

The canary therefore triggers the stop rule: D1 has no signal on this pair.

## Recommendations

Do not start the 5-pair mini-slice yet.

Next practical step:

- Pick a new canary where the base experience contains all decisions needed by
  the related task, or
- Add an explicit "diagnostic observation" category for accepted failed/surprising
  behavior if it is authorized by the base artifact.

For this exact pair, a useful Decision Brief would have needed something like:

```text
When parser-created unevaluated function calls still evaluate through function internals, inspect the function's doit/eval path; a parser-only evaluate=False patch may be insufficient.
```

That statement is not present in the base decision brief, so we should not count
this canary as Decision Layer evidence.
