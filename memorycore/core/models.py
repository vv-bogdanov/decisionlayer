from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Ref:
    target: str
    rel: str = "related"
    weight: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {"target": self.target, "rel": self.rel, "weight": self.weight}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Ref":
        return cls(
            target=str(data["target"]),
            rel=str(data.get("rel", "related")),
            weight=float(data.get("weight", 1.0)),
        )


@dataclass(slots=True)
class RawInput:
    text: str
    scope: str
    source: str = "input"
    meta: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("raw"))
    kind: str = "raw_input"
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "text": self.text,
            "scope": self.scope,
            "source": self.source,
            "meta": self.meta,
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class Fact:
    text: str
    scope: str
    tags: list[str] = field(default_factory=list)
    refs: list[Ref] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    recall_count: int = 0
    id: str = field(default_factory=lambda: new_id("fact"))
    kind: str = "fact"
    archived: bool = False
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "text": self.text,
            "scope": self.scope,
            "recall_count": self.recall_count,
            "tags": list(self.tags),
            "refs": [ref.to_dict() for ref in self.refs],
            "meta": self.meta,
            "archived": self.archived,
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class Decision:
    key: str
    value: str
    scope: str
    refs: list[Ref] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("decision"))
    kind: str = "decision"
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "key": self.key,
            "value": self.value,
            "scope": self.scope,
            "refs": [ref.to_dict() for ref in self.refs],
            "meta": self.meta,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(slots=True)
class TraceSelection:
    id: str
    kind: str
    score: float
    reason: str
    refs: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "score": self.score,
            "reason": self.reason,
            "refs": list(self.refs),
        }


@dataclass(slots=True)
class RecallTrace:
    query: str
    scope: str | None
    policy: str
    decisions: list[TraceSelection] = field(default_factory=list)
    facts: list[TraceSelection] = field(default_factory=list)
    related_refs: list[dict[str, Any]] = field(default_factory=list)
    recall_count_updates: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "scope": self.scope,
            "policy": self.policy,
            "decisions": [item.to_dict() for item in self.decisions],
            "facts": [item.to_dict() for item in self.facts],
            "related_refs": list(self.related_refs),
            "recall_count_updates": list(self.recall_count_updates),
        }


@dataclass(slots=True)
class MemoryBrief:
    decisions: list[Decision]
    facts: list[Fact]
    related_facts: list[Fact] = field(default_factory=list)
    trace: RecallTrace | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decisions": [decision.to_dict() for decision in self.decisions],
            "facts": [fact.to_dict() for fact in self.facts],
            "related_facts": [fact.to_dict() for fact in self.related_facts],
            "trace": self.trace.to_dict() if self.trace else None,
        }

    def render(self) -> str:
        lines: list[str] = []
        if self.decisions:
            lines.append("Decisions:")
            for decision in self.decisions:
                lines.append(f"- {decision.scope}:{decision.key} = {decision.value}")
        if self.facts:
            lines.append("Facts:")
            for fact in self.facts:
                lines.append(f"- {fact.text}")
        if self.related_facts:
            lines.append("Related facts:")
            for fact in self.related_facts:
                lines.append(f"- {fact.text}")
        return "\n".join(lines)
