from __future__ import annotations

from typing import Any

from memorycore.core.models import Decision, Fact, RawInput


class MemoryStore:
    """Small deterministic store for research runs and tests."""

    def __init__(self) -> None:
        self.raw_inputs: dict[str, RawInput] = {}
        self.facts: dict[str, Fact] = {}
        self.decisions: dict[tuple[str, str], Decision] = {}

    def add_raw_input(self, raw_input: RawInput) -> RawInput:
        self.raw_inputs[raw_input.id] = raw_input
        return raw_input

    def add_fact(self, fact: Fact) -> Fact:
        self.facts[fact.id] = fact
        return fact

    def set_decision(self, decision: Decision) -> Decision | None:
        key = (decision.scope, decision.key)
        previous = self.decisions.get(key)
        self.decisions[key] = decision
        return previous

    def get_decisions(self, scope: str | None = None) -> list[Decision]:
        decisions = list(self.decisions.values())
        if scope is not None:
            decisions = [decision for decision in decisions if decision.scope == scope]
        return sorted(decisions, key=lambda item: (item.scope, item.key))

    def get_facts(
        self,
        scope: str | None = None,
        *,
        include_archived: bool = False,
    ) -> list[Fact]:
        facts = list(self.facts.values())
        if scope is not None:
            facts = [fact for fact in facts if fact.scope == scope]
        if not include_archived:
            facts = [fact for fact in facts if not fact.archived]
        return sorted(facts, key=lambda item: item.created_at)

    def get_fact(self, fact_id: str) -> Fact | None:
        return self.facts.get(fact_id)

    def archive_fact(self, fact_id: str) -> None:
        if fact_id in self.facts:
            self.facts[fact_id].archived = True

    def decision_ref_targets(self) -> set[str]:
        targets: set[str] = set()
        for decision in self.decisions.values():
            for ref in decision.refs:
                targets.add(ref.target)
        return targets

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_inputs": [item.to_dict() for item in self.raw_inputs.values()],
            "facts": [item.to_dict() for item in self.facts.values()],
            "decisions": [item.to_dict() for item in self.decisions.values()],
        }
