from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

DecisionCommandAction = Literal["add", "replace", "remove"]

AUTHORIZED_ROLES = frozenset({"user"})
AUTHORIZED_SOURCE_KINDS = frozenset({"chat", "manual_api"})
WEAK_MARKERS = (
    "maybe",
    "possibly",
    "could consider",
    "worth thinking",
    "not sure",
    "может быть",
    "возможно",
    "стоит подумать",
    "можно рассмотреть",
    "подумаем",
    "интересный вариант",
)
ADD_PATTERNS = (
    re.compile(
        r"^\s*(?:let'?s\s+commit|commit|decide|we choose|choose)\s*:?\s*(?P<text>.+)$",
        re.I,
    ),
    re.compile(r"^\s*goal\s*:?\s*(?P<text>.+)$", re.I),
    re.compile(r"^\s*(?:фиксируем|решаем|выбираем|бер[её]м|цель)\s*:?\s*(?P<text>.+)$", re.I),
)
REPLACE_PATTERNS = (
    re.compile(
        r"^\s*(?:change\s+the\s+decision|replace\s+the\s+decision|replace\s+decision)"
        r"\s*:?\s*(?P<text>.+)$",
        re.I,
    ),
    re.compile(r"^\s*(?:меняем\s+решение|переходим\s+на)\s*:?\s*(?P<text>.+)$", re.I),
)
REMOVE_PATTERNS = (
    re.compile(r"^\s*(?:remove\s+decision|drop\s+decision)\s*:?\s*(?P<text>.+)$", re.I),
    re.compile(r"^\s*(?:удаляем\s+решение|отказываемся\s+от)\s*:?\s*(?P<text>.+)$", re.I),
)


@dataclass(frozen=True, slots=True)
class SourceMessage:
    id: str
    role: str
    content: str
    source_kind: str = "chat"


@dataclass(frozen=True, slots=True)
class DecisionCommand:
    action: DecisionCommandAction
    text: str
    source_message_id: str
    reason: str


class RuleBasedDecisionExtractor:
    name = "rule_based"

    def extract(self, message: SourceMessage) -> tuple[DecisionCommand, ...]:
        if message.role not in AUTHORIZED_ROLES:
            return ()
        if message.source_kind not in AUTHORIZED_SOURCE_KINDS:
            return ()
        content = " ".join(message.content.split())
        if not content or contains_weak_marker(content):
            return ()
        pattern_groups: tuple[tuple[DecisionCommandAction, tuple[re.Pattern[str], ...]], ...] = (
            ("replace", REPLACE_PATTERNS),
            ("remove", REMOVE_PATTERNS),
            ("add", ADD_PATTERNS),
        )
        for action, patterns in pattern_groups:
            text = first_pattern_text(content, patterns)
            if text:
                return (
                    DecisionCommand(
                        action=action,
                        text=text,
                        source_message_id=message.id,
                        reason=f"{action}_commit_signal",
                    ),
                )
        return ()


def contains_weak_marker(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in WEAK_MARKERS)


def first_pattern_text(text: str, patterns: tuple[re.Pattern[str], ...]) -> str | None:
    for pattern in patterns:
        match = pattern.match(text)
        if match:
            return match.group("text").strip()
    return None
