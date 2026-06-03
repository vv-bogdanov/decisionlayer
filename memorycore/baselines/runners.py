from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from memorycore.benchmarks.base import BenchmarkExample
from memorycore.core.models import MemoryBrief, Ref
from memorycore.core.runtime import MemoryRuntime
from memorycore.policies.extraction import get_extractor, split_labelled_examples


@dataclass(slots=True)
class BaselineResult:
    answer: str
    brief: MemoryBrief | None
    trace: dict[str, object] | None


class BaselineRunner:
    name = "decisions_plus_facts"
    recall_policy = "decision_first"

    def __init__(
        self,
        *,
        extractor_policy: str = "rule_based",
        extractor_model: str = "gpt-4o-mini",
        extractor_url: str = "https://api.openai.com/v1/responses",
        extractor_max_facts: int = 12,
        extractor_max_decisions: int = 4,
        top_k_decisions: int = 5,
        top_k_facts: int = 5,
        include_refs: bool = False,
        refs_expansion_depth: int = 0,
        refs_expansion_limit: int = 10,
        max_memory_brief_tokens: int | None = None,
        forgetting_policy: str | None = None,
        forgetting_threshold: int | None = None,
        recall_count_weight: float = 0.05,
        keyword_weight: float = 1.0,
        recency_weight: float = 0.0,
        scope_weight: float = 0.25,
    ) -> None:
        self.extractor = get_extractor(
            extractor_policy,
            model=extractor_model,
            url=extractor_url,
            max_facts=extractor_max_facts,
            max_decisions=extractor_max_decisions,
        )
        self.top_k_decisions = top_k_decisions
        self.top_k_facts = top_k_facts
        self.include_refs = include_refs
        self.refs_expansion_depth = refs_expansion_depth
        self.refs_expansion_limit = refs_expansion_limit
        self.max_memory_brief_tokens = max_memory_brief_tokens
        self.forgetting_policy = forgetting_policy
        self.forgetting_threshold = forgetting_threshold
        self.recall_count_weight = recall_count_weight
        self.keyword_weight = keyword_weight
        self.recency_weight = recency_weight
        self.scope_weight = scope_weight

    def run(self, example: BenchmarkExample) -> BaselineResult:
        runtime = MemoryRuntime(
            recall_policy=self.recall_policy,
            recall_count_weight=self.recall_count_weight,
            keyword_weight=self.keyword_weight,
            recency_weight=self.recency_weight,
            scope_weight=self.scope_weight,
            forgetting_policy=self.forgetting_policy,
        )
        self.ingest(example, runtime)
        if self.forgetting_threshold is not None:
            runtime.forget_facts(threshold=self.forgetting_threshold)
        brief = runtime.recall(
            example.question,
            scope=example.scope,
            top_k_decisions=self.top_k_decisions,
            top_k_facts=self.top_k_facts,
            include_refs=self.include_refs,
            refs_expansion_depth=self.refs_expansion_depth,
            refs_expansion_limit=self.refs_expansion_limit,
            max_memory_brief_tokens=self.max_memory_brief_tokens,
        )
        answer = synthesize_answer(example.question, brief)
        return BaselineResult(answer=answer, brief=brief, trace=brief.trace.to_dict() if brief.trace else None)

    def ingest(self, example: BenchmarkExample, runtime: MemoryRuntime) -> None:
        for message in example.messages:
            scope = message.scope or example.scope
            raw = runtime.add_raw_input(message.content, scope=scope, source=message.role, meta=message.meta)
            extraction = self.extractor.extract(message.content, scope=scope, raw_input_id=raw.id)
            for fact in extraction.facts:
                tags = string_list(fact.get("tags"))
                if message.meta.get("benchmark") == "longmemeval" and "longmemeval" not in tags:
                    tags.append("longmemeval")
                runtime.add_fact(
                    str(fact["text"]),
                    scope=str(fact["scope"]),
                    tags=tags,
                    refs=ref_list(fact.get("refs")),
                    meta={
                        "source_role": message.role,
                        **message.meta,
                    },
                )
            for decision in extraction.decisions:
                if not decision.get("commit"):
                    runtime.add_fact(
                        f"Uncommitted decision candidate: {decision['key']} = {decision['value']}",
                        scope=str(decision["scope"]),
                        tags=["hypothesis"],
                        refs=ref_list(decision.get("refs")),
                    )
                    continue
                runtime.set_decision(
                    str(decision["key"]),
                    str(decision["value"]),
                    scope=str(decision["scope"]),
                    refs=ref_list(decision.get("refs")),
                    commit=True,
                )


