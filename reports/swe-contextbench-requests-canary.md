# SWE-ContextBench Requests Canary

This report records the clean proof canary after the Sphinx-865 D2 extractor
diagnostic.

Pair:

```text
base:    psf__requests-1142
related: psf__requests-1144
```

Generated artifacts live outside this repository:

```text
/home/dev/benchmarks/swe-contextbench/agent-runs/psf__requests-1144
/home/dev/benchmarks/swe-contextbench/SWEContextBench/predictions_requests_*
/home/dev/benchmarks/swe-contextbench/SWEContextBench/logs/run_evaluation
```

## Protocol

D1 and D2 briefs were prepared from base-task artifacts only. The related hidden
patch, hidden tests, final answer, and grading result were not inspected until
after both briefs were complete.

The counted workspaces were sanitized single-commit checkouts at related base
commit `22623bd8c265b78b161542663ee980738441c307`.

All modes used the same backend and runner:

```text
opencode run --dir <workspace> --dangerously-skip-permissions --format json \
  --model llama.cpp/qwen36-35b-a3b-udiq3s
```

The prompts also disallowed the OpenCode `task`/explore subagent, following the
Sphinx-865 diagnostic where that tool path produced a malformed tool call.

## Decision Briefs

D1 manual brief preserved the complete base decision:

- `requests/models.py` is the accepted extension point.
- `PreparedRequest.prepare_content_length(body)` must not set
  `Content-Length: 0` before checking the body.
- Seekable bodies still use `seek/tell` and restore position.
- Non-`None` bodies still set `Content-Length` to `len(body)`.
- Bodyless non-`GET`/`HEAD` methods set `Content-Length: 0`.
- Bodyless `GET`/`HEAD` leave `Content-Length` unset.

D2 automatic extraction produced one compact decision:

```text
In prepare_content_length, only set Content-Length to '0' when the method is
not GET or HEAD.
```

That was enough for the agent to make the resolving patch.

## Results

| Variant | Resolved | F2P | P2P | Agent time | Grading time | Verifier | Audit |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| Gold preflight | yes | 1/1 | 5/5 | n/a | 37.13s | n/a | n/a |
| D0 clean | no | 0/1 | 5/5 | 55.21s | 24.86s | fail | clean |
| D1 clean | yes | 1/1 | 5/5 | 13.84s | 22.18s | pass | clean |
| D2 clean | yes | 1/1 | 5/5 | 15.89s | 21.19s | pass | clean |

Patch footprint:

| Variant | Touched files | Patch size |
| --- | --- | ---: |
| D0 clean | `requests/utils.py` | 424 chars |
| D1 clean | `requests/models.py` | 1140 chars |
| D2 clean | `requests/models.py` | 587 chars |

Structured log sizes:

| Variant | JSONL lines | stderr | Commands | Dirty audit |
| --- | ---: | ---: | ---: | --- |
| D0 clean | 94 | 0 bytes | 18 | no |
| D1 clean | 17 | 0 bytes | 0 | no |
| D2 clean | 25 | 0 bytes | 2 | no |

## Patch Diagnosis

D0 changed `requests/utils.py` by removing `compress` from the default
`Accept-Encoding` header. It did not touch content-length handling and failed
the official F2P test.

D1 rewrote `prepare_content_length()` around the full manual brief: body
handling first, then `Content-Length: 0` only for bodyless non-`GET`/`HEAD`
methods. It resolved the official target without P2P regression.

D2 made the minimal accepted move: only set the default `Content-Length: 0`
when `self.method not in ('GET', 'HEAD')`; later body branches still override
the header when a body exists. It resolved the official target without P2P
regression.

## Interpretation

This is the first clean D2 proof signal under the hardened coding protocol:

- same local model/backend for D0, D1, and D2;
- sanitized single-commit workspaces;
- no dirty audit events;
- verifier caught the D0 wrong-file patch;
- D0 failed officially;
- D2 passed officially with no P2P regression.

The result supports the Decision Layer hypothesis for coding tasks: a compact
accepted operational decision can steer the same agent to the right fix where
the baseline chooses a plausible but wrong change.

## Caveats

This is still one small Requests pair, not publishable proof by itself. The
next step is a 5-pair mini-slice selected before running, using the same
hardened runner, extractor prompt, audit flags, and reporting template.
