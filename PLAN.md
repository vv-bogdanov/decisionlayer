# Decision Layer POC Result

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
but not a fully independent hand-labeled gold corpus. The next useful step would
be packaging these artifacts into a short POC report before adding more rules.
