from decision_layer.extraction import RuleBasedDecisionExtractor, SourceMessage


def extract(
    content: str,
    *,
    role: str = "user",
    source_kind: str = "chat",
) -> tuple[str, str] | None:
    commands = RuleBasedDecisionExtractor().extract(
        SourceMessage(id="msg_1", role=role, content=content, source_kind=source_kind)
    )
    if not commands:
        return None
    return commands[0].action, commands[0].text


def test_strong_commit_signal_adds_decision() -> None:
    assert extract("Let's commit: use SQLite for the MVP") == ("add", "use SQLite for the MVP")


def test_goal_signal_adds_decision() -> None:
    assert extract("Goal: test Decision Layer on the benchmark") == (
        "add",
        "test Decision Layer on the benchmark",
    )


def test_replace_signal_replaces_decision() -> None:
    assert extract("Change the decision: use PostgreSQL for the MVP") == (
        "replace",
        "use PostgreSQL for the MVP",
    )


def test_weak_phrases_do_not_create_decisions() -> None:
    assert extract("Maybe SQLite") is None
    assert extract("SQLite looks interesting") is None
    assert extract("Could consider PostgreSQL later") is None


def test_non_user_roles_cannot_create_decisions() -> None:
    assert extract("Let's commit: use SQLite for the MVP", role="assistant") is None
    assert extract("Let's commit: use SQLite for the MVP", role="tool") is None
    assert extract("Let's commit: use SQLite for the MVP", role="retrieved_memory") is None


def test_external_source_kinds_cannot_create_decisions() -> None:
    text = "Let's commit: use SQLite for the MVP"

    assert extract(text, source_kind="document") is None
    assert extract(text, source_kind="web_page") is None
    assert extract(text, source_kind="benchmark_answer") is None
    assert extract(text, source_kind="external_source") is None
