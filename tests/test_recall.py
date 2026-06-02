from memorycore import MemoryRuntime


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

