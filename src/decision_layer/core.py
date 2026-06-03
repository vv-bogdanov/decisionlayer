from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Literal

Authority = Literal["user_commit", "user_confirmation", "manual_api_commit"]
DecisionAction = Literal["add", "replace", "remove"]

ALLOWED_AUTHORITIES: frozenset[str] = frozenset(
    {"user_commit", "user_confirmation", "manual_api_commit"}
)
MAX_DECISION_CHARS = 280
DEFAULT_BRIEF_INSTRUCTION = (
    "Use these decisions as current commitments. "
    "If decisions are conflicting, ambiguous, or outdated, ask the user for clarification "
    "before acting and then update the decision list."
)


class DecisionLayerError(ValueError):
    """Base error for invalid pure-core operations."""


class InvalidAuthorityError(DecisionLayerError):
    """Raised when a non-authorized source tries to change decisions."""


class DecisionNotFoundError(DecisionLayerError):
    """Raised when a requested decision id is not active."""


@dataclass(frozen=True, slots=True)
class Decision:
    id: str
    text: str
    meta: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id, "text": self.text, "meta": dict(self.meta)}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Decision:
        meta = data.get("meta")
        typed_meta = meta if isinstance(meta, dict) else {}
        return cls(
            id=str(data["id"]),
            text=str(data["text"]),
            meta={str(key): str(value) for key, value in typed_meta.items()},
        )


@dataclass(frozen=True, slots=True)
class DecisionState:
    decisions: tuple[Decision, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {"decisions": [decision.to_dict() for decision in self.decisions]}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> DecisionState:
        raw_decisions = data.get("decisions")
        if not isinstance(raw_decisions, list):
            return cls()
        return cls(tuple(Decision.from_dict(dict(item)) for item in raw_decisions))


@dataclass(frozen=True, slots=True)
class DecisionTrace:
    action: DecisionAction
    decision_id: str
    text: str
    authority: str
    source_id: str | None = None
    replaced_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "decision_id": self.decision_id,
            "text": self.text,
            "authority": self.authority,
            "source_id": self.source_id,
            "replaced_id": self.replaced_id,
        }


@dataclass(frozen=True, slots=True)
class DecisionBrief:
    decisions: tuple[Decision, ...]
    text: str
    token_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "decisions": [decision.to_dict() for decision in self.decisions],
            "text": self.text,
            "token_count": self.token_count,
        }


def add_decision(
    state: DecisionState,
    text: str,
    *,
    authority: Authority,
    decision_id: str | None = None,
    meta: dict[str, str] | None = None,
) -> tuple[DecisionState, DecisionTrace]:
    assert_authority(authority)
    normalized = normalize_decision_text(text)
    new_decision = Decision(
        id=decision_id or stable_decision_id(normalized),
        text=normalized,
        meta=dict(meta or {}),
    )
    active = tuple(decision for decision in state.decisions if decision.id != new_decision.id)
    next_state = DecisionState(active + (new_decision,))
    trace = DecisionTrace(
        action="add",
        decision_id=new_decision.id,
        text=new_decision.text,
        authority=authority,
        source_id=new_decision.meta.get("source_message_id"),
    )
    return next_state, trace


def replace_decision(
    state: DecisionState,
    decision_id: str,
    text: str,
    *,
    authority: Authority,
    new_decision_id: str | None = None,
    meta: dict[str, str] | None = None,
) -> tuple[DecisionState, DecisionTrace]:
    assert_authority(authority)
    if not any(decision.id == decision_id for decision in state.decisions):
        raise DecisionNotFoundError(f"active decision not found: {decision_id}")
    normalized = normalize_decision_text(text)
    replacement_meta = dict(meta or {})
    replacement_meta.setdefault("replaces", decision_id)
    replacement = Decision(
        id=new_decision_id or stable_decision_id(normalized),
        text=normalized,
        meta=replacement_meta,
    )
    active = tuple(decision for decision in state.decisions if decision.id != decision_id)
    next_state = DecisionState(active + (replacement,))
    trace = DecisionTrace(
        action="replace",
        decision_id=replacement.id,
        text=replacement.text,
        authority=authority,
        source_id=replacement.meta.get("source_message_id"),
        replaced_id=decision_id,
    )
    return next_state, trace


def remove_decision(
    state: DecisionState,
    decision_id: str,
    *,
    authority: Authority,
    source_id: str | None = None,
) -> tuple[DecisionState, DecisionTrace]:
    assert_authority(authority)
    removed = [decision for decision in state.decisions if decision.id == decision_id]
    if not removed:
        raise DecisionNotFoundError(f"active decision not found: {decision_id}")
    next_state = DecisionState(
        tuple(decision for decision in state.decisions if decision.id != decision_id)
    )
    trace = DecisionTrace(
        action="remove",
        decision_id=decision_id,
        text=removed[0].text,
        authority=authority,
        source_id=source_id,
    )
    return next_state, trace


def list_decisions(state: DecisionState) -> tuple[Decision, ...]:
    return state.decisions


def render_decision_brief(
    state: DecisionState,
    *,
    max_decisions: int = 12,
    max_tokens: int | None = None,
    instruction: str = DEFAULT_BRIEF_INSTRUCTION,
) -> DecisionBrief:
    selected: list[Decision] = []
    for decision in state.decisions[: max(max_decisions, 0)]:
        candidate = selected + [decision]
        text = render_brief_text(candidate, instruction=instruction)
        if max_tokens is not None and token_count(text) > max_tokens:
            break
        selected.append(decision)
    brief_text = render_brief_text(selected, instruction=instruction)
    return DecisionBrief(tuple(selected), brief_text, token_count(brief_text))


def render_brief_text(decisions: list[Decision], *, instruction: str) -> str:
    lines = ["Decision Brief", "", "Relevant decisions:"]
    if decisions:
        lines.extend(f"- {decision.text}" for decision in decisions)
    else:
        lines.append("- None")
    lines.extend(["", "Instruction:", instruction])
    return "\n".join(lines)


def normalize_decision_text(text: str) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        raise DecisionLayerError("decision text must not be empty")
    if len(normalized) > MAX_DECISION_CHARS:
        raise DecisionLayerError(f"decision text must be {MAX_DECISION_CHARS} characters or fewer")
    return normalized


def stable_decision_id(text: str) -> str:
    digest = sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"decision_{digest}"


def assert_authority(authority: str) -> None:
    if authority not in ALLOWED_AUTHORITIES:
        raise InvalidAuthorityError(f"decision authority is not allowed: {authority}")


def token_count(text: str) -> int:
    return len(text.split())
