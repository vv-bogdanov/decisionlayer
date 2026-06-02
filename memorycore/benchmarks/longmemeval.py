from __future__ import annotations

from pathlib import Path
from typing import Any

from memorycore.benchmarks.base import BenchmarkAdapter, BenchmarkExample, Message
from memorycore.benchmarks.json_loader import load_json_records
from memorycore.benchmarks.toy import ToyBenchmark

PREFERRED_FILES = (
    "longmemeval_oracle.json",
    "longmemeval_s_cleaned.json",
    "longmemeval_s.json",
    "longmemeval_m_cleaned.json",
    "longmemeval_m.json",
)


class LongMemEvalBenchmark(BenchmarkAdapter):
    name = "longmemeval"

    def load(self) -> list[BenchmarkExample]:
        if self.data_path is None:
            examples = ToyBenchmark(limit=self.limit, offset=self.offset).load()
            for example in examples:
                example.meta["fixture"] = "tiny_longmemeval_compatible"
            return examples
        path = resolve_longmemeval_path(self.data_path)
        examples = [record_to_longmemeval_example(record) for record in load_json_records(path)]
        return self.apply_window(examples)


def resolve_longmemeval_path(path: Path) -> Path:
    if not path.is_dir():
        return path
    for filename in PREFERRED_FILES:
        candidate = path / filename
        if candidate.exists():
            return candidate
    return path


def record_to_longmemeval_example(record: dict[str, Any]) -> BenchmarkExample:
    question_id = str(record["question_id"])
    question_type = str(record.get("question_type") or "unknown")
    scope = f"longmemeval:{question_id}"
    return BenchmarkExample(
        id=question_id,
        scope=scope,
        messages=parse_haystack_sessions(record, scope),
        question=str(record.get("question") or ""),
        expected_answer=str(record.get("answer") or ""),
        meta={
            "benchmark": "longmemeval",
            "question_id": question_id,
            "question_type": question_type,
            "question_date": record.get("question_date"),
            "haystack_session_ids": list(record.get("haystack_session_ids") or []),
            "haystack_dates": list(record.get("haystack_dates") or []),
            "answer_session_ids": list(record.get("answer_session_ids") or []),
            "is_abstention": question_id.endswith("_abs") or question_type == "abstention",
        },
    )


def parse_haystack_sessions(record: dict[str, Any], scope: str) -> list[Message]:
    sessions = record.get("haystack_sessions") or []
    session_ids = list(record.get("haystack_session_ids") or [])
    dates = list(record.get("haystack_dates") or [])
    question_id = str(record.get("question_id") or "")
    question_type = str(record.get("question_type") or "unknown")
    answer_session_ids = list(record.get("answer_session_ids") or [])
    messages: list[Message] = []
    for session_index, session in enumerate(sessions):
        if not isinstance(session, list):
            continue
        session_id = session_ids[session_index] if session_index < len(session_ids) else str(session_index)
        date = dates[session_index] if session_index < len(dates) else None
        for turn_index, turn in enumerate(session):
            if not isinstance(turn, dict):
                continue
            content = turn.get("content")
            if not content:
                continue
            messages.append(
                Message(
                    role=str(turn.get("role") or "user"),
                    content=str(content),
                    scope=scope,
                    meta={
                        "benchmark": "longmemeval",
                        "question_id": question_id,
                        "question_type": question_type,
                        "session_id": session_id,
                        "session_index": session_index,
                        "turn_index": turn_index,
                        "date": date,
                        "has_answer": bool(turn.get("has_answer", False)),
                        "answer_session_ids": answer_session_ids,
                    },
                )
            )
    return messages
