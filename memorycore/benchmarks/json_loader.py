from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from memorycore.benchmarks.base import BenchmarkExample, Message


def load_json_records(path: Path) -> list[dict[str, Any]]:
    if path.is_dir():
        records: list[dict[str, Any]] = []
        for child in sorted(path.glob("*.json")):
            records.extend(load_json_records(child))
        for child in sorted(path.glob("*.jsonl")):
            records.extend(load_json_records(child))
        return records

    if path.suffix == ".jsonl":
        rows = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    rows.append(json.loads(stripped))
        return rows

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return data
    for key in ("data", "examples", "records", "questions"):
        value = data.get(key)
        if isinstance(value, list):
            return value
    return [data]


def record_to_example(record: dict[str, Any], *, fallback_scope: str) -> BenchmarkExample:
    example_id = str(record.get("id") or record.get("question_id") or record.get("qid") or len(str(record)))
    scope = str(record.get("scope") or fallback_scope)
    messages = parse_messages(record, scope)
    question = str(record.get("question") or record.get("query") or record.get("input") or "")
    expected = record.get("expected_answer", record.get("answer", record.get("target", "")))
    if isinstance(expected, list):
        expected = expected[0] if expected else ""
    return BenchmarkExample(
        id=example_id,
        scope=scope,
        messages=messages,
        question=question,
        expected_answer=str(expected),
        meta={key: value for key, value in record.items() if key not in {"messages", "question", "answer"}},
    )


def parse_messages(record: dict[str, Any], scope: str) -> list[Message]:
    raw_messages = (
        record.get("messages") or record.get("conversation") or record.get("history") or record.get("sessions") or []
    )
    messages: list[Message] = []
    if isinstance(raw_messages, str):
        return [Message(role="user", content=raw_messages, scope=scope)]
    if not isinstance(raw_messages, list):
        return messages

    for item in raw_messages:
        if isinstance(item, str):
            messages.append(Message(role="user", content=item, scope=scope))
            continue
        if not isinstance(item, dict):
            continue
        if "messages" in item and isinstance(item["messages"], list):
            for nested in item["messages"]:
                if isinstance(nested, dict):
                    content = nested.get("content") or nested.get("text") or nested.get("message") or ""
                    role = str(nested.get("role") or nested.get("speaker") or "user")
                    if content:
                        messages.append(Message(role=role, content=str(content), scope=scope, meta=nested))
            continue
        content = item.get("content") or item.get("text") or item.get("message") or ""
        role = str(item.get("role") or item.get("speaker") or "user")
        if content:
            messages.append(Message(role=role, content=str(content), scope=scope, meta=item))
    return messages
