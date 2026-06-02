from __future__ import annotations

from dataclasses import dataclass

from memorycore.benchmarks.base import BenchmarkExample
from memorycore.core.models import MemoryBrief
from memorycore.core.runtime import MemoryRuntime
from memorycore.policies.extraction import get_extractor


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
        top_k_decisions: int = 5,
        top_k_facts: int = 5,
    ) -> None:
        self.extractor = get_extractor(extractor_policy)
        self.top_k_decisions = top_k_decisions
        self.top_k_facts = top_k_facts

    def run(self, example: BenchmarkExample) -> BaselineResult:
        runtime = MemoryRuntime(recall_policy=self.recall_policy)
        self.ingest(example, runtime)
        brief = runtime.recall(
            example.question,
            scope=example.scope,
            top_k_decisions=self.top_k_decisions,
            top_k_facts=self.top_k_facts,
        )
        answer = synthesize_answer(example.question, brief)
        return BaselineResult(answer=answer, brief=brief, trace=brief.trace.to_dict() if brief.trace else None)

    def ingest(self, example: BenchmarkExample, runtime: MemoryRuntime) -> None:
        for message in example.messages:
            scope = message.scope or example.scope
            raw = runtime.add_raw_input(message.content, scope=scope, source=message.role, meta=message.meta)
            extraction = self.extractor.extract(message.content, scope=scope, raw_input_id=raw.id)
            for fact in extraction.facts:
                runtime.add_fact(
                    str(fact["text"]),
                    scope=str(fact["scope"]),
                    tags=list(fact.get("tags", [])),
                    refs=list(fact.get("refs", [])),
                )
            for decision in extraction.decisions:
                if not decision.get("commit"):
                    runtime.add_fact(
                        f"Uncommitted decision candidate: {decision['key']} = {decision['value']}",
                        scope=str(decision["scope"]),
                        tags=["hypothesis"],
                        refs=list(decision.get("refs", [])),
                    )
                    continue
                runtime.set_decision(
                    str(decision["key"]),
                    str(decision["value"]),
                    scope=str(decision["scope"]),
                    refs=list(decision.get("refs", [])),
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


class DecisionsFactsRecallCountRunner(BaselineRunner):
    name = "decisions_plus_facts_plus_refs_plus_recall_count"
    recall_policy = "decision_first_with_recall_count"


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
}


def get_baseline_runner(name: str, **kwargs: object) -> BaselineRunner:
    try:
        runner_cls = RUNNERS[name]
    except KeyError as exc:
        known = ", ".join(sorted(RUNNERS))
        raise ValueError(f"unknown memory baseline: {name}; known: {known}") from exc
    return runner_cls(**kwargs)


def synthesize_answer(question: str, brief: MemoryBrief) -> str:
    query = question.lower()
    for decision in brief.decisions:
        key = decision.key.lower()
        if any(part and part in query for part in key.split(".")):
            return decision.value
    if brief.decisions:
        return brief.decisions[0].value
    if brief.facts:
        return brief.facts[0].text
    return ""
