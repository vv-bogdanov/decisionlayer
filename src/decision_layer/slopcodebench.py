from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DECISION_KEYWORDS = (
    "must",
    "required",
    "requires",
    "default",
    "priority",
    "sort",
    "order",
    "always",
    "never",
    "inclusive",
    "exclusive",
    "deterministic",
    "case-sensitive",
    "exit",
    "stdout",
    "stderr",
    "json",
    "event",
    "error",
    "checksum",
    "preserve",
    "omit",
    "emit",
    "validate",
    "reject",
)


@dataclass(frozen=True)
class CheckpointSummary:
    mode: str
    problem: str
    checkpoint: str
    passed: bool
    passed_tests: int
    total_tests: int
    infrastructure_failure: bool
    pytest_exit_code: int | None
    cost: float | None
    steps: int | None
    decisions: int
    runtime_error: str | None


def strip_benchmark_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    trimmed = text[: max_chars - 1].rsplit(" ", 1)[0].rstrip(".,;:")
    return f"{trimmed}."


def _normalize_markdown_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^#{1,6}\s+", "", line)
    line = re.sub(r"^[-*+]\s+", "", line)
    line = re.sub(r"^\d+[.)]\s+", "", line)
    line = line.replace("%%%ENTRYPOINT:entry_file%%%", "the benchmark entry file")
    line = line.replace("%%%ENTRYPOINT:entry_command%%%", "the benchmark entry command")
    line = line.strip("` ")
    return _compact(line)


def _is_candidate_decision(line: str) -> bool:
    if len(line) < 16:
        return False
    lowered = line.lower()
    if lowered.startswith(("example", "given ", "input", "output", "configuration")):
        return False
    if lowered in {"deliverables", "examples", "notes", "request format"}:
        return False
    if any(keyword in lowered for keyword in DECISION_KEYWORDS):
        return True
    if "|" in line and ("required" in lowered or "`" in line):
        return True
    return False


def extract_decisions_from_spec(
    spec_text: str,
    *,
    checkpoint_name: str,
    max_decisions: int = 24,
    max_chars: int = 220,
) -> list[str]:
    """Extract short accepted requirements from an authoritative checkpoint spec.

    This is intentionally conservative and deterministic. It is not a general
    memory extractor; it creates a POC Decision Brief from benchmark specs that
    have already passed the configured policy.
    """

    clean = strip_benchmark_comments(spec_text)
    decisions = [f"{checkpoint_name}: preserve all behavior accepted by this checkpoint"]
    seen = {decisions[0].lower()}

    in_fence = False
    for raw_line in clean.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        line = _normalize_markdown_line(raw_line)
        if not line or line.startswith("|---") or line.startswith("---"):
            continue
        if not _is_candidate_decision(line):
            continue

        decision = _truncate(f"{checkpoint_name}: {line}", max_chars)
        key = decision.lower()
        if key in seen:
            continue
        decisions.append(decision)
        seen.add(key)
        if len(decisions) >= max_decisions:
            break

    return decisions


def merge_decisions(
    existing: list[str], new_decisions: list[str], *, max_total: int = 160
) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for decision in [*existing, *new_decisions]:
        compacted = _compact(decision)
        if not compacted:
            continue
        key = compacted.lower()
        if key in seen:
            continue
        merged.append(compacted)
        seen.add(key)
        if len(merged) >= max_total:
            break
    return merged


def format_decision_brief(decisions: list[str]) -> str:
    if not decisions:
        return ""
    lines = [
        "Decision Brief from prior accepted checkpoints:",
        (
            "Keep these decisions while solving the current checkpoint. "
            "If the current checkpoint explicitly changes one, it wins."
        ),
    ]
    lines.extend(f"- {decision}" for decision in decisions)
    return "\n".join(lines)


def load_json_list(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, str)]


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def evaluation_passed_all_cases(data: dict[str, Any]) -> bool:
    if data.get("infrastructure_failure"):
        return False
    if data.get("pytest_exit_code") not in (0, None):
        return False
    totals = data.get("total_counts", {})
    passes = data.get("pass_counts", {})
    if not isinstance(totals, dict) or not isinstance(passes, dict):
        return False
    if sum(int(value or 0) for value in totals.values()) <= 0:
        return False
    return all(
        int(passes.get(group, 0) or 0) >= int(total or 0)
        for group, total in totals.items()
    )


def _usage_from_checkpoint(checkpoint_dir: Path) -> tuple[float | None, int | None]:
    path = checkpoint_dir / "inference_result.json"
    if not path.exists():
        return None, None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None, None
    usage = data.get("usage", {})
    if not isinstance(usage, dict):
        return None, None
    cost = usage.get("cost")
    steps = usage.get("steps")
    return (
        float(cost) if isinstance(cost, int | float) else None,
        int(steps) if isinstance(steps, int) else None,
    )


def _extract_runtime_error_field(event: str, field: str) -> str | None:
    match = re.search(rf"{field}=([\"'])(.*?)\1", event)
    if not match:
        return None
    return match.group(2)


def _problem_runtime_error(problem_dir: Path) -> str | None:
    path = problem_dir / "infer.log"
    if not path.exists():
        return None
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return None
    for line in lines:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        event = data.get("event")
        if data.get("level") != "error" or not isinstance(event, str):
            continue
        if "Error running problem" not in event:
            continue
        error_type = _extract_runtime_error_field(event, "error_type")
        error_message = _extract_runtime_error_field(event, "error_message")
        if error_type and error_message:
            return _truncate(f"{error_type}: {error_message}", 240)
        return _truncate(event, 240)
    return None


