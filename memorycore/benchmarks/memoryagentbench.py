from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from memorycore.benchmarks.base import BenchmarkAdapter, BenchmarkExample, Message
from memorycore.benchmarks.json_loader import load_json_records

DOCUMENT_RE = re.compile(r"(?m)^Document\s+(?P<index>\d+):\s*")


class MemoryAgentBenchBenchmark(BenchmarkAdapter):
    name = "memoryagentbench"

    def load(self) -> list[BenchmarkExample]:
        if self.data_path is None:
            raise ValueError("memoryagentbench requires data_path")
        examples: list[BenchmarkExample] = []
        for row_index, record in enumerate(load_memoryagentbench_records(self.data_path)):
            examples.extend(record_to_memoryagentbench_examples(record, row_index=row_index))
        return self.apply_window(examples)


def load_memoryagentbench_records(path: Path) -> list[dict[str, Any]]:
    if path.is_dir():
        records: list[dict[str, Any]] = []
        for pattern in ("*.json", "*.jsonl", "*.parquet"):
            for child in sorted(path.glob(pattern)):
                records.extend(load_memoryagentbench_records(child))
        return records
    if path.suffix == ".parquet":
        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError("MemoryAgentBench parquet files require pandas in the experiments extra") from exc
        try:
            frame = pd.read_parquet(path)
        except ImportError as exc:
            raise RuntimeError(
                "MemoryAgentBench parquet files require pyarrow or fastparquet. "
                "Use `uv run --extra experiments ...` after syncing the experiments extra."
            ) from exc
        return list(frame.to_dict(orient="records"))
    return load_json_records(path)


def record_to_memoryagentbench_examples(record: dict[str, Any], *, row_index: int) -> list[BenchmarkExample]:
    questions = normalize_list(first_present(record, "questions", "question", "queries"))
    answers = normalize_list(first_present(record, "answers", "answer", "targets"))
    if not questions:
        return []
    metadata = metadata_dict(record)
    scope = f"memoryagentbench:{metadata.get('source') or row_index}"
    base_messages = parse_memoryagentbench_messages(record, scope)
    examples = []
    qa_pair_ids = normalize_list(metadata.get("qa_pair_ids"))
    question_ids = normalize_list(metadata.get("question_ids"))
    question_types = normalize_list(metadata.get("question_types"))
    question_dates = normalize_list(metadata.get("question_dates"))
    keypoints = normalize_list(metadata.get("keypoints"))
    for question_index, question in enumerate(questions):
        expected_answers = answer_options_at(answers, question_index)
        expected = expected_answers[0] if expected_answers else ""
        qa_pair_id = str(value_at(qa_pair_ids, question_index, f"row_{row_index}_q_{question_index}"))
        examples.append(
            BenchmarkExample(
                id=qa_pair_id,
                scope=scope,
                messages=base_messages,
                question=str(question),
                expected_answer=expected,
                meta={
                    "benchmark": "memoryagentbench",
                    "row_index": row_index,
                    "qa_pair_id": qa_pair_id,
                    "question_id": value_at(question_ids, question_index),
                    "question_type": value_at(question_types, question_index, metadata.get("source")),
                    "question_date": value_at(question_dates, question_index),
                    "keypoint": value_at(keypoints, question_index),
                    "expected_answers": expected_answers,
                    "source": metadata.get("source"),
                },
            )
        )
    return examples


def parse_memoryagentbench_messages(record: dict[str, Any], scope: str) -> list[Message]:
    metadata = metadata_dict(record)
    haystack_sessions = metadata.get("haystack_sessions")
    messages: list[Message] = []
    flatten_haystack_messages(haystack_sessions, scope=scope, messages=messages)
    if messages:
        return messages
    context = record.get("context")
    if context:
        return parse_context_documents(str(context), scope=scope, source=metadata.get("source"))
    return []


def parse_context_documents(context: str, *, scope: str, source: object) -> list[Message]:
    matches = list(DOCUMENT_RE.finditer(context))
    if not matches:
        return [
            Message(
                role="context",
                content=context,
                scope=scope,
                meta={
                    "benchmark": "memoryagentbench",
                    "source_kind": "context",
                    "source": source,
                },
            )
        ]

    messages: list[Message] = []
    for match_index, match in enumerate(matches):
        start = match.end()
        end = matches[match_index + 1].start() if match_index + 1 < len(matches) else len(context)
        content = context[start:end].strip()
        if not content:
            continue
        messages.append(
            Message(
                role="context",
                content=content,
                scope=scope,
                meta={
                    "benchmark": "memoryagentbench",
                    "source_kind": "context_document",
                    "source": source,
                    "document_index": int(match.group("index")),
                },
            )
        )
    return messages


def flatten_haystack_messages(
    value: object,
    *,
    scope: str,
    messages: list[Message],
    session_index: int | None = None,
    turn_index: int | None = None,
) -> None:
    if isinstance(value, dict):
        content = value.get("content")
        if content:
            messages.append(
                Message(
                    role=str(value.get("role") or "user"),
                    content=str(content),
                    scope=scope,
                    meta={
                        "benchmark": "memoryagentbench",
                        "source_kind": "haystack_session",
                        "session_index": session_index,
                        "turn_index": turn_index,
                        "has_answer": bool(value.get("has_answer", False)),
                    },
                )
            )
    elif isinstance(value, list):
        for index, item in enumerate(value):
            next_session = session_index if session_index is not None else index
            next_turn = index if session_index is not None else None
            flatten_haystack_messages(
                item,
                scope=scope,
                messages=messages,
                session_index=next_session,
                turn_index=next_turn,
            )


def normalize_list(value: object) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        converted = tolist()
        return converted if isinstance(converted, list) else [converted]
    return [value]


def first_present(record: dict[str, Any], *keys: str) -> object:
    for key in keys:
        if key in record and record[key] is not None:
            return record[key]
    return None


def value_at(values: list[Any], index: int, default: object = None) -> object:
    if index < len(values):
        return values[index]
    return default


def answer_at(answers: list[Any], index: int) -> str:
    options = answer_options_at(answers, index)
    return options[0] if options else ""


def answer_options_at(answers: list[Any], index: int) -> list[str]:
    return [str(item) for item in flatten_answer_values(value_at(answers, index, "")) if str(item)]


def flatten_answer_values(value: object) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        flattened: list[Any] = []
        for item in value:
            flattened.extend(flatten_answer_values(item))
        return flattened
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        return flatten_answer_values(tolist())
    return [value]


def metadata_dict(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("metadata")
    return value if isinstance(value, dict) else {}
