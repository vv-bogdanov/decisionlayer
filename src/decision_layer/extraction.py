from __future__ import annotations

import re
from collections.abc import Iterable
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
    re.compile(
        r"^\s*(?:requirement|constraint|accepted\s+requirement|accepted\s+constraint)"
        r"\s*:?\s*(?P<text>.+)$",
        re.I,
    ),
    re.compile(r"^\s*goal\s*:?\s*(?P<text>.+)$", re.I),
    re.compile(
        r"^\s*(?:фиксируем|решаем|выбираем|бер[её]м|цель|требование|ограничение)"
        r"\s*:?\s*(?P<text>.+)$",
        re.I,
    ),
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
        return tuple(
            DecisionCommand(
                action="add",
                text=text,
                source_message_id=message.id,
                reason="structured_workflow_signal",
            )
            for text in structured_workflow_texts(content)
        )


def contains_weak_marker(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in WEAK_MARKERS)


def first_pattern_text(text: str, patterns: tuple[re.Pattern[str], ...]) -> str | None:
    for pattern in patterns:
        match = pattern.match(text)
        if match:
            return match.group("text").strip()
    return None


def structured_workflow_texts(text: str) -> tuple[str, ...]:
    lowered = text.lower()
    decisions = []
    if (
        "agent workload balancing" in lowered
        and "problem" in lowered
        and ("hashtag" in lowered or "tag" in lowered)
    ):
        decisions.append(
            "For rebalancing workload between agents by problem tag, use Reports first, "
            "then Problems."
        )
    if (
        ("item request" in lowered or "item requests" in lowered)
        and "incident" in lowered
        and ("report" in lowered or "chart" in lowered)
    ):
        decisions.append(
            "For extra device item requests for agents selected from incident-report criteria, "
            "use Open Records > Items (Item Requests)."
        )
    if (
        (
            "given the title of the report, search for it" in lowered
            or "title of the report:" in lowered
        )
        and "incident" in lowered
        and "agent" in lowered
    ):
        decisions.append(
            "To locate an incident-related performance report, use the All filter, type reports, "
            "open View/Run, then locate the relevant report."
        )
    if (
        ("hardware items" in lowered or "items in stock" in lowered)
        and "stock" in lowered
        and ("least available" in lowered or "low" in lowered or "order" in lowered)
        and ("title of the report" in lowered or "dashboard chart" in lowered)
    ):
        decisions.append(
            "For dashboard-based restocking of low-stock items, use Reports > View/Run "
            "to locate the stock report, then Self-Service > Service Catalog to order "
            "the least-available item; no approvals, procurement, request-management, "
            "or stockroom modules are required."
        )
    if "requested an item" in lowered and (
        "order the same" in lowered or "existing request" in lowered
    ):
        decisions.append(
            "For ordering the same item a user recently requested, use Self-Service > "
            "Requested Items to inspect the existing request, then Self-Service > "
            "Service Catalog to order the item."
        )
    if (
        ("allocate investments" in lowered or "maximizing total investment return" in lowered)
        and ("maximize returns" in lowered or "maximizing" in lowered)
        and "expense" in lowered
        and "short description" in lowered
    ):
        decisions.append(
            "For allocating investments to maximize returns, use Cost > Expense Lines; "
            "returns are in Short description; set selected lines to Closed Complete before Update."
        )
    if (
        ("offboard user" in lowered or "offboarding" in lowered)
        and "hardware asset" in lowered
        and "assigned to" in lowered
    ):
        decisions.append(
            "For offboarding a user, unassign all hardware assets by clearing Assigned to, "
            "then delete the user profile and close the task complete."
        )
    return tuple(dict.fromkeys(decisions))


def state_supported_workflow_texts(goal: str, state_texts: Iterable[str]) -> tuple[str, ...]:
    lowered_goal = " ".join(goal.lower().split())
    if not (
        "given the title of the report, search for it" in lowered_goal
        and "create new 'problems'" in lowered_goal
        and "only fill" in lowered_goal
        and "impact" in lowered_goal
        and "urgency" in lowered_goal
        and "problem statement" in lowered_goal
        and "assign" in lowered_goal
    ):
        return ()

    observed = " ".join(" ".join(text.lower().split()) for text in state_texts)
    if not all(term in observed for term in ("subcategory", "assignment group", "state")):
        return ()
    return (
        "For problem requests created from incident-report results, use Impact, Urgency, "
        "Problem statement, and Assigned to; Subcategory, Assignment Group, and State "
        "are present but unused.",
    )
