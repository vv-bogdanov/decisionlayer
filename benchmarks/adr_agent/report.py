from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchmarks.adr_agent.run_case import DEFAULT_RESULTS, MODES


STATUS_ORDER = {"passed": 0, "failed": 1, "prepared": 2}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adr-agent-report")
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--run-id", default="latest")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    run_dir = _select_run_dir(args.results_dir, args.run_id)
    results = _load_results(run_dir)
    if not results:
        print(f"No result.json files found under {run_dir}")
        return 1

    report = build_report(run_dir, results)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
        print(args.out)
    else:
        print(report, end="")
    return 0


def build_report(run_dir: Path, results: list[dict[str, Any]]) -> str:
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%SZ")
    lines = [
        "# ADR-Agent Canary Report",
        "",
        f"- Run: `{run_dir.name}`",
        f"- Generated: {generated}",
        f"- Results: `{run_dir}`",
        "",
        "## Summary",
        "",
        "| Mode | Prepared | Passed | Failed | Total |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for mode in MODES:
        mode_results = [item for item in results if item.get("mode") == mode]
        prepared = sum(1 for item in mode_results if item.get("status") == "prepared")
        passed = sum(1 for item in mode_results if item.get("status") == "passed")
        failed = sum(1 for item in mode_results if item.get("status") == "failed")
        lines.append(f"| `{mode}` | {prepared} | {passed} | {failed} | {len(mode_results)} |")

    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| Case | Variant | d0 | d1 | d2 | Notes |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    case_variants = sorted({(str(item.get("case_id")), _brief_variant(item)) for item in results})
    for case_id, variant in case_variants:
        cells = []
        notes = []
        for mode in MODES:
            item = _find_result(results, case_id, mode, variant)
            if not item:
                cells.append("-")
                continue
            status = str(item.get("status"))
            cells.append(status)
            failures = item.get("checks", {}).get("failures", [])
            if failures:
                notes.append(f"{mode}: {'; '.join(str(failure) for failure in failures)}")
        lines.append(f"| `{case_id}` | `{variant}` | {' | '.join(cells)} | {_escape_cell(' '.join(notes)) or '-'} |")

    lines.extend(
        [
            "",
            "## Metrics",
            "",
            "| Case | Mode | Variant | Prompt chars | Duration | Diff size | Files | ADR files | Tool calls | Writes |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in sorted(results, key=lambda value: (str(value.get("case_id")), str(value.get("mode")), _brief_variant(value))):
        metrics = item.get("metrics", {})
        lines.append(
            "| "
            f"`{item.get('case_id')}` | `{item.get('mode')}` | "
            f"`{_brief_variant(item)}` | "
            f"{metrics.get('prompt_chars', '-')} | "
            f"{metrics.get('duration_sec', '-')} | "
            f"{metrics.get('diff_size', '-')} | "
            f"{metrics.get('changed_files', '-')} | "
            f"{metrics.get('changed_adr_files', '-')} | "
            f"{metrics.get('tool_calls', '-')} | "
            f"{metrics.get('write_events', '-')} |"
        )

    if any(item.get("status") == "prepared" for item in results):
        lines.extend(
            [
                "",
                "## Notes",
                "",
                "- `prepared` means the workspace and effective prompt were generated, but no agent command was run.",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def _select_run_dir(results_dir: Path, run_id: str) -> Path:
    if run_id != "latest":
        return results_dir / run_id
    candidates = [path for path in results_dir.iterdir() if path.is_dir()] if results_dir.exists() else []
    if not candidates:
        raise FileNotFoundError(f"No run directories under {results_dir}")
    return sorted(candidates)[-1]


def _load_results(run_dir: Path) -> list[dict[str, Any]]:
    results = []
    for path in sorted(run_dir.glob("*/*/result.json")):
        results.append(json.loads(path.read_text(encoding="utf-8")))
    return results


def _find_result(results: list[dict[str, Any]], case_id: str, mode: str, brief_variant: str) -> dict[str, Any] | None:
    for item in results:
        if item.get("case_id") == case_id and item.get("mode") == mode and _brief_variant(item) == brief_variant:
            return item
    return None


def _brief_variant(item: dict[str, Any]) -> str:
    return str(item.get("brief_variant") or "standard")


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|")


if __name__ == "__main__":
    raise SystemExit(main())
