from __future__ import annotations

import re
from dataclasses import dataclass
from math import log, sqrt

from memorycore.core.models import Decision, Fact
from memorycore.core.store import MemoryStore

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def keyword_score(query: str, text: str) -> float:
    query_tokens = set(tokenize(query))
    if not query_tokens:
        return 0.0
    text_tokens = set(tokenize(text))
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

    def __init__(
        self,
        *,
        keyword_weight: float = 1.0,
        recall_count_weight: float = 0.05,
        recency_weight: float = 0.0,
        scope_weight: float = 0.25,
    ) -> None:
        self.keyword_weight = keyword_weight
        self.recall_count_weight = recall_count_weight
        self.recency_weight = recency_weight
        self.scope_weight = scope_weight

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
            score = self.keyword_weight * keyword_score(context, text)
            if scope and decision.scope == scope:
                score += self.scope_weight
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
        facts = store.get_facts(scope)
        total = max(len(facts) - 1, 1)
        for index, fact in enumerate(facts):
            recency_boost = (index / total) * self.recency_weight if facts else 0.0
            score = self.keyword_weight * keyword_score(context, fact.text) + recency_boost
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
            score = self.keyword_weight * keyword_score(context, text)
            if scope and decision.scope == scope:
                score += self.scope_weight
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
            score = (
                self.keyword_weight * keyword_score(context, fact.text)
                + min(fact.recall_count, 10) * self.recall_count_weight
            )
            scored.append(SelectedItem(fact, score, "keyword plus recall_count"))
        return self._top(scored, top_k)


class BM25Recall(RecallPolicy):
    name = "bm25"

    def select_facts(
        self,
        context: str,
        store: MemoryStore,
        scope: str | None,
        top_k: int,
    ) -> list[SelectedItem]:
        facts = store.get_facts(scope)
        scores = bm25_scores(context, [fact.text for fact in facts])
        return self._top(
            [
                SelectedItem(
                    fact,
                    scores[index] + min(fact.recall_count, 10) * self.recall_count_weight,
                    "bm25 fact match",
                )
                for index, fact in enumerate(facts)
            ],
            top_k,
        )


class TfIdfVectorRecall(RecallPolicy):
    name = "tfidf_vector"

    def select_facts(
        self,
        context: str,
        store: MemoryStore,
        scope: str | None,
        top_k: int,
    ) -> list[SelectedItem]:
        facts = store.get_facts(scope)
        scores = tfidf_cosine_scores(context, [fact.text for fact in facts])
        return self._top(
            [
                SelectedItem(
                    fact,
                    scores[index] + min(fact.recall_count, 10) * self.recall_count_weight,
                    "tfidf vector fact match",
                )
                for index, fact in enumerate(facts)
            ],
            top_k,
        )


class HybridRecall(DecisionFirstRecall):
    name = "hybrid"

    def select_facts(
        self,
        context: str,
        store: MemoryStore,
        scope: str | None,
        top_k: int,
    ) -> list[SelectedItem]:
        facts = store.get_facts(scope)
        bm25 = bm25_scores(context, [fact.text for fact in facts])
        tfidf = tfidf_cosine_scores(context, [fact.text for fact in facts])
        scored = []
        for index, fact in enumerate(facts):
            score = (
                self.keyword_weight * keyword_score(context, fact.text)
                + bm25[index]
                + tfidf[index]
                + min(fact.recall_count, 10) * self.recall_count_weight
            )
            scored.append(SelectedItem(fact, score, "hybrid keyword/bm25/tfidf fact match"))
        return self._top(scored, top_k)


def bm25_scores(query: str, documents: list[str], *, k1: float = 1.5, b: float = 0.75) -> list[float]:
    if not documents:
        return []
    query_terms = tokenize(query)
    doc_terms = [tokenize(document) for document in documents]
    avg_len = sum(len(terms) for terms in doc_terms) / len(doc_terms) if doc_terms else 0.0
    doc_freq: dict[str, int] = {}
    for terms in doc_terms:
        for term in set(terms):
            doc_freq[term] = doc_freq.get(term, 0) + 1
    scores = []
    for terms in doc_terms:
        term_counts: dict[str, int] = {}
        for term in terms:
            term_counts[term] = term_counts.get(term, 0) + 1
        score = 0.0
        doc_len = len(terms) or 1
        for term in query_terms:
            tf = term_counts.get(term, 0)
            if not tf:
                continue
            idf = log((len(documents) - doc_freq.get(term, 0) + 0.5) / (doc_freq.get(term, 0) + 0.5) + 1)
            denom = tf + k1 * (1 - b + b * doc_len / (avg_len or 1))
            score += idf * (tf * (k1 + 1)) / denom
        scores.append(score)
    return scores


def tfidf_cosine_scores(query: str, documents: list[str]) -> list[float]:
    if not documents:
        return []
    doc_terms = [tokenize(document) for document in documents]
    query_terms = tokenize(query)
    doc_freq: dict[str, int] = {}
    for terms in doc_terms:
        for term in set(terms):
            doc_freq[term] = doc_freq.get(term, 0) + 1
    idf = {
        term: log((1 + len(documents)) / (1 + count)) + 1
        for term, count in doc_freq.items()
    }
    query_vector = tfidf_vector(query_terms, idf)
    return [cosine(query_vector, tfidf_vector(terms, idf)) for terms in doc_terms]


def tfidf_vector(terms: list[str], idf: dict[str, float]) -> dict[str, float]:
    counts: dict[str, int] = {}
    for term in terms:
        counts[term] = counts.get(term, 0) + 1
    return {term: count * idf.get(term, 0.0) for term, count in counts.items()}


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(term, 0.0) for term, value in left.items())
    left_norm = sqrt(sum(value * value for value in left.values()))
    right_norm = sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def get_recall_policy(
    name: str | None,
    *,
    keyword_weight: float = 1.0,
    recall_count_weight: float = 0.05,
    recency_weight: float = 0.0,
    scope_weight: float = 0.25,
) -> RecallPolicy:
    kwargs = {
        "keyword_weight": keyword_weight,
        "recall_count_weight": recall_count_weight,
        "recency_weight": recency_weight,
        "scope_weight": scope_weight,
    }
    if name in {None, "keyword"}:
        return RecallPolicy(**kwargs)
    if name == "recent_only":
        return RecentOnlyRecall(**kwargs)
    if name == "decision_first":
        return DecisionFirstRecall(**kwargs)
    if name == "decision_first_with_recall_count":
        return DecisionFirstWithRecallCount(**kwargs)
    if name == "bm25":
        return BM25Recall(**kwargs)
    if name in {"tfidf", "tfidf_vector"}:
        return TfIdfVectorRecall(**kwargs)
    if name == "hybrid":
        return HybridRecall(**kwargs)
    raise ValueError(f"unknown recall policy: {name}")
