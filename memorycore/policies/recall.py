from __future__ import annotations

import re
from dataclasses import dataclass

from memorycore.core.models import Decision, Fact
from memorycore.core.store import MemoryStore

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


def keyword_score(query: str, text: str) -> float:
    query_tokens = tokenize(query)
    if not query_tokens:
        return 0.0
    text_tokens = tokenize(text)
    if not text_tokens:
        return 0.0
    overlap = query_tokens & text_tokens
    return len(overlap) / len(query_tokens)


@dataclass(slots=True)
class SelectedItem:
    item: Decision | Fact
    score: float
    reason: str


class RecallPolicy:
    name = "keyword"

    def select(
        self,
        *,
        context: str,
        store: MemoryStore,
        scope: str | None,
        top_k_decisions: int,
        top_k_facts: int,
    ) -> tuple[list[SelectedItem], list[SelectedItem]]:
        decisions = self.select_decisions(context, store, scope, top_k_decisions)
        facts = self.select_facts(context, store, scope, top_k_facts)
        return decisions, facts

    def select_decisions(
        self,
        context: str,
        store: MemoryStore,
        scope: str | None,
        top_k: int,
    ) -> list[SelectedItem]:
        scored = []
        for decision in store.get_decisions(scope):
            text = f"{decision.key} {decision.value} {decision.scope}"
            score = keyword_score(context, text)
            scored.append(SelectedItem(decision, score, "keyword decision match"))
        return self._top(scored, top_k)

    def select_facts(
        self,
        context: str,
        store: MemoryStore,
        scope: str | None,
        top_k: int,
    ) -> list[SelectedItem]:
        scored = []
        for fact in store.get_facts(scope):
            score = keyword_score(context, fact.text)
            scored.append(SelectedItem(fact, score, "keyword fact match"))
        return self._top(scored, top_k)

    def _top(self, items: list[SelectedItem], limit: int) -> list[SelectedItem]:
        if limit <= 0:
            return []
        positive = [item for item in items if item.score > 0]
        source = positive if positive else items
        return sorted(source, key=lambda item: item.score, reverse=True)[:limit]


class RecentOnlyRecall(RecallPolicy):
    name = "recent_only"

    def select_decisions(
        self,
        context: str,
        store: MemoryStore,
        scope: str | None,
        top_k: int,
    ) -> list[SelectedItem]:
        return []

    def select_facts(
        self,
        context: str,
        store: MemoryStore,
        scope: str | None,
        top_k: int,
    ) -> list[SelectedItem]:
        facts = store.get_facts(scope)
        selected = list(reversed(facts))[: max(top_k, 0)]
        return [SelectedItem(fact, 1.0, "recent fact") for fact in selected]


class DecisionFirstRecall(RecallPolicy):
    name = "decision_first"

    def select_decisions(
        self,
        context: str,
        store: MemoryStore,
        scope: str | None,
        top_k: int,
    ) -> list[SelectedItem]:
        decisions = store.get_decisions(scope)
        scored = []
        for decision in decisions:
            text = f"{decision.key} {decision.value} {decision.scope}"
            score = keyword_score(context, text)
            if scope and decision.scope == scope:
                score += 0.25
            scored.append(SelectedItem(decision, score, "decision-first priority"))
        return self._top(scored, top_k)


class DecisionFirstWithRecallCount(DecisionFirstRecall):
    name = "decision_first_with_recall_count"

    def select_facts(
        self,
        context: str,
        store: MemoryStore,
        scope: str | None,
        top_k: int,
    ) -> list[SelectedItem]:
        scored = []
        for fact in store.get_facts(scope):
            score = keyword_score(context, fact.text) + min(fact.recall_count, 10) * 0.05
            scored.append(SelectedItem(fact, score, "keyword plus recall_count"))
        return self._top(scored, top_k)


def get_recall_policy(name: str | None) -> RecallPolicy:
    if name in {None, "keyword"}:
        return RecallPolicy()
    if name == "recent_only":
        return RecentOnlyRecall()
    if name == "decision_first":
        return DecisionFirstRecall()
    if name == "decision_first_with_recall_count":
        return DecisionFirstWithRecallCount()
    raise ValueError(f"unknown recall policy: {name}")

