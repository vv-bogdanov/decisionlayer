# Decision Layer POC Plan

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

## Latest Completed Artifacts

Old deterministic D0 baseline:

```text
/tmp/decision-layer-overnight-20260603212552/full/D0
```

Old broad blind D1 run:

```text
/tmp/decision-layer-d1-blind-full
```

D2 v3 broad-oracle audit after reader-output contract and stock-restocking
clarification:

```text
/tmp/decision-layer-d2-blind-full-v3-broad
```

Current conservative narrow oracle:

```text
configs/longmemeval-v2-full-blind-oracle-decisions.narrow.json
```

Narrow oracle summary: 42 questions with decisions, 45 question-level decisions,
12 unique decision texts. This is still not hand-audited gold, but it removes
most facts, UI state, answer-like statements, and weak requirements from the
broad 70k-line draft, then applies the same question-relevance gate used by D1.

Current narrow D1 full run:

```text
/tmp/decision-layer-d1-narrow-relevant-full-v2
```

Current D2 full run against the narrow oracle:

```text
/tmp/decision-layer-d2-narrow-full-v4
```

## Current Metrics

| Run | Correct | Accuracy | Procedure | Static | Dynamic | Briefs | Adds | Completion Tokens | False Rate | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Old D0 | 21/295 | 0.071186 | 1/74 | 17/134 | 3/86 | 0 | 0 | 20954 | n/a | n/a |
| Old broad D1 | 30/295 | 0.101695 | 9/74 | 18/134 | 3/86 | 74 | 16798 | 19984 | n/a | n/a |
| D2 v3 broad audit | 40/295 | 0.135593 | 16/74 | 20/134 | 4/86 | 14 | 15 | 4709 | 0.0 | not useful |
| D1 narrow v2 | 44/295 | 0.149153 | 19/74 | 22/134 | 3/86 | 17 | 18 | 4970 | n/a | n/a |
| D2 narrow v4 | 42/295 | 0.142373 | 18/74 | 20/134 | 4/86 | 16 | 17 | 4585 | 0.0 | 0.377778 |

Important read:

- D2 narrow v4 has zero audited false decisions.
- D2 narrow v4 has no failed cases with non-empty Decision Briefs.
- D2 narrow v4 is only 2 correct answers behind D1 narrow v2.
- The D1-only-correct cases versus D2 v4 had 0 Decision Brief entries, so the
  gap is reader variance or base-task behavior, not an obvious memory miss.
- The promising signal is procedure lift: old D0 `1/74`, D1 narrow v2 `19/74`,
  D2 narrow v4 `18/74`.
- The proof is not finished because old D0 was produced before the latest reader
  contract changes. We need a fresh current-code D0 before claiming the final
  Decision Layer delta.

## Active Checklist

- [ ] Run a fresh current-code D0 full baseline with reasoning disabled and the
  same reader settings as D2 narrow v4.
- [ ] Compare current-code D0 vs D1 narrow v2 vs D2 narrow v4; treat only lift
  over the fresh D0 as the Decision Layer signal.
- [ ] Audit D2 v4 missing expected decisions: 28 expected narrow-oracle
  decisions were not extracted. Classify each as extractor miss, oracle noise, or
  harmless because it did not affect the final answer.
- [ ] Add at most one small extractor improvement only if the audit shows a
  repeated high-confidence decision pattern with low false-decision risk.
- [ ] Re-run D2 after any extractor change, using resume-by-default behavior so
  completed benchmark cases are not repeated unless an explicit overwrite flag is
  passed.

## Next D0 Command

```bash
uv run decision-layer run-poc \
  --data-root data/longmemeval-v2 \
  --output-dir /tmp/decision-layer-d0-current-no-reasoning \
  --mode D0 \
  --tier small \
  --question-id-file configs/longmemeval-v2-full-deterministic-subset.txt \
  --reader openai-chat \
  --reader-base-url http://127.0.0.1:18080/v1 \
  --reader-model qwen36-35b-a3b-udiq3s \
  --reader-max-tokens 128 \
  --context-max-chars 96000
```
