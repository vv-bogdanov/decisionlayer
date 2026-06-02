from __future__ import annotations

from memorycore.core.models import Decision, Fact, MemoryBrief, RawInput, RecallTrace, Ref, TraceSelection
from memorycore.core.store import MemoryStore
from memorycore.policies.forgetting import ForgettingPolicy, get_forgetting_policy
from memorycore.policies.recall import RecallPolicy, SelectedItem, get_recall_policy
from memorycore.policies.safety import SafetyPolicy, get_safety_policy


class MemoryRuntime:
    def __init__(
        self,
        *,
        store: MemoryStore | None = None,
        recall_policy: RecallPolicy | str | None = None,
        forgetting_policy: ForgettingPolicy | str | None = None,
        safety_policy: SafetyPolicy | str | None = None,
        recall_count_weight: float = 0.05,
        keyword_weight: float = 1.0,
        recency_weight: float = 0.0,
        scope_weight: float = 0.25,
    ) -> None:
        self.store = store or MemoryStore()
        self.recall_policy = (
            get_recall_policy(
                recall_policy,
                recall_count_weight=recall_count_weight,
                keyword_weight=keyword_weight,
                recency_weight=recency_weight,
                scope_weight=scope_weight,
            )
            if isinstance(recall_policy, str) or recall_policy is None
            else recall_policy
        )
        self.forgetting_policy = (
            get_forgetting_policy(forgetting_policy)
            if isinstance(forgetting_policy, str) or forgetting_policy is None
            else forgetting_policy
        )
        self.safety_policy = (
            get_safety_policy(safety_policy)
            if isinstance(safety_policy, str) or safety_policy is None
            else safety_policy
        )
        self.traces: list[RecallTrace] = []

    def add_raw_input(
        self,
        text: str,
        *,
        scope: str,
        source: str = "input",
        meta: dict[str, object] | None = None,
    ) -> RawInput:
        raw_input = RawInput(text=text, scope=scope, source=source, meta=dict(meta or {}))
        return self.store.add_raw_input(raw_input)

    def add_fact(
        self,
        text: str,
        *,
        scope: str,
        tags: list[str] | None = None,
        refs: list[Ref] | None = None,
        meta: dict[str, object] | None = None,
    ) -> Fact:
        fact = Fact(
            text=text,
            scope=scope,
            tags=list(tags or []),
            refs=list(refs or []),
            meta=dict(meta or {}),
        )
        return self.store.add_fact(fact)

    def set_decision(
        self,
        key: str,
        value: str,
        *,
        scope: str,
        refs: list[Ref] | None = None,
        meta: dict[str, object] | None = None,
        commit: bool = False,
    ) -> Decision:
        self.safety_policy.validate_decision(key=key, value=value, scope=scope, commit=commit)
        decision = Decision(
            key=key,
            value=value,
            scope=scope,
            refs=list(refs or []),
            meta=dict(meta or {}),
        )
        previous = self.store.set_decision(decision)
        if previous is not None:
            history_refs = list(refs or [])
            history_refs.append(Ref(target=previous.id, rel="replaces"))
            self.add_fact(
                f"Decision {scope}:{key} changed: {previous.value} -> {value}.",
                scope=scope,
                tags=["history", "decision_change"],
                refs=history_refs,
                meta={
                    "decision_key": key,
                    "old_value": previous.value,
                    "new_value": value,
                    "previous_decision_id": previous.id,
                    "new_decision_id": decision.id,
                },
            )
        return decision

    def recall(
        self,
        context: str,
        *,
        scope: str | None = None,
        top_k_decisions: int = 5,
        top_k_facts: int = 5,
        include_refs: bool = False,
        refs_expansion_depth: int = 1,
        refs_expansion_limit: int = 10,
        max_memory_brief_tokens: int | None = None,
    ) -> MemoryBrief:
        selected_decisions, selected_facts = self.recall_policy.select(
            context=context,
            store=self.store,
            scope=scope,
            top_k_decisions=top_k_decisions,
            top_k_facts=top_k_facts,
        )
        trace = RecallTrace(query=context, scope=scope, policy=self.recall_policy.name)
        decisions = []
        for selected in selected_decisions:
            decision = selected.item
            assert isinstance(decision, Decision)
            decisions.append(decision)
            trace.decisions.append(
                TraceSelection(
                    decision.id,
                    decision.kind,
                    selected.score,
                    selected.reason,
                    [ref.to_dict() for ref in decision.refs],
                )
            )

        selected_facts = self._fit_selected_fact_budget(selected_facts, decisions, max_memory_brief_tokens)
        facts = []
        for selected in selected_facts:
            fact = selected.item
            assert isinstance(fact, Fact)
            before = fact.recall_count
            fact.recall_count += 1
            facts.append(fact)
            trace.facts.append(
                TraceSelection(
                    fact.id,
                    fact.kind,
                    selected.score,
                    selected.reason,
                    [ref.to_dict() for ref in fact.refs],
                )
            )
            trace.recall_count_updates.append({"fact_id": fact.id, "before": before, "after": fact.recall_count})

        related_facts = (
            self._expand_related_facts(decisions + facts, refs_expansion_limit, refs_expansion_depth)
            if include_refs
            else []
        )
        for fact in related_facts:
            trace.related_refs.append({"fact_id": fact.id, "reason": "refs expansion"})

        self.traces.append(trace)
        return MemoryBrief(decisions=decisions, facts=facts, related_facts=related_facts, trace=trace)

    def _fit_selected_fact_budget(
        self,
        selected_facts: list[SelectedItem],
        decisions: list[Decision],
        max_tokens: int | None,
    ) -> list[SelectedItem]:
        if max_tokens is None or max_tokens <= 0:
            return selected_facts
        used = sum(len(f"{decision.scope}:{decision.key} = {decision.value}".split()) for decision in decisions)
        selected: list[SelectedItem] = []
        for selected_fact in selected_facts:
            fact = selected_fact.item
            assert isinstance(fact, Fact)
            fact_tokens = len(fact.text.split())
            if selected and used + fact_tokens > max_tokens:
                break
            selected.append(selected_fact)
            used += fact_tokens
        return selected

    def _expand_related_facts(
        self,
        items: list[Decision | Fact],
        limit: int,
        depth: int,
    ) -> list[Fact]:
        related: list[Fact] = []
        seen: set[str] = set()
        frontier = list(items)
        for _ in range(max(depth, 0)):
            next_frontier: list[Fact] = []
            for item in frontier:
                for ref in item.refs:
                    fact = self.store.get_fact(ref.target)
                    if fact and fact.id not in seen and not fact.archived:
                        related.append(fact)
                        next_frontier.append(fact)
                        seen.add(fact.id)
                        if len(related) >= limit:
                            return related
            frontier = next_frontier
            if not frontier:
                break
        return related

    def forget_facts(self, *, threshold: int = 0) -> list[str]:
        return self.forgetting_policy.apply(self.store, threshold=threshold)

    def export_trace(self) -> list[dict[str, object]]:
        return [trace.to_dict() for trace in self.traces]
