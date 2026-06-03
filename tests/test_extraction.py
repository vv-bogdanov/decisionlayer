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


def extract_texts(content: str) -> tuple[str, ...]:
    commands = RuleBasedDecisionExtractor().extract(
        SourceMessage(id="msg_1", role="user", content=content, source_kind="chat")
    )
    return tuple(command.text for command in commands)


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


def test_structured_workflow_extraction_for_agent_workload_balancing() -> None:
    assert extract(
        'Referring to company protocol "Agent Workload Balancing" re-distribute the '
        "problems with hashtag=#PRB052840832."
    ) == ("add", "For Agent Workload Balancing, use Reports first, then Problems.")


def test_structured_workflow_extraction_can_emit_multiple_decisions() -> None:
    texts = extract_texts(
        "Given the title of the report, search for it. The report shows the number of "
        "incidents assigned to an agent. You have to create new item requests for all "
        "the agents based on the above criteria."
    )

    assert "For incident-report criteria tasks that create item requests" in texts[0]
    assert "To locate an incident-related performance report" in texts[1]


def test_structured_workflow_extraction_still_respects_authority() -> None:
    text = 'Referring to company protocol "Agent Workload Balancing" re-distribute problems.'

    assert extract(text, role="assistant") is None
    assert extract(text, source_kind="document") is None
