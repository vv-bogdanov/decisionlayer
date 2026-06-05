from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from benchmarks.adr_agent.checks import DEFAULT_CASES, load_cases
from benchmarks.adr_agent.run_case import DEFAULT_RESULTS, MODES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adr-agent-run-suite")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--mode", action="append", choices=MODES, dest="modes")
    parser.add_argument("--agent-command")
    parser.add_argument("--run-verify", action="store_true")
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    case_ids = args.case_ids or sorted(cases)
    modes = args.modes or list(MODES)
    failures = 0
    for case_id in case_ids:
        if case_id not in cases:
            print(f"Unknown case: {case_id}", file=sys.stderr)
            failures += 1
            continue
        for mode in modes:
            command = [
                sys.executable,
                "-m",
                "benchmarks.adr_agent.run_case",
                case_id,
                "--cases",
                str(args.cases),
                "--results-dir",
                str(args.results_dir),
                "--mode",
                mode,
            ]
            if args.agent_command:
                command.extend(["--agent-command", args.agent_command])
            if args.run_verify:
                command.append("--run-verify")
            print(f"running {case_id} {mode}", flush=True)
            completed = subprocess.run(command, check=False)
            if completed.returncode != 0:
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
