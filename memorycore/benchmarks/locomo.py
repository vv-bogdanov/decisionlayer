from __future__ import annotations

from typing import Any

from memorycore.benchmarks.base import BenchmarkAdapter, BenchmarkExample, Message
from memorycore.benchmarks.json_loader import load_json_records


class LoCoMoBenchmark(BenchmarkAdapter):
    name = "locomo"

    def load(self) -> list[BenchmarkExample]:
        if self.data_path is None:
            raise ValueError("locomo requires data_path")
        examples: list[BenchmarkExample] = []
        for record in load_json_records(self.data_path):
            examples.extend(record_to_locomo_examples(record))
        return self.apply_window(examples)


def record_to_locomo_examples(record: dict[str, Any]) -> list[BenchmarkExample]:
    sample_id = str(record.get("sample_id") or len(str(record)))
    scope = f"locomo:{sample_id}"
    messages = parse_locomo_conversation(record, scope)
    examples = []
    for qa_index, qa in enumerate(record.get("qa") or []):
        if not isinstance(qa, dict):
            continue
        question = str(qa.get("question") or "")
        answer = qa.get("answer", "")
        if isinstance(answer, list):
            answer = answer[0] if answer else ""
        examples.append(
            BenchmarkExample(
                id=f"{sample_id}:qa:{qa_index}",
                scope=scope,
                messages=messages,
                question=question,
                expected_answer=str(answer),
                meta={
                    "benchmark": "locomo",
                    "sample_id": sample_id,
                    "qa_index": qa_index,
                    "category": qa.get("category"),
                    "evidence": list(qa.get("evidence") or []),
                    "question_type": f"category_{qa.get('category', 'unknown')}",
                },
            )
        )
    return examples


def parse_locomo_conversation(record: dict[str, Any], scope: str) -> list[Message]:
    conversation = record.get("conversation") or {}
    if not isinstance(conversation, dict):
        return []

    sample_id = str(record.get("sample_id") or "")
    messages: list[Message] = []
    session_numbers = sorted(
        {
            int(key.removeprefix("session_"))
            for key, value in conversation.items()
            if key.startswith("session_")
            and not key.endswith("_date_time")
            and key.removeprefix("session_").isdigit()
            and isinstance(value, list)
        }
    )
    for session_number in session_numbers:
        session_key = f"session_{session_number}"
        date_key = f"{session_key}_date_time"
        turns = conversation.get(session_key) or []
        if not isinstance(turns, list):
            continue
        for turn_index, turn in enumerate(turns):
            if not isinstance(turn, dict):
                continue
            content = turn.get("text") or turn.get("content") or turn.get("message")
            if not content:
                continue
            dia_id = turn.get("dia_id")
            messages.append(
                Message(
                    role=str(turn.get("speaker") or "user"),
                    content=str(content),
                    scope=scope,
                    meta={
                        "benchmark": "locomo",
                        "sample_id": sample_id,
                        "session_id": f"session_{session_number}",
                        "session_number": session_number,
                        "session_date_time": conversation.get(date_key),
                        "turn_index": turn_index,
                        "dia_id": dia_id,
                        "speaker": turn.get("speaker"),
                    },
                )
            )
    return messages