def _decision_count(problem_dir: Path, checkpoint: str) -> int:
    path = problem_dir / "decision_layer" / "checkpoint_decisions" / f"{checkpoint}.json"
    return len(load_json_list(path))


def collect_checkpoint_summaries(run_root: Path, modes: list[str]) -> list[CheckpointSummary]:
    summaries: list[CheckpointSummary] = []
    for mode in modes:
        mode_dir = run_root / mode
        if not mode_dir.exists():
            continue
        for problem_dir in sorted(path for path in mode_dir.iterdir() if path.is_dir()):
            runtime_error = _problem_runtime_error(problem_dir)
            for checkpoint_dir in sorted(problem_dir.glob("checkpoint_*")):
                evaluation_path = checkpoint_dir / "evaluation.json"
                if not evaluation_path.exists():
                    continue
                try:
                    evaluation = json.loads(evaluation_path.read_text())
                except (OSError, json.JSONDecodeError):
                    continue
                totals = evaluation.get("total_counts", {})
                passes = evaluation.get("pass_counts", {})
                total_tests = (
                    sum(int(value or 0) for value in totals.values())
                    if isinstance(totals, dict)
                    else 0
                )
                passed_tests = (
                    sum(int(value or 0) for value in passes.values())
                    if isinstance(passes, dict)
                    else 0
                )
                cost, steps = _usage_from_checkpoint(checkpoint_dir)
                infrastructure_failure = (
                    bool(evaluation.get("infrastructure_failure"))
                    or runtime_error is not None
                )
                summaries.append(
                    CheckpointSummary(
                        mode=mode,
                        problem=problem_dir.name,
                        checkpoint=checkpoint_dir.name,
                        passed=(
                            evaluation_passed_all_cases(evaluation)
                            and runtime_error is None
                        ),
                        passed_tests=passed_tests,
                        total_tests=total_tests,
                        infrastructure_failure=infrastructure_failure,
                        pytest_exit_code=evaluation.get("pytest_exit_code"),
                        cost=cost,
                        steps=steps,
                        decisions=_decision_count(problem_dir, checkpoint_dir.name),
                        runtime_error=runtime_error,
                    )
                )
    return summaries


def summarize_run(run_root: Path, modes: list[str]) -> dict[str, Any]:
    rows = collect_checkpoint_summaries(run_root, modes)
    by_mode: dict[str, dict[str, Any]] = {}
    for mode in modes:
        mode_rows = [row for row in rows if row.mode == mode]
        by_mode[mode] = {
            "checkpoints": len(mode_rows),
            "passed": sum(1 for row in mode_rows if row.passed),
            "infra_errors": sum(1 for row in mode_rows if row.infrastructure_failure),
            "cost": round(sum(row.cost or 0 for row in mode_rows), 6),
            "steps": sum(row.steps or 0 for row in mode_rows),
        }

    lookup = {(row.problem, row.checkpoint, row.mode): row for row in rows}
    keys = sorted({(row.problem, row.checkpoint) for row in rows})
    deltas = []
    for problem, checkpoint in keys:
        d0 = lookup.get((problem, checkpoint, "D0"))
        d1 = lookup.get((problem, checkpoint, "D1"))
        if not d0 or not d1 or d0.passed == d1.passed:
            continue
        deltas.append(
            {
                "problem": problem,
                "checkpoint": checkpoint,
                "winner": "D1" if d1.passed else "D0",
                "d0": d0.passed,
                "d1": d1.passed,
            }
        )

    return {
        "run_root": str(run_root),
        "modes": by_mode,
        "deltas": deltas,
        "checkpoints": [asdict(row) for row in rows],
    }


def render_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# SlopCodeBench D0/D1 Summary",
        "",
        f"Run root: `{summary['run_root']}`",
        "",
        "## Mode Totals",
        "",
        "| Mode | Passed | Checkpoints | Infra Errors | Cost | Steps |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for mode, data in summary["modes"].items():
        lines.append(
            "| {mode} | {passed} | {checkpoints} | {infra_errors} | {cost} | {steps} |".format(
                mode=mode,
                **data,
            )
        )

    lines.extend(
        [
            "",
            "## Deltas",
            "",
            "| Problem | Checkpoint | Winner | D0 | D1 |",
            "|---|---|---|---:|---:|",
        ]
    )
    if summary["deltas"]:
        for delta in summary["deltas"]:
            lines.append(
                "| {problem} | {checkpoint} | {winner} | {d0} | {d1} |".format(**delta)
            )
    else:
        lines.append("| - | - | none | - | - |")

    lines.extend(
        [
            "",
            "## Checkpoint Matrix",
            "",
            (
                "| Mode | Problem | Checkpoint | Passed | Tests | Infra | Steps | "
                "Decisions | Runtime Error |"
            ),
            "|---|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in summary["checkpoints"]:
        display_row = {**row, "runtime_error": row.get("runtime_error") or ""}
        lines.append(
            (
                "| {mode} | {problem} | {checkpoint} | {passed} | "
                "{passed_tests}/{total_tests} | {infrastructure_failure} | "
                "{steps} | {decisions} | {runtime_error} |"
            ).format(**display_row)
        )
    return "\n".join(lines) + "\n"


def write_summary_files(run_root: Path, modes: list[str]) -> dict[str, Any]:
    summary = summarize_run(run_root, modes)
    save_json(run_root / "summary.json", summary)
    (run_root / "summary.md").write_text(render_summary_markdown(summary))
    return summary
