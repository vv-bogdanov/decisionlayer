# Coding Benchmark Selection

The next benchmark track should focus on coding-agent tasks. The goal is not to
create a custom benchmark. The goal is to test whether Decision Layer improves a
recognized external coding or software-work benchmark under the same
backend/model.

## Selection Criteria

- public task definitions and citation path
- runnable locally or with inspectable containers
- deterministic or auditable grading
- feasible small canary before a larger run
- resume/cache support or a wrapper that can add it safely
- natural Decision Layer insertion point
- measurable horizon proxy: human-time bucket, tool-call count, wall-clock time,
  repo size, file count, or multi-step dependency depth

## Candidates

| Benchmark | Fit | Cost | Main Risk |
| --- | --- | --- | --- |
| SWE-bench Lite/Verified or SWE-bench Live small slice | Highest name recognition; real GitHub issue fixing | Medium | Decision Layer insertion can look like prompt engineering unless the agent loop records decisions across attempts |
| WildClawBench | Native-runtime CLI agent tasks; long-horizon, real tools, containerized | Medium | Newer benchmark; need verify harness maturity locally |
| RoadmapBench | Explicit long-horizon software development across version upgrades | High | Heavy tasks and likely expensive full runs |
| TheAgentCompany coding subset | Realistic software-company environment with coding, tools, communication | High | Multi-service setup and broader non-coding task surface |
| METR-style time-horizon methodology | Best measurement frame for "how much longer" | High | Their main task suite is not a simple public drop-in benchmark |

## Recommended Next Slice

Start with a SWE-bench-family canary, preferably a small SWE-bench Lite/Verified
or live/decontaminated slice if the harness can run with the local backend.

Reason:

- easiest to explain in a research artifact
- widely recognized by coding-agent readers
- enough existing tooling to avoid writing a custom benchmark
- can start with a very small slice before overnight runs

Decision Layer should be inserted as an agent-side sidecar, not as task-answer
leakage. The canary should compare:

- D0: same coding agent without Decision Brief persistence
- D2: same coding agent with accepted requirements, constraints, failed-attempt
  conclusions, and implementation decisions persisted into a compact Decision
  Brief

Do not pre-label answer patches or test outcomes as decisions.

## D0/D2 Harness Definition

D0 coding harness:

- run the selected coding agent normally
- keep the same model/backend and tool limits
- collect trajectory, patch, tests, tool calls, and wall-clock time

D2 coding harness:

- run the same agent and limits
- add a Decision Layer sidecar inside the agent loop
- allow only authorized decision updates:
  - explicit task requirements from the issue/instructions
  - implementation commitments proposed by the agent and accepted by the harness
  - stable conclusions from failed tests when backed by observed test output
- inject the rendered Decision Brief before each planning/implementation turn

Decision examples for coding tasks:

- "The fix must preserve the public API of `Foo.bar`."
- "The failing behavior is in path normalization, not parser tokenization."
- "Do not change generated fixtures."
- "The implementation decision is to add regression coverage before changing the resolver."

Non-decisions:

- raw stack traces
- full test logs
- retrieved file contents
- guessed root causes without evidence
- final patch contents

## Canary Plan

Preflight status:

- SWE-bench local checkout and Python package install succeeded outside this
  repository under `/home/dev/benchmarks/SWE-bench`.
- Official SWE-bench gold-patch evaluation for `sympy__sympy-20590` completed
  successfully: 1/1 resolved, 0 errors.
- Docker Python access requires
  `DOCKER_HOST=unix:///run/user/1000/docker.sock` on this machine.

The next canary must test Decision Layer behavior:

1. Select 5-10 coding tasks with deterministic tests.
2. Run D0 once per task.
3. Run D2 once per task with the same backend/model.
4. Record:
   - pass/fail
   - tool calls
   - wall-clock time
   - prompt/completion tokens
   - number of accepted decisions
   - false decision audit
5. Continue only if D2 shows a signal without introducing false decisions.

## External Sources

- SWE-bench: https://arxiv.org/abs/2310.06770
- SWE-bench organization: https://github.com/swe-bench
- WildClawBench: https://arxiv.org/abs/2605.10912
- RoadmapBench: https://arxiv.org/abs/2605.15846
- TheAgentCompany: https://github.com/TheAgentCompany/TheAgentCompany
- METR time horizons: https://metr.org/time-horizons/
