from decision_layer.extraction import (
    RuleBasedDecisionExtractor,
    SourceMessage,
    state_supported_workflow_texts,
)


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


def test_explicit_requirement_signal_adds_decision() -> None:
    assert extract("Requirement: return responses as JSON") == (
        "add",
        "return responses as JSON",
    )
    assert extract("Constraint: do not use custom benchmarks for proof") == (
        "add",
        "do not use custom benchmarks for proof",
    )
    assert extract("Требование: не сохранять факты как решения") == (
        "add",
        "не сохранять факты как решения",
    )


def test_one_off_need_statement_is_not_a_decision() -> None:
    assert extract("I need to find the current ticket status") is None


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
    ) == (
        "add",
        "For rebalancing workload between agents by problem tag, use Reports first, then Problems.",
    )


def test_structured_workflow_extraction_can_emit_multiple_decisions() -> None:
    texts = extract_texts(
        "Given the title of the report, search for it. The report shows the number of "
        "incidents assigned to an agent. You have to create new item requests for all "
        "the agents based on the above criteria."
    )

    assert (
        "For extra device item requests for agents selected from incident-report criteria"
        in texts[0]
    )
    assert "To locate an incident-related performance report" in texts[1]


def test_structured_workflow_extraction_for_investment_allocation() -> None:
    assert extract(
        'Follow protocol "Maximizing total investment return" to allocate investments '
        "to the expenses with short description containing #ded37a11-b to maximize "
        "returns while fitting inside the budget."
    ) == (
        "add",
        "For allocating investments to maximize returns, use Cost > Expense Lines; "
        "returns are in Short description; set selected lines to Closed Complete before Update.",
    )


def test_structured_workflow_extraction_for_stock_restocking_report() -> None:
    assert extract(
        "You have to retrieve information from a dashboard chart. The chart presents "
        "the number of hardware items available in stock. Title of the report: "
        "#CAT001314192. Place an order for the least available item in stock."
    ) == (
        "add",
        "For dashboard-based restocking of low-stock items, use Reports to locate the "
        "stock report before ordering.",
    )


def test_structured_workflow_extraction_for_user_offboarding() -> None:
    assert extract(
        "Offboard user Sean-Michelle Morris-Martinez. Create a filter for hardware "
        'assets where "Assigned to" is the user. Edit the hardware asset record by '
        'replacing "Assigned to" with "".'
    ) == (
        "add",
        "For offboarding a user, unassign all hardware assets by clearing Assigned to, "
        "then delete the user profile and close the task complete.",
    )


def test_state_supported_workflow_extraction_for_problem_requests() -> None:
    texts = state_supported_workflow_texts(
        (
            "Given the title of the report, search for it. The report shows incidents "
            "assigned to an agent. You have to create new 'problems' for all the agents. "
            "Only fill the following fields when creating a new problem: Impact, "
            "Urgency, Problem statement and assign them to each agent."
        ),
        [
            (
                "Problem form fields include State, Assignment group, Assigned to, "
                "Problem statement, and Subcategory."
            )
        ],
    )

    assert texts == (
        "For problem requests created from incident-report results, use Impact, Urgency, "
        "Problem statement, and Assigned to; Subcategory, Assignment Group, and State "
        "are present but unused.",
    )


def test_structured_workflow_extraction_still_respects_authority() -> None:
    text = 'Referring to company protocol "Agent Workload Balancing" re-distribute problems.'

    assert extract(text, role="assistant") is None
    assert extract(text, source_kind="document") is None
