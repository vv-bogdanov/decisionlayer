# ADR-Agent Harness

Small deterministic canaries for checking whether a coding agent respects
repository ADRs. This is a regression and prompt-selection harness, not a
replacement for an external benchmark.

Prepare a case without running an agent:

```bash
python3 -m benchmarks.adr_agent.run_case format-preservation-add-adr
```

Run a case with an agent command. The command may use `{workspace}`,
`{prompt_file}`, `{debug_log}`, and `{repo_root}` placeholders:

```bash
python3 -m benchmarks.adr_agent.run_case format-preservation-add-adr \
  --agent-command '{repo_root}/scripts/repo-decisions --root {workspace} codex -- "$(cat {prompt_file})"'
```

Results are written under `benchmarks/adr_agent/runs/`.
