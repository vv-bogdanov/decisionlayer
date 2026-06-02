import pytest

from memorycore import MemoryRuntime, Ref
from memorycore.policies.safety import SafetyError


def test_add_raw_input_and_fact() -> None:
    runtime = MemoryRuntime()

    raw = runtime.add_raw_input("FACT: user prefers SQLite", scope="project:test")
    fact = runtime.add_fact(
        "user prefers SQLite",
        scope="project:test",
        tags=["observation"],
        refs=[Ref(raw.id, "source")],
    )

    assert raw.id in runtime.store.raw_inputs
    assert fact.id in runtime.store.facts
    assert fact.refs[0].target == raw.id


def test_decision_requires_commit_signal() -> None:
    runtime = MemoryRuntime()

    with pytest.raises(SafetyError):
        runtime.set_decision("project.db", "SQLite", scope="project:test")


def test_update_decision_preserves_history_fact() -> None:
    runtime = MemoryRuntime()

    first = runtime.set_decision("project.db", "SQLite", scope="project:test", commit=True)
    second = runtime.set_decision("project.db", "PostgreSQL", scope="project:test", commit=True)

    decisions = runtime.store.get_decisions("project:test")
    facts = runtime.store.get_facts("project:test")

    assert len(decisions) == 1
    assert decisions[0].id == second.id
    assert decisions[0].value == "PostgreSQL"
    assert first.id != second.id
    assert len(facts) == 1
    assert {"history", "decision_change"} <= set(facts[0].tags)
    assert facts[0].meta["old_value"] == "SQLite"
    assert facts[0].meta["new_value"] == "PostgreSQL"


def test_forgetting_keeps_facts_referenced_by_current_decisions() -> None:
    runtime = MemoryRuntime(forgetting_policy="low_recall_count_except_decision_refs")
    protected = runtime.add_fact("SQLite is cheap for MVP", scope="project:test")
    disposable = runtime.add_fact("temporary note", scope="project:test")
    runtime.set_decision(
        "project.db",
        "SQLite",
        scope="project:test",
        refs=[Ref(protected.id, "based_on")],
        commit=True,
    )

    archived = runtime.forget_facts(threshold=0)

    assert protected.id not in archived
    assert disposable.id in archived
    assert not runtime.store.get_fact(protected.id).archived
    assert runtime.store.get_fact(disposable.id).archived


def test_age_aware_forgetting_keeps_newest_low_recall_facts() -> None:
    runtime = MemoryRuntime(forgetting_policy="age_aware_low_recall_count_except_decision_refs")
    first = runtime.add_fact("old low recall note", scope="project:test")
    second = runtime.add_fact("new low recall note", scope="project:test")

    archived = runtime.forget_facts(threshold=0)

    assert first.id in archived
    assert second.id not in archived
