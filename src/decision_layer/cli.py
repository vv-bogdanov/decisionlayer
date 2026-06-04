from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import cast

from decision_layer.canary_runner import CanaryRunConfig, run_opencode_canary
from decision_layer.core import (
    DecisionState,
    add_decision,
    list_decisions,
    remove_decision,
    render_decision_brief,
    replace_decision,
)
from decision_layer.patch_verifier import verify_patch
from decision_layer.poc import (
    DEFAULT_CONTEXT_MAX_CHARS,
    PocConfig,
    PocMode,
    PocSuiteConfig,
    run_poc,
    run_poc_suite,
)
from decision_layer.readers import ReaderKind


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
    run_poc_parser.add_argument("--question-id", action="append", default=[])
    run_poc_parser.add_argument("--question-id-file", action="append", default=[])
    add_reader_arguments(run_poc_parser)
    run_poc_parser.add_argument("--oracle-decisions")
    run_poc_parser.add_argument("--accepted-decisions")

    run_suite_parser = subparsers.add_parser("run-suite")
    run_suite_parser.add_argument("--data-root", required=True)
    run_suite_parser.add_argument("--output-dir", required=True)
    run_suite_parser.add_argument("--tier", default="small")
    run_suite_parser.add_argument("--limit", type=int)
    run_suite_parser.add_argument("--question-id", action="append", default=[])
    run_suite_parser.add_argument("--question-id-file", action="append", default=[])
    add_reader_arguments(run_suite_parser)
    run_suite_parser.add_argument("--oracle-decisions")
    run_suite_parser.add_argument("--accepted-decisions")

    verify_patch_parser = subparsers.add_parser("verify-patch")
    verify_patch_parser.add_argument(
        "--patch", required=True, help="Path to a unified diff, or '-'."
    )
    verify_patch_parser.add_argument("--require-term", action="append", default=[])
    verify_patch_parser.add_argument("--require-file", action="append", default=[])
    verify_patch_parser.add_argument("--allow-file", action="append", default=[])

    run_canary_parser = subparsers.add_parser("run-opencode-canary")
    run_canary_parser.add_argument("--workspace", required=True)
    run_canary_parser.add_argument("--prompt", required=True)
    run_canary_parser.add_argument("--guard-bin", required=True)
    run_canary_parser.add_argument("--log", required=True)
    run_canary_parser.add_argument("--stderr", required=True)
    run_canary_parser.add_argument("--time", required=True)
    run_canary_parser.add_argument("--patch", required=True)
    run_canary_parser.add_argument("--verifier-json")
    run_canary_parser.add_argument("--model", default="llama.cpp/qwen36-35b-a3b-udiq3s")
    run_canary_parser.add_argument("--timeout-seconds", type=float, default=600.0)
    run_canary_parser.add_argument("--opencode-bin", default="opencode")
    run_canary_parser.add_argument("--require-term", action="append", default=[])
    run_canary_parser.add_argument("--require-file", action="append", default=[])
    run_canary_parser.add_argument("--allow-file", action="append", default=[])

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
                question_ids=load_question_ids(args.question_id, args.question_id_file),
                reader=cast(ReaderKind, args.reader),
                reader_base_url=args.reader_base_url,
                reader_model=args.reader_model,
                reader_timeout_seconds=args.reader_timeout_seconds,
                reader_max_tokens=args.reader_max_tokens,
                context_max_chars=args.context_max_chars,
                resume=not args.no_resume,
                oracle_decisions_path=Path(args.oracle_decisions)
                if args.oracle_decisions
                else None,
                accepted_decisions_path=Path(args.accepted_decisions)
                if args.accepted_decisions
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
                question_ids=load_question_ids(args.question_id, args.question_id_file),
                reader=cast(ReaderKind, args.reader),
                reader_base_url=args.reader_base_url,
                reader_model=args.reader_model,
                reader_timeout_seconds=args.reader_timeout_seconds,
                reader_max_tokens=args.reader_max_tokens,
                context_max_chars=args.context_max_chars,
                resume=not args.no_resume,
                oracle_decisions_path=Path(args.oracle_decisions)
                if args.oracle_decisions
                else None,
                accepted_decisions_path=Path(args.accepted_decisions)
                if args.accepted_decisions
                else None,
            )
        )
        print(json.dumps(suite_result.metrics, ensure_ascii=False))
        return 0
    if args.command == "verify-patch":
        patch_text = (
            sys.stdin.read() if args.patch == "-" else Path(args.patch).read_text(encoding="utf-8")
        )
        verification = verify_patch(
            patch_text,
            required_terms=tuple(args.require_term),
            required_files=tuple(args.require_file),
            allowed_files=tuple(args.allow_file),
        )
        print(json.dumps(verification.to_dict(), ensure_ascii=False))
        return 0 if verification.ok else 1
    if args.command == "run-opencode-canary":
        canary_result = run_opencode_canary(
            CanaryRunConfig(
                workspace=Path(args.workspace),
                prompt_path=Path(args.prompt),
                guard_bin=Path(args.guard_bin),
                log_path=Path(args.log),
                stderr_path=Path(args.stderr),
                time_path=Path(args.time),
                patch_path=Path(args.patch),
                verifier_json_path=Path(args.verifier_json) if args.verifier_json else None,
                model=args.model,
                timeout_seconds=args.timeout_seconds,
                opencode_bin=args.opencode_bin,
                required_terms=tuple(args.require_term),
                required_files=tuple(args.require_file),
                allowed_files=tuple(args.allow_file),
            )
        )
        print(json.dumps(canary_result.to_dict(), ensure_ascii=False))
        return 0 if canary_result.ok else 1
    raise AssertionError(f"unhandled command: {args.command}")


def add_reader_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--reader", choices=["smoke", "openai-chat"], default="smoke")
    parser.add_argument("--reader-base-url", default="http://127.0.0.1:18080/v1")
    parser.add_argument("--reader-model")
    parser.add_argument("--reader-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--reader-max-tokens", type=int, default=64)
    parser.add_argument("--context-max-chars", type=int, default=DEFAULT_CONTEXT_MAX_CHARS)
    parser.add_argument("--no-resume", action="store_true")


def load_question_ids(inline_ids: list[str], file_paths: list[str]) -> tuple[str, ...]:
    ids = list(inline_ids)
    for file_path in file_paths:
        for line in Path(file_path).read_text(encoding="utf-8").splitlines():
            question_id = line.split("#", 1)[0].strip()
            if question_id:
                ids.append(question_id)
    return tuple(dict.fromkeys(ids))


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
