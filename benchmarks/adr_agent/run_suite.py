from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from benchmarks.adr_agent.checks import DEFAULT_CASES, load_cases
from benchmarks.adr_agent.run_case import BRIEF_VARIANTS, DEFAULT_RESULTS, MODES, new_run_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adr-agent-run-suite")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--run-id")
    parser.add_argument("--source-dir", type=Path, help="Override case fixture with an external repository checkout")
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--mode", action="append", choices=MODES, dest="modes")
    parser.add_argument("--brief-variant", action="append", choices=BRIEF_VARIANTS, dest="brief_variants")
    parser.add_argument("--agent-command")
    parser.add_argument("--run-verify", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    case_ids = args.case_ids or sorted(case_id for case_id, case in cases.items() if case.fixture)
    modes = args.modes or list(MODES)
    brief_variants = args.brief_variants or ["standard"]
    run_id = args.run_id or new_run_id()
    print(f"run_id: {run_id}", flush=True)
    failures = 0
    for case_id in case_ids:
        if case_id not in cases:
            print(f"Unknown case: {case_id}", file=sys.stderr)
            failures += 1
            continue
        for mode in modes:
            for brief_variant in brief_variants:
                command = [
                    sys.executable,
                    "-m",
                    "benchmarks.adr_agent.run_case",
                    case_id,
                    "--cases",
                    str(args.cases),
                    "--results-dir",
                    str(args.results_dir),
                    "--run-id",
                    run_id,
                    "--mode",
                    mode,
                    "--brief-variant",
                    brief_variant,
                ]
                if args.source_dir:
                    command.extend(["--source-dir", str(args.source_dir)])
                if args.agent_command:
                    command.extend(["--agent-command", args.agent_command])
                if args.run_verify:
                    command.append("--run-verify")
                if not args.quiet:
                    print(f"running {case_id} {mode} {brief_variant}", flush=True)
                completed = subprocess.run(
                    command,
                    check=False,
                    stdout=subprocess.PIPE if args.quiet else None,
                    stderr=subprocess.STDOUT if args.quiet else None,
                    text=True,
                )
                if args.quiet and completed.returncode != 0 and completed.stdout:
                    print(completed.stdout, file=sys.stderr, end="")
                if completed.returncode != 0:
                    failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
