import pytest

from decision_layer.core import (
    DecisionLayerError,
    DecisionNotFoundError,
    DecisionState,
    InvalidAuthorityError,
    add_decision,
    list_decisions,
    remove_decision,
    render_decision_brief,
    replace_decision,
)


def test_add_list_replace_remove_decision() -> None:
    state = DecisionState()

    state, add_trace = add_decision(
        state,
        "Use SQLite for the MVP.",
        authority="user_commit",
        decision_id="decision_db",
    )

    assert add_trace.action == "add"
    assert [decision.text for decision in list_decisions(state)] == ["Use SQLite for the MVP."]

    state, replace_trace = replace_decision(
        state,
        "decision_db",
        "Use PostgreSQL for the MVP.",
        authority="user_confirmation",
        new_decision_id="decision_db_v2",
    )

    assert replace_trace.action == "replace"
    assert replace_trace.replaced_id == "decision_db"
    assert [decision.id for decision in state.decisions] == ["decision_db_v2"]
    assert [decision.text for decision in state.decisions] == ["Use PostgreSQL for the MVP."]

    state, remove_trace = remove_decision(
        state,
        "decision_db_v2",
        authority="manual_api_commit",
    )

    assert remove_trace.action == "remove"
    assert state.decisions == ()


def test_replaced_decision_is_not_active_context() -> None:
    state, _ = add_decision(
        DecisionState(),
        "Use SQLite for the MVP.",
        authority="user_commit",
        decision_id="decision_db",
    )
    state, _ = replace_decision(
        state,
        "decision_db",
        "Use PostgreSQL for the MVP.",
        authority="user_commit",
        new_decision_id="decision_db_v2",
    )

    brief = render_decision_brief(state)

    assert "Use PostgreSQL for the MVP." in brief.text
    assert "Use SQLite for the MVP." not in brief.text


def test_decision_brief_contains_instruction_and_respects_budget() -> None:
    state, _ = add_decision(
        DecisionState(),
        "Use Python for the POC.",
        authority="user_commit",
        decision_id="decision_lang",
    )
    state, _ = add_decision(
        state,
        "Defer Rust until production core work.",
        authority="user_commit",
        decision_id="decision_rust",
    )

    brief = render_decision_brief(state, max_decisions=2)
    tiny_brief = render_decision_brief(state, max_decisions=2, max_tokens=24)

    assert "Decision Brief" in brief.text
    assert "Use these decisions as current commitments" in brief.text
    assert "Use Python for the POC." in brief.text
    assert "Defer Rust until production core work." in brief.text
    assert len(tiny_brief.decisions) < len(brief.decisions)


def test_invalid_authority_cannot_change_decisions() -> None:
    with pytest.raises(InvalidAuthorityError):
        add_decision(DecisionState(), "Use SQLite.", authority="assistant_suggestion")  # type: ignore[arg-type]


def test_missing_decision_replace_and_remove_fail() -> None:
    with pytest.raises(DecisionNotFoundError):
        replace_decision(
            DecisionState(),
            "missing",
            "Use PostgreSQL.",
            authority="user_commit",
        )
    with pytest.raises(DecisionNotFoundError):
        remove_decision(DecisionState(), "missing", authority="user_commit")


def test_empty_and_oversized_decisions_are_rejected() -> None:
    with pytest.raises(DecisionLayerError):
        add_decision(DecisionState(), "   ", authority="user_commit")
    with pytest.raises(DecisionLayerError):
        add_decision(DecisionState(), "x" * 281, authority="user_commit")
