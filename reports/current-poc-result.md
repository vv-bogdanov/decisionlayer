# Current POC Result

This is the compact result snapshot for the current Decision Layer POC.

## Environment

```text
benchmark=LongMemEval-V2 text-only deterministic subset
examples=295
reader=openai-chat via local llama.cpp
model=qwen36-35b-a3b-udiq3s
reasoning=off
reader_max_tokens=128
context_max_chars=96000
```

## Artifacts

```text
/tmp/decision-layer-d0-current-no-reasoning
/tmp/decision-layer-d1-narrow-relevant-full-v2
/tmp/decision-layer-d2-narrow-full-v5-procedure-audit
```

## Metrics

| Run | Correct | Accuracy | Procedure | Static | Dynamic | Briefs | Adds | False Rate | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D0 current | 31/295 | 0.105085 | 3/74 | 22/134 | 6/86 | 0 | 0 | n/a | n/a |
| D1 narrow v2 | 44/295 | 0.149153 | 19/74 | 22/134 | 3/86 | 17 | 18 | n/a | n/a |
| D2 procedure audit | 42/295 | 0.142373 | 18/74 | 20/134 | 4/86 | 16 | 17 | 0.0 | 0.944444 |

## Headline

D2 improves over current D0 by 11 correct answers overall and by 15 correct
answers on procedure tasks.

The strongest signal is procedural reliability:

```text
D0 procedure: 3/74
D2 procedure: 18/74
delta: +15
```

D2 had zero audited false decisions. All 16 cases with non-empty Decision Briefs
were answered correctly.

## Conclusion

The current result supports a narrow POC claim: compact accepted decisions help
the same backend/model retain procedural commitments across long-horizon memory
tasks. It does not claim to replace ordinary memory, RAG, or environment state
tracking.
