# Decision Layer POC Result and Next Plan

## Goal

Prove or falsify that a Decision Layer improves long-horizon task performance
on a known external benchmark while using the same backend/model. We are not
building a memory product, custom benchmark, REST API, UI, vector DB, graph
memory, reranker, or production storage for this POC.

Reasoning stays disabled for the local reader. Current reader calls use
`/no_think`, strict one-line boxed answers, and the same llama.cpp OpenAI
compatible endpoint:

```text
http://127.0.0.1:18080/v1
qwen36-35b-a3b-udiq3s
```

## Completed Checklist

- [x] Run a fresh current-code D0 full baseline with reasoning disabled and the
  same reader settings as D2.
- [x] Compare current-code D0 vs D1 narrow v2 vs D2.
- [x] Audit D2 missing expected decisions.
- [x] Avoid extractor expansion because the audit found oracle/audit denominator
  noise, not a repeated high-confidence extractor miss.
- [x] Recalculate D2 audit with a procedure-only accepted-decisions config and
  295/295 reader cache hits.

## Artifacts

Fresh current-code D0 baseline:

```text
/tmp/decision-layer-d0-current-no-reasoning
```

Current narrow D1 full run:

```text
/tmp/decision-layer-d1-narrow-relevant-full-v2
```

Current D2 full run with procedure-only audit denominator:

```text
/tmp/decision-layer-d2-narrow-full-v5-procedure-audit
```

Runtime narrow oracle:

```text
configs/longmemeval-v2-full-blind-oracle-decisions.narrow.json
```

Procedure-only accepted-decisions audit config:

```text
configs/longmemeval-v2-full-blind-accepted-decisions.procedure.json
```

Audit config summary: 17 procedure questions, 18 question-level expected
decisions, 9 unique decision texts.

## Metrics

| Run | Correct | Accuracy | Procedure | Static | Dynamic | Briefs | Adds | Cache Hits | False Rate | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D0 current | 31/295 | 0.105085 | 3/74 | 22/134 | 6/86 | 0 | 0 | 0 | n/a | n/a |
| D1 narrow v2 | 44/295 | 0.149153 | 19/74 | 22/134 | 3/86 | 17 | 18 | 0 | n/a | n/a |
| D2 procedure audit | 42/295 | 0.142373 | 18/74 | 20/134 | 4/86 | 16 | 17 | 295 | 0.0 | 0.944444 |

## Read

The current proof signal is positive:

- D2 improves over current D0 by `+11` correct answers overall.
- D2 improves procedure tasks from `3/74` to `18/74`, a `+15` procedure lift.
- D2 has `0` audited false decisions.
- D2 has `16/16` correct answers on cases with non-empty Decision Briefs.
- D2 is only `2` correct answers behind D1 narrow v2, while using extracted
  decisions rather than oracle-injected decisions.

The earlier D2 v4 audit reported 28 missing expected decisions because the
accepted oracle still contained static/dynamic entries that D2 intentionally
skips under the safety rule. After using a procedure-only accepted-decisions
denominator, missing expected decisions dropped to 1 and recall became
`0.944444`.

The single remaining procedure miss is `7e32e4a2`:

```text
Do not change any other configuration while placing the order.
```

D1 had this brief and still answered the case incorrectly, so this is not enough
evidence to expand the extractor.

## Trade-Offs

This is a POC signal, not a production claim. The benchmark run is still one
deterministic local-reader pass, and the accepted decision set is conservative
but not a fully independent hand-labeled gold corpus.

## Next Goal

Turn the repository into a publishable, reproducible research artifact, then
move the next benchmark track toward coding-agent tasks. Do not expand the
extractor before the repo can be cited and the current result can be reproduced.

## Publishable Repo Checklist

- [x] Write `docs/research-report.md` with hypothesis, methodology, result
  tables, case studies, limitations, and recommendations.
- [x] Write `docs/reproducibility.md` with exact setup, data preparation,
  commands, local llama.cpp assumptions, expected metrics, and artifact paths.
- [x] Write `docs/decision-layer-design.md` explaining the core/plugin boundary,
  D0/D1/D2 definitions, authority rules, and why facts/history/RAG are not
  Decision Layer state.
- [x] Update `README.md` so a new reader can understand what this is, what it is
  not, how to run smoke tests, and how to reproduce the current POC result.
- [x] Add `LICENSE` before publishing. Prefer Apache-2.0 or MIT.
- [x] Add `CITATION.cff` with project name, authors, repository URL placeholder,
  and version/date.
- [x] Add a minimal CI workflow for `pytest`, `ruff`, `ruff format --check`, and
  `mypy`.
- [x] Clean repository noise before publishing: remove editor/cache artifacts
  from git, verify `.gitignore`, and keep large/generated benchmark artifacts out
  of the repository.
- [x] Add a compact `reports/current-poc-result.md` snapshot so the headline
  result is visible without reading `/tmp` artifacts.
- [x] Add a small reproduction helper script for the current result or a
  documented smoke equivalent; avoid hiding important benchmark assumptions in
  shell magic.

## Coding Benchmark Track

The next external benchmark should focus on coding or software-work tasks, not
another custom synthetic benchmark. Selection criteria:

- [x] Known external benchmark with public task definitions and citation path.
- [x] Runnable with the same backend/model for D0 vs Decision Layer comparison.
- [x] Supports resume/cache or can be wrapped safely for long runs.
- [x] Has deterministic or inspectable grading.
- [x] Lets us measure horizon through task success by human-time bucket, task
  length, tool-call count, repository size, or multi-step dependency depth.
- [x] Has a natural place for Decision Layer interventions: accepted
  requirements, constraints, implementation decisions, prior failed attempts, or
  project-specific procedures.

Candidate order:

1. **SWE-bench Lite/Verified or SWE-bench Live small slice**: best known coding
   benchmark family and easiest to explain, but may require harness integration
   work before Decision Layer has a clean insertion point.
2. **WildClawBench**: native-runtime CLI/coding-style agent tasks with real
   tools and containerized grading; promising for long-horizon agent loops.
3. **RoadmapBench**: explicitly long-horizon software development across version
   upgrades; strong fit for decisions/constraints, likely heavier to run.
4. **TheAgentCompany coding subset**: realistic workplace tasks including
   coding, communication, and file/tool use; heavier environment setup.
5. **METR-style time-horizon methodology**: use as the measurement model even if
   we cannot run their private task suite. Report success by task-duration proxy,
   not only aggregate accuracy.

## Next Implementation Checklist

- [x] Finish publishable repo cleanup before adding new benchmark code.
- [x] Create a benchmark-selection note comparing SWE-bench, WildClawBench,
  RoadmapBench, TheAgentCompany, and METR-style horizon analysis.
- [x] Pick one coding benchmark slice for the next POC based on setup cost,
  reproducibility, and Decision Layer insertion quality.
- [x] Define D0/D2 harness integration for the selected coding benchmark.
- [x] Run an official SWE-bench gold-patch harness preflight before adding
  benchmark integration code.
- [ ] Run a small D0/D2 coding-agent canary slice before any overnight/full run.
- [ ] Only after the canary shows signal, prepare a larger coding benchmark run.
