# SWE-ContextBench Sphinx-865 Canary

This report records the hardened canary for the fresh pair selected after the
runner fixes:

```text
base:    sphinx-doc__sphinx-10614
related: sphinx-doc__sphinx-865
```

Generated artifacts live outside this repository:

```text
/home/dev/benchmarks/swe-contextbench/agent-runs/sphinx-doc__sphinx-865
/home/dev/benchmarks/swe-contextbench/SWEContextBench/predictions
/home/dev/benchmarks/swe-contextbench/SWEContextBench/logs/run_evaluation
```

## Protocol

D1 and D2 briefs were prepared from base-task artifacts only. The related
hidden patch, hidden tests, final answer, and grading result were not inspected
before the briefs were written.

The counted workspaces were sanitized single-commit checkouts at the related
base commit. All modes used the same local backend:

```text
opencode run --dir <workspace> --dangerously-skip-permissions --format json \
  --model llama.cpp/qwen36-35b-a3b-udiq3s
```

`decision-layer run-opencode-canary` wrote JSONL agent logs, stderr logs, timing
markers, patch diffs, verifier JSON, and guard-bin wrappers. After this run, the
runner was extended with `--audit-json` and `--progress-log` so future long
runs also persist machine-readable guard/subagent/progress summaries.

## Decision Briefs

D1 manual brief preserved the critical implementation decisions:

- use `sphinx/ext/inheritance_diagram.py`;
- use resolved `refuri` without adding SVG-specific `../`;
- for external intersphinx refs where `internal` is false, derive the graph key
  from the URI fragment after `#`;
- for internal refs with `refuri`, keep `reftitle` as the graph key;
- for local `refid` anchors in SVG, use `current_filename + '#' + refid`;
- for local `refid` anchors in non-SVG, keep `'#' + refid`.

D2 automatic extraction kept the URL-prefix decisions but lost the exact
`internal is false -> URI fragment is graph key` condition. That omission is
the main D2 failure mode.

## Results

| Variant | Resolved | F2P | P2P | Agent time | Grading time | Verifier | Guard audit |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| Gold preflight | yes | 1/1 | 5/5 | n/a | 38.42s | n/a | n/a |
| D0 clean | no | 0/1 | 5/5 | 201.42s | 12.04s | pass | dirty: 1 blocked `pip3` command |
| D1 clean | yes | 1/1 | 5/5 | 325.04s | 11.70s | fail: missing literal `rsplit` | dirty: 16 forbidden-like commands, 14 blocked outputs |
| D2 clean | no | 0/1 | 5/5 | 270.57s | 11.79s | fail: missing `internal`, `rsplit` | clean: no forbidden-like commands |

Patch footprint:

| Variant | Touched files | Patch size |
| --- | --- | ---: |
| D0 clean | `sphinx/ext/inheritance_diagram.py` | 2151 chars |
| D1 clean | `sphinx/ext/inheritance_diagram.py` | 3082 chars |
| D2 clean | `sphinx/ext/inheritance_diagram.py` | 1350 chars |

Structured log sizes:

| Variant | JSONL lines | stderr |
| --- | ---: | ---: |
| D0 clean | 233 | 0 bytes |
| D1 clean | 350 | 0 bytes |
| D2 clean | 311 | 0 bytes |

## Patch Diagnosis

D0 changed the key from `child['reftitle']` to `child.astext()` but kept the
old SVG `../` behavior and did not handle external `internal=false` references.
It did not resolve the F2P test.

D1 used the manual brief to add `class-names`, map resolved children back to
full class names, branch on `child.get('internal')`, derive external fragments
with `split('#')[-1]`, and remove the SVG `../` prefix for local anchors. It
resolved the official target with no P2P regression.

D2 only changed the key to `child.astext()`. It did not branch on `internal`,
did not extract external URI fragments as graph keys, and did not remove the
critical SVG prefix behavior. The verifier correctly caught the missing
concepts.

The D1 verifier failure is too literal: the patch used `split('#')[-1]` instead
of `rsplit('#', 1)[-1]`, while official grading passed. For future runs, verifier
rules should check concepts or accepted alternatives, not one exact token.

## Subagent Notes

OpenCode invoked its internal `task`/explore subagent once in each variant. A
separate local OpenCode helper was also run from this repository as a read-only
auditor over the Sphinx-865 artifacts. The first helper attempt hit the external
directory permission guard; the second used permission-skip for read-only
inspection and matched the main diagnosis: D1 was the only resolved mode, D2
lost the `internal`/fragment-key decision.

## Interpretation

This is the best manual Decision Brief signal so far: with the same model and
hardened runner, D0 failed, D1 resolved, and no P2P regression appeared.

It is not enough to start the 5-pair mini-slice:

- D1 is audit-dirty because the agent attempted install/venv commands despite
  the prompt, even though guard-bin blocked them;
- D2 failed because automatic extraction dropped the most important conditional
  implementation decision;
- the verifier needs less brittle required-term handling.

## Recommendation

Do not start the mini-slice yet. First tighten D2 extraction so conditionals,
authority, and key mappings survive summarization. Then run either a diagnostic
D2 retry on this pair or, for proof, a fresh pair after the extractor update.

## Diagnostic D2 Retry

After this report, the D2 extractor prompt/schema was tightened in
`configs/swe-contextbench-operational-extractor-prompt.md` to preserve exact
conditions, branch behavior, key mappings, and negative prefixes. A diagnostic
retry was run on the same Sphinx-865 pair. This is extractor debugging only, not
proof evidence for this pair.

The new extractor output preserved the missing critical decision:

```text
For external inheritance-diagram refs where `internal` is false, derive the
graph key from the `refuri` fragment after `#`, not from `reftitle`.
```

Retry artifacts:

```text
briefs/d2_retry_operational_brief.md
prompts/d2_retry_extract_operational.md
prompts/d2_retry_task.md
prompts/d2_retry_direct_task.md
logs/d2_retry_extract_operational_*.*
logs/d2_retry*_opencode.*
logs/d2_retry*_verifier.json
logs/d2_retry*_audit.json
patches/d2_retry*.patch
```

| Diagnostic variant | Result | Agent time | Verifier | Audit | Official grading |
| --- | --- | ---: | --- | --- | --- |
| D2 retry standard | no patch | 7.48s | fail | clean | not graded |
| D2 retry direct/no-subagent | patch | 14.64s | pass | clean | resolved, F2P 1/1, P2P 5/5 |

The standard retry failed because the model emitted an OpenCode `task` tool call
as plain text and then stopped. The direct/no-subagent prompt avoided that
executor failure and produced a resolving patch.

The direct patch still differs from the accepted base logic: it treats missing
`internal` as external, while the base patch defaulted missing `internal` to
true. Official grading did not expose a regression, but this should be tightened
in the next fresh proof pair's verifier/prompt expectations.
