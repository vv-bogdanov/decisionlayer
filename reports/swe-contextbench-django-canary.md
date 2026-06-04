# SWE-ContextBench Django Canary

This report records a third SWE-ContextBench canary under the sanitized
single-commit protocol and the new patch/brief verifier.

Pair:

```text
base:    django__django-11019
related: django__django-30153
```

Generated artifacts live outside this repository:

```text
/home/dev/benchmarks/swe-contextbench/agent-runs/django__django-30153
/home/dev/benchmarks/swe-contextbench/SWEContextBench/predictions
/home/dev/benchmarks/swe-contextbench/SWEContextBench/logs/run_evaluation
```

## Why This Pair

The base task fixes Django `Media` ordering by replacing sequential pairwise
merging with a graph-based merge over original media sublists. The related
public task reports broken admin media ordering when custom widget media,
inlines, and `filter_horizontal` interact.

This made the pair a good test for operational decisions:

- merge all original sublists at once with `Media.merge(*lists)`;
- keep original JS/CSS sublists until final rendering;
- build dependencies only from adjacent items in original sublists;
- use ordered unique items plus topological sorting;
- warn and fall back on cyclic dependencies.

No related hidden patch, hidden tests, final answer, or grading result was used
while writing D1 or extracting D2.

## Runner Notes

The run uncovered two important non-benchmark issues:

- `opencode run` must receive an explicit `--dir`; `cwd` alone can leave tools
  pointed at this repository instead of the benchmark checkout.
- noninteractive OpenCode needs `--dangerously-skip-permissions` plus a guard
  layer, otherwise it can stall before the first tool call.

Diagnostic runs are kept in the artifact directory:

```text
logs/d0_clean_blocked_*
logs/d0_clean_wrong_dir_*
logs/d0_clean_gitlog_violation_*
logs/d1_clean_noop_*
```

The final guard blocked installs, privilege escalation, and later blocked
`git log`, `git show`, and `git blame` even when passed after options such as
`git -C ... log`.

## Results

| Variant | Counted? | Agent result | Official result | Verifier | Time | Notes |
| --- | --- | --- | --- | --- | ---: | --- |
| Gold preflight | yes | n/a | resolved, F2P 2/2, P2P 15/15 | n/a | 44.27s grading | Harness/image valid. |
| D0 clean | yes | timeout, no patch | not graded | n/a | 600.02s | Valid guarded baseline timeout. |
| D1 clean compact | yes, dirty audit | timeout with partial patch | resolved, F2P 2/2, P2P 14/15 | fail | 600.03s agent, 9.84s grading | Manual brief directed the agent to a resolving patch, but it regressed `test_merge_warning`. |
| D2 clean compact | yes, dirty verifier | exit 0 with patch | unresolved, verifier setup failed | fail | 548.73s agent, 9.19s grading | Auto brief led to an over-broad patch that broke test collection. |

D1 official P2P failure:

```text
tests/forms_tests/tests/test_media.py::FormsMediaTestCase::test_merge_warning
```

D2 official failure:

```text
Verifier setup failed: collected 0 tests after patch for django__django-30153;
expected 17 requested tests
```

Patch footprint:

| Variant | Touched files |
| --- | --- |
| D0 clean | none |
| D1 clean compact | `django/forms/widgets.py` |
| D2 clean compact | `django/forms/widgets.py`, `django/db/migrations/topological_sort.py`, `django/utils/topological_sort.py` |

Structured log sizes:

| Log | JSONL lines | stderr |
| --- | ---: | --- |
| D0 clean | 2 | 0 bytes |
| D1 clean compact | 654 | 0 bytes |
| D2 clean compact | 604 | 0 bytes |

## Verifier Outcomes

D1 was checked with:

```text
--require-term stable_topological_sort
--require-term CyclicDependencyError
--require-file django/forms/widgets.py
--allow-file django/forms/widgets.py
```

It touched the right file but missed both required terms. The agent implemented
its own Kahn-sort approach instead of following the accepted base decision.

D2 matched the required terms and required file, but failed the allowlist by
editing migration topological sort code and adding a new utility module. The
allowlist caught the over-broad patch before official grading.

## Audit Notes

D1 is not clean proof:

- it timed out and only left a partial patch;
- it attempted dependency installation despite the prompt;
- it ran `git -C ... log` before the guard was hardened;
- it failed the patch/brief verifier;
- it regressed one PASS_TO_PASS test.

D2 is also not clean proof:

- it attempted blocked `git log/show` commands, which the hardened guard caught;
- it failed the patch verifier due to unexpected files;
- the official verifier collected zero tests after the patch.

## Interpretation

This is the first canary with a real positive-looking D1 direction: D0 produced
no patch, while D1's manual operational brief produced a patch that resolved the
target F2P tests. However, it is not publishable proof because the run is dirty
and the patch regresses P2P behavior.

The practical lesson is stronger than the benchmark signal: the Decision Brief
can move the agent toward the right implementation area, but the current
executor loop is too willing to repair the environment, ignore exact authorized
decisions, and broaden the patch.

## Recommendation

Do not start the 5-pair mini-slice yet. Before another canary:

- make `--dir` mandatory for OpenCode runs;
- keep permission-skip only with a strict guard layer;
- block history commands regardless of git option order;
- block or explicitly disallow local environment repair loops;
- run the patch verifier before official grading and store its JSON output;
- treat D1 as signal only if it resolves without timeout, install attempts,
  forbidden-history attempts, verifier failure, or P2P regression.
