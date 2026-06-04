# SWE-bench D0/D2 Agent Canary

This report records the first coding-agent D0/D2 canary for the Decision Layer
track.

## Purpose

Verify that a local coding agent can produce SWE-bench predictions and that the
official harness can grade both D0 and D2 under the same backend/model.

This is not a Decision Layer proof result. The selected instance was easy enough
that both D0 and D2 resolved it.

## Benchmark Instance

```text
dataset=SWE-bench/SWE-bench_Lite
instance_id=sympy__sympy-20590
repo=sympy/sympy
base_commit=cffd4e0f86fefd4802349a9f9b19ed70934ea354
FAIL_TO_PASS=["test_immutable"]
```

Issue summary:

```text
Symbol instances unexpectedly expose __dict__. Accessing
sympy.Symbol("s").__dict__ should raise AttributeError.
```

## Local Setup

SWE-bench is installed outside this repository:

```text
/home/dev/benchmarks/SWE-bench
```

Agent workspaces are also outside this repository:

```text
/home/dev/benchmarks/swebench-canary/sympy__sympy-20590/d0
/home/dev/benchmarks/swebench-canary/sympy__sympy-20590/d2
```

Official harness reports are outside this repository:

```text
/home/dev/benchmarks/SWE-bench/opencode-llama.cpp-qwen36-d0.decision-layer-canary-d0.json
/home/dev/benchmarks/SWE-bench/opencode-llama.cpp-qwen36-d2.decision-layer-canary-d2.json
```

The Docker Python client needs the rootless socket on this machine:

```text
DOCKER_HOST=unix:///run/user/1000/docker.sock
```

## D0

D0 used the same local OpenCode agent and llama.cpp backend without a Decision
Brief.

Prediction artifact:

```text
/home/dev/benchmarks/swebench-canary/sympy__sympy-20590/predictions/d0.json
```

Patch summary:

```text
sympy/core/_print_helpers.py | 1 +
```

The patch adds:

```python
__slots__ = ()
```

to `class Printable`.

Official evaluation command:

```bash
cd /home/dev/benchmarks/SWE-bench
DOCKER_HOST=unix:///run/user/1000/docker.sock uv run python -m swebench.harness.run_evaluation \
  --predictions_path /home/dev/benchmarks/swebench-canary/sympy__sympy-20590/predictions/d0.json \
  --max_workers 1 \
  --instance_ids sympy__sympy-20590 \
  --run_id decision-layer-canary-d0
```

Result:

```text
total_instances=1
completed_instances=1
resolved_instances=1
unresolved_instances=0
error_instances=0
```

## D2

D2 used the same local OpenCode agent and llama.cpp backend, with this accepted
Decision Brief injected into the task prompt:

```text
- Symbol instances must not expose __dict__; accessing sympy.Symbol("s").__dict__
  should raise AttributeError.
- Preserve Symbol.__slots__ == ("name",) behavior and do not add per-instance
  storage to Symbol.
- Make the smallest class-hierarchy fix needed; avoid unrelated API or behavior
  changes.
```

Prediction artifact:

```text
/home/dev/benchmarks/swebench-canary/sympy__sympy-20590/predictions/d2.json
```

Patch summary:

```text
sympy/core/_print_helpers.py | 1 +
```

The patch adds the same `__slots__ = ()` class-hierarchy fix to
`class Printable`.

Official evaluation command:

```bash
cd /home/dev/benchmarks/SWE-bench
DOCKER_HOST=unix:///run/user/1000/docker.sock uv run python -m swebench.harness.run_evaluation \
  --predictions_path /home/dev/benchmarks/swebench-canary/sympy__sympy-20590/predictions/d2.json \
  --max_workers 1 \
  --instance_ids sympy__sympy-20590 \
  --run_id decision-layer-canary-d2
```

Result:

```text
total_instances=1
completed_instances=1
resolved_instances=1
unresolved_instances=0
error_instances=0
```

## Interpretation

The coding-benchmark pipeline is now proven on this machine:

- local coding agent -> patch
- patch -> SWE-bench prediction JSON
- prediction JSON -> official SWE-bench Docker harness
- official report -> resolved/unresolved metric

The one-instance canary does not show Decision Layer lift because D0 and D2 both
resolved the task. It is still useful because it validates the harness before a
larger run.

The next run should not be a full overnight run yet. The next step is a harder
5-10 task SWE-bench-family slice where the issue text contains durable
requirements, constraints, or failed-attempt conclusions that can naturally
benefit from Decision Brief persistence.

## Operational Caveats

- The D0 helper run attempted a system package install with
  `pip install ... --break-system-packages` before the final patch was captured.
  Future agent prompts must explicitly forbid installs, and harness wrappers
  should enforce that rule where possible.
- The D2 prompt included hard command rules forbidding package installation.
  No install command was observed during the D2 run.
- Local `pytest` was unavailable in the SymPy checkout, so local agent
  verification was limited to Python smoke snippets. The official SWE-bench
  harness result is the grading source of truth.
