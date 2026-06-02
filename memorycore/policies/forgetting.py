from __future__ import annotations

from memorycore.core.store import MemoryStore


class ForgettingPolicy:
    name = "none"

    def apply(self, store: MemoryStore, *, threshold: int = 0) -> list[str]:
        return []


class LowRecallCountExceptDecisionRefs(ForgettingPolicy):
    name = "low_recall_count_except_decision_refs"

    def apply(self, store: MemoryStore, *, threshold: int = 0) -> list[str]:
        protected = store.decision_ref_targets()
        archived: list[str] = []
        for fact in store.get_facts(include_archived=False):
            if fact.id in protected:
                continue
            if fact.recall_count <= threshold:
                store.archive_fact(fact.id)
                archived.append(fact.id)
        return archived


def get_forgetting_policy(name: str | None) -> ForgettingPolicy:
    if name in {None, "none"}:
        return ForgettingPolicy()
    if name == "low_recall_count_except_decision_refs":
        return LowRecallCountExceptDecisionRefs()
    raise ValueError(f"unknown forgetting policy: {name}")

