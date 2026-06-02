from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass(slots=True)
class Message:
    role: str
    content: str
    scope: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BenchmarkExample:
    id: str
    scope: str
    messages: list[Message]
    question: str
    expected_answer: str
    meta: dict[str, Any] = field(default_factory=dict)


class BenchmarkAdapter:
    name = "base"

    def __init__(self, data_path: str | None = None) -> None:
        self.data_path = Path(data_path) if data_path else None

    def load(self) -> list[BenchmarkExample]:
        raise NotImplementedError

    def iter_examples(self) -> Iterable[BenchmarkExample]:
        yield from self.load()

