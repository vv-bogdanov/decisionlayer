# Publishing Checklist

This project is a POC until the checklist below is complete.

## Local Release Gate

Run:

```bash
scripts/check
python3 -m benchmarks.adr_agent.run_suite --mode d0 --mode d1 --mode d2 --quiet
python3 -m benchmarks.adr_agent.report --run-id latest
```

`scripts/check` runs static checks, coverage, plugin validation when the local
validator is available, isolated lab checks, and a wheel install smoke test.

## CI Gate

GitHub Actions runs:

- `scripts/check --skip-lab --skip-build`
- `python3 -m benchmarks.adr_agent.run_suite --mode d0 --mode d1 --mode d2 --quiet`
- `scripts/check-wheel`

CI intentionally skips `scripts/codex-plugin-lab doctor`; that check requires a
local Codex CLI/plugin environment and should be run before a release tag.

## Before Public Release

- Choose and add a `LICENSE`.
- Re-run `scripts/codex-plugin-lab doctor`.
- Run `scripts/codex-plugin-lab runtime-smoke`. If it reports missing lab
  authentication, run `CODEX_HOME=.codex-lab/home codex login` and retry.
- Run one interactive lab session with `scripts/codex-plugin-lab interactive`
  and verify `hook-context` appears in `.codex-lab/repo-decisions-debug.jsonl`.
- Run ADR-agent fixture canaries with the selected agent command and save a
  short report under `benchmarks/adr_agent/reports/`.
- Tag the release only after `scripts/check`, `scripts/check-wheel`, and CI
  pass.
