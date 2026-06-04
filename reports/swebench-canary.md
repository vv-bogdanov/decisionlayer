# SWE-bench Canary Preflight

This report records the first coding-benchmark preflight for the next phase.

## Purpose

Verify that the machine can run an official external coding benchmark harness
before adding Decision Layer integration.

This is not yet a D0/D2 Decision Layer result. It uses SWE-bench gold
predictions to validate the dataset, Docker harness, and grading pipeline.

## Source

```text
https://github.com/SWE-bench/SWE-bench
https://arxiv.org/abs/2310.06770
```

## Local Setup

SWE-bench was cloned outside this repository:

```text
/home/dev/benchmarks/SWE-bench
```

The local install was created with:

```bash
mkdir -p /home/dev/benchmarks
git clone --depth 1 https://github.com/SWE-bench/SWE-bench /home/dev/benchmarks/SWE-bench
cd /home/dev/benchmarks/SWE-bench
uv venv
uv pip install -e .
```

Docker uses the rootless context on this machine, so the Python Docker client
needs:

```text
DOCKER_HOST=unix:///run/user/1000/docker.sock
```

## Command

```bash
cd /home/dev/benchmarks/SWE-bench
DOCKER_HOST=unix:///run/user/1000/docker.sock uv run python -m swebench.harness.run_evaluation \
  --predictions_path gold \
  --max_workers 1 \
  --instance_ids sympy__sympy-20590 \
  --run_id decision-layer-canary-gold
```

## Result

```text
Total instances: 1
Instances completed: 1
Instances resolved: 1
Instances unresolved: 0
Instances with errors: 0
Unstopped containers: 0
Unremoved images: 0
Report written to gold.decision-layer-canary-gold.json
```

The generated SWE-bench report is outside this repository:

```text
/home/dev/benchmarks/SWE-bench/gold.decision-layer-canary-gold.json
```

## Interpretation

The external coding benchmark harness is runnable on this machine. The next
step was a D0/D2 coding-agent canary on the same instance with the same
backend/model and an explicit Decision Layer brief.

Follow-up result:

```text
reports/swebench-d0-d2-canary.md
```

Both D0 and D2 resolved the instance, so the follow-up validates the pipeline
but does not show Decision Layer lift.

## Caveats

- This canary used a gold patch, so it does not test agent coding ability.
- It does not test Decision Layer extraction or prompt enrichment.
- It validates infrastructure only: dataset access, local SWE-bench package,
  Docker access, and grading.
