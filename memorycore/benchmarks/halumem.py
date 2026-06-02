from __future__ import annotations

from typing import Any

from memorycore.benchmarks.base import BenchmarkAdapter, BenchmarkExample, Message
from memorycore.benchmarks.json_loader import load_json_records, record_to_example


class HaluMemBenchmark(BenchmarkAdapter):
    name = "halumem"

    def load(self) -> list[BenchmarkExample]:
        if self.data_path is None:
            raise ValueError("halumem requires data_path")
        examples: list[BenchmarkExample] = []
        for row_index, record in enumerate(load_json_records(self.data_path)):
            converted = record_to_halumem_examples(record, row_index=row_index)
            if converted:
                examples.extend(converted)
            else:
                examples.append(record_to_example(record, fallback_scope="benchmark:halumem"))
        return self.apply_window(examples)


def record_to_halumem_examples(record: dict[str, Any], *, row_index: int) -> list[BenchmarkExample]:
    memory_points = record.get("memory_points_all") or []
    if not isinstance(memory_points, list) or not memory_points:
        return []

    uuid = str(record.get("uuid") or row_index)
    scope = f"halumem:{uuid}"
    examples: list[BenchmarkExample] = []
    for point_index, point in enumerate(memory_points):
        if not isinstance(point, dict):
            continue
        memory_content = point.get("memory_content")
        if not memory_content:
            continue
        memory_index = point.get("index", point_index + 1)
        event_source = optional_int(point.get("event_source"))
        messages = parse_halumem_event_messages(record, scope=scope, event_source=event_source)
        messages.append(
            Message(
                role="memory",
                content=f"HaluMem memory point {memory_index}: {memory_content}",
                scope=scope,
                meta={
                    "benchmark": "halumem",
                    "uuid": uuid,
                    "source_kind": "memory_point",
                    "memory_index": memory_index,
                    "memory_type": point.get("memory_type"),
                    "is_update": parse_bool(point.get("is_update")),
                    "event_source": event_source,
                    "timestamp": point.get("timestamp"),
                    "importance": point.get("importance"),
                    "original_memories": list(point.get("original_memories") or []),
                },
            )
        )
        examples.append(
            BenchmarkExample(
                id=f"{uuid}:memory:{memory_index}",
                scope=scope,
                messages=messages,
                question=f"What is HaluMem memory point {memory_index}?",
                expected_answer=str(memory_content),
                meta={
                    "benchmark": "halumem",
                    "uuid": uuid,
                    "memory_index": memory_index,
                    "memory_type": point.get("memory_type"),
                    "is_update": parse_bool(point.get("is_update")),
                    "event_source": event_source,
                    "question_type": str(point.get("memory_type") or "memory_point"),
                },
            )
        )
    return examples


def parse_halumem_event_messages(
    record: dict[str, Any],
    *,
    scope: str,
    event_source: int | None,
) -> list[Message]:
    event_list = record.get("event_list") or []
    if not isinstance(event_list, list):
        return []

    messages: list[Message] = []
    for event in event_list:
        if not isinstance(event, dict):
            continue
        event_index = optional_int(event.get("event_index"))
        if event_source is not None and event_index != event_source:
            continue
        dialogue_info = event.get("dialogue_info") or {}
        if not isinstance(dialogue_info, dict):
            continue
        dialogue = dialogue_info.get("dialogue") or {}
        if not isinstance(dialogue, dict):
            continue
        for turn_key in sorted(dialogue):
            turn_items = dialogue.get(turn_key)
            if not isinstance(turn_items, list):
                continue
            timestamp = None
            for item in turn_items:
                if isinstance(item, dict) and "timestamp" in item:
                    timestamp = item.get("timestamp")
            for item_index, item in enumerate(turn_items):
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if not content:
                    continue
                messages.append(
                    Message(
                        role=str(item.get("role") or "user"),
                        content=str(content),
                        scope=scope,
                        meta={
                            "benchmark": "halumem",
                            "source_kind": "dialogue",
                            "event_index": event_index,
                            "event_type": event.get("event_type"),
                            "event_name": event.get("event_name"),
                            "event_time": event.get("event_time"),
                            "turn_key": turn_key,
                            "turn_item_index": item_index,
                            "timestamp": timestamp,
                        },
                    )
                )
    return messages


def optional_int(value: object) -> int | None:
    if value in {None, ""}:
        return None
    if not isinstance(value, (str, int, float)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}
