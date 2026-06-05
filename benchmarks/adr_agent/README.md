# ADR-Agent Harness

Small deterministic canaries for checking whether a coding agent respects
repository ADRs. This is a regression and prompt-selection harness, not a
replacement for an external benchmark.

Prepare a case without running an agent:

```bash
python3 -m benchmarks.adr_agent.run_case format-preservation-add-adr
python3 -m benchmarks.adr_agent.run_suite
```

Run a case with an agent command. The command may use `{workspace}`,
`{prompt_file}`, `{effective_prompt_file}`, `{debug_log}`, `{mode}`, and
`{repo_root}` placeholders:

```bash
python3 -m benchmarks.adr_agent.run_case format-preservation-add-adr \
  --mode d1 \
  --agent-command 'codex exec --cd {workspace} "$(cat {effective_prompt_file})"'
```

Modes:

- `d0`: task prompt only.
- `d1`: accepted ADR brief prepended to the task.
- `d2`: accepted ADR brief plus explicit repo-decisions MCP tool guidance. The
  agent command still has to run in an environment where the MCP server is
  available, such as the isolated Codex plugin lab.

For wrapper-fallback testing specifically, run `d0` and let the wrapper add the
brief:

```bash
python3 -m benchmarks.adr_agent.run_case format-preservation-add-adr \
  --mode d0 \
  --agent-command '{repo_root}/scripts/repo-decisions --root {workspace} codex -- "$(cat {prompt_file})"'
```

Results are written under `benchmarks/adr_agent/runs/`.
