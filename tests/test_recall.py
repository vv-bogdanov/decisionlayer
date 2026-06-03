from memorycore import MemoryRuntime, Ref


def test_recall_returns_decisions_first_and_increments_recall_count() -> None:
    runtime = MemoryRuntime(recall_policy="decision_first_with_recall_count")
    fact = runtime.add_fact("The selected database is SQLite for the MVP.", scope="project:test")
    runtime.set_decision("project.db", "SQLite", scope="project:test", commit=True)

    brief = runtime.recall("Which database should the project use?", scope="project:test")

    assert brief.render().index("Decisions:") < brief.render().index("Facts:")
    assert brief.decisions[0].key == "project.db"
    assert fact.recall_count == 1


def test_recall_trace_explains_selected_items() -> None:
    runtime = MemoryRuntime(recall_policy="keyword")
    fact = runtime.add_fact("The user asked for Russian answers.", scope="project:test")

    brief = runtime.recall("Should answers be Russian?", scope="project:test")
    traces = runtime.export_trace()

    assert brief.trace is not None
    assert traces[0]["facts"][0]["id"] == fact.id
    assert traces[0]["facts"][0]["reason"] == "keyword fact match"
    assert traces[0]["recall_count_updates"][0]["before"] == 0
    assert traces[0]["recall_count_updates"][0]["after"] == 1


def test_bm25_recall_prefers_relevant_fact() -> None:
    runtime = MemoryRuntime(recall_policy="bm25")
    relevant = runtime.add_fact("The car had a GPS system failure after service.", scope="project:test")
    runtime.add_fact("The user likes oatmeal for breakfast.", scope="project:test")

    brief = runtime.recall("What car GPS issue happened?", scope="project:test", top_k_facts=1)

    assert brief.facts[0].id == relevant.id
    assert brief.trace.facts[0].reason == "bm25 fact match"


def test_tfidf_and_hybrid_recall_are_available() -> None:
    for policy in ("tfidf", "hybrid"):
        runtime = MemoryRuntime(recall_policy=policy)
        relevant = runtime.add_fact("Book club discussion focused on Gone Girl.", scope="project:test")
        runtime.add_fact("The car had new floor mats.", scope="project:test")

        brief = runtime.recall("Which book club topic?", scope="project:test", top_k_facts=1)

        assert brief.facts[0].id == relevant.id


def test_recall_refs_expansion_and_token_budget() -> None:
    runtime = MemoryRuntime(recall_policy="keyword")
    related = runtime.add_fact("SQLite was selected because it is cheap.", scope="project:test")
    runtime.add_fact("This fact is long enough to exceed a very tiny token budget.", scope="project:test")
    runtime.set_decision(
        "project.db",
        "SQLite",
        scope="project:test",
        refs=[Ref(related.id, "based_on")],
        commit=True,
    )

    brief = runtime.recall(
        "database",
        scope="project:test",
        top_k_decisions=1,
        top_k_facts=2,
        include_refs=True,
        refs_expansion_depth=1,
        max_memory_brief_tokens=3,
    )

    assert related.id in {fact.id for fact in brief.related_facts}
    assert len(brief.facts) <= 1


def test_recall_token_budget_skips_oversized_facts() -> None:
    runtime = MemoryRuntime(recall_policy="keyword")
    oversized = runtime.add_fact("database " * 100, scope="project:test")
    small = runtime.add_fact("database SQLite", scope="project:test")

    brief = runtime.recall("database", scope="project:test", top_k_facts=2, max_memory_brief_tokens=5)

    fact_ids = {fact.id for fact in brief.facts}
    assert oversized.id not in fact_ids
    assert small.id in fact_ids