class NoMemoryRunner(BaselineRunner):
    name = "no_memory"

    def run(self, example: BenchmarkExample) -> BaselineResult:
        return BaselineResult(answer="", brief=None, trace=None)


class RecentContextOnlyRunner(BaselineRunner):
    name = "recent_context_only"
    recall_policy = "recent_only"


class SimpleRagRunner(BaselineRunner):
    name = "simple_rag"
    recall_policy = "keyword"


class BM25Runner(BaselineRunner):
    name = "bm25"
    recall_policy = "bm25"


class TfIdfRunner(BaselineRunner):
    name = "tfidf"
    recall_policy = "tfidf"


class HybridRunner(BaselineRunner):
    name = "hybrid"
    recall_policy = "hybrid"


class FactOnlyRunner(BaselineRunner):
    name = "fact_only"
    recall_policy = "keyword"

    def ingest(self, example: BenchmarkExample, runtime: MemoryRuntime) -> None:
        super().ingest(example, runtime)
        runtime.store.decisions.clear()


class DecisionsOnlyRunner(BaselineRunner):
    name = "decisions_only"
    recall_policy = "decision_first"

    def ingest(self, example: BenchmarkExample, runtime: MemoryRuntime) -> None:
        super().ingest(example, runtime)
        runtime.store.facts.clear()


class DecisionsFactsRunner(BaselineRunner):
    name = "decisions_plus_facts"
    recall_policy = "decision_first"


class DecisionsFactsRefsRunner(BaselineRunner):
    name = "decisions_plus_facts_plus_refs"
    recall_policy = "decision_first"

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("include_refs", True)
        kwargs.setdefault("refs_expansion_depth", 1)
        super().__init__(**kwargs)


class DecisionsFactsRecallCountRunner(BaselineRunner):
    name = "decisions_plus_facts_plus_refs_plus_recall_count"
    recall_policy = "decision_first_with_recall_count"

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("include_refs", True)
        kwargs.setdefault("refs_expansion_depth", 1)
        super().__init__(**kwargs)


RUNNERS: dict[str, type[BaselineRunner]] = {
    "no_memory": NoMemoryRunner,
    "recent_context_only": RecentContextOnlyRunner,
    "full_context_where_possible": RecentContextOnlyRunner,
    "simple_rag": SimpleRagRunner,
    "fact_only": FactOnlyRunner,
    "decisions_only": DecisionsOnlyRunner,
    "decisions_facts": DecisionsFactsRunner,
    "decisions_plus_facts": DecisionsFactsRunner,
    "decisions_plus_facts_plus_refs": DecisionsFactsRefsRunner,
    "decisions_plus_facts_plus_refs_plus_recall_count": DecisionsFactsRecallCountRunner,
    "bm25": BM25Runner,
    "tfidf": TfIdfRunner,
    "hybrid": HybridRunner,
}


def get_baseline_runner(name: str, **kwargs: Any) -> BaselineRunner:
    try:
        runner_cls = RUNNERS[name]
    except KeyError as exc:
        known = ", ".join(sorted(RUNNERS))
        raise ValueError(f"unknown memory baseline: {name}; known: {known}") from exc
    return runner_cls(**kwargs)


def string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def ref_list(value: object) -> list[Ref]:
    if not isinstance(value, list):
        return []
    return cast(list[Ref], value)


def synthesize_answer(question: str, brief: MemoryBrief) -> str:
    query = question.lower()
    for decision in brief.decisions:
        key = decision.key.lower()
        if any(part and part in query for part in key.split(".")):
            return decision.value
    label_answer = synthesize_label_answer(question, brief)
    if label_answer is not None:
        return label_answer
    if brief.decisions:
        return brief.decisions[0].value
    if brief.facts:
        return brief.facts[0].text
    return ""


def synthesize_label_answer(question: str, brief: MemoryBrief) -> str | None:
    del question
    for fact in brief.facts:
        examples = split_labelled_examples(fact.text)
        if len(examples) == 1:
            return examples[0][1]
    return None
