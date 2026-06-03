from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from decision_layer.core import (
    DecisionState,
    add_decision,
    list_decisions,
    remove_decision,
    render_decision_brief,
    replace_decision,
)
from decision_layer.poc import PocConfig, PocMode, PocSuiteConfig, run_poc, run_poc_suite


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="decision-layer")
    parser.add_argument("--state", default="decision_state.json", help="Path to JSON state file.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("text")

    replace_parser = subparsers.add_parser("replace")
    replace_parser.add_argument("decision_id")
    replace_parser.add_argument("text")

    remove_parser = subparsers.add_parser("remove")
    remove_parser.add_argument("decision_id")

    subparsers.add_parser("list")
    subparsers.add_parser("brief")

    run_poc_parser = subparsers.add_parser("run-poc")
    run_poc_parser.add_argument("--data-root", required=True)
    run_poc_parser.add_argument("--output-dir", required=True)
    run_poc_parser.add_argument("--mode", choices=["D0", "D1", "D2"], required=True)
    run_poc_parser.add_argument("--tier", default="small")
    run_poc_parser.add_argument("--limit", type=int)
    run_poc_parser.add_argument("--oracle-decisions")

    run_suite_parser = subparsers.add_parser("run-suite")
    run_suite_parser.add_argument("--data-root", required=True)
    run_suite_parser.add_argument("--output-dir", required=True)
    run_suite_parser.add_argument("--tier", default="small")
    run_suite_parser.add_argument("--limit", type=int)
    run_suite_parser.add_argument("--oracle-decisions")

    args = parser.parse_args(argv)
    state_path = Path(args.state)
    state = load_state(state_path)

    if args.command == "add":
        state, trace = add_decision(state, args.text, authority="manual_api_commit")
        save_state(state_path, state)
        print(json.dumps(trace.to_dict(), ensure_ascii=False))
        return 0
    if args.command == "replace":
        state, trace = replace_decision(
            state,
            args.decision_id,
            args.text,
            authority="manual_api_commit",
        )
        save_state(state_path, state)
        print(json.dumps(trace.to_dict(), ensure_ascii=False))
        return 0
    if args.command == "remove":
        state, trace = remove_decision(state, args.decision_id, authority="manual_api_commit")
        save_state(state_path, state)
        print(json.dumps(trace.to_dict(), ensure_ascii=False))
        return 0
    if args.command == "list":
        print(
            json.dumps(
                [decision.to_dict() for decision in list_decisions(state)],
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "brief":
        print(render_decision_brief(state).text)
        return 0
    if args.command == "run-poc":
        result = run_poc(
            PocConfig(
                data_root=Path(args.data_root),
                output_dir=Path(args.output_dir),
                mode=cast(PocMode, args.mode),
                tier=args.tier,
                limit=args.limit,
                oracle_decisions_path=Path(args.oracle_decisions)
                if args.oracle_decisions
                else None,
            )
        )
        print(json.dumps(result.metrics, ensure_ascii=False))
        return 0
    if args.command == "run-suite":
        suite_result = run_poc_suite(
            PocSuiteConfig(
                data_root=Path(args.data_root),
                output_dir=Path(args.output_dir),
                tier=args.tier,
                limit=args.limit,
                oracle_decisions_path=Path(args.oracle_decisions)
                if args.oracle_decisions
                else None,
            )
        )
        print(json.dumps(suite_result.metrics, ensure_ascii=False))
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


def load_state(path: Path) -> DecisionState:
    if not path.exists():
        return DecisionState()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return DecisionState()
    return DecisionState.from_dict(data)


def save_state(path: Path, state: DecisionState) -> None:
    path.write_text(
        json.dumps(state.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
