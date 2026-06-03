from memorycore.baselines.runners import synthesize_answer
from memorycore.core.models import Fact, MemoryBrief


def test_synthesize_answer_extracts_label_from_selected_atomic_fact() -> None:
    brief = MemoryBrief(
        decisions=[],
        facts=[
            Fact(
                "My disposable virtual card isn't working. label: 28",
                scope="memoryagentbench:test",
            )
        ],
    )

    assert (
        synthesize_answer(
            "Are there restrictions for my disposable card since it does not seem to be working?",
            brief,
        )
        == "28"
    )


def test_synthesize_answer_keeps_fact_fallback_without_labelled_examples() -> None:
    brief = MemoryBrief(
        decisions=[],
        facts=[Fact("The selected database is SQLite.", scope="project:test")],
    )

    assert synthesize_answer("Which database?", brief) == "The selected database is SQLite."
