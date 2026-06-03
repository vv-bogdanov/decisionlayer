import pytest

from memorycore.core.models import Ref
from memorycore.policies.extraction import get_extractor, parse_llm_extraction_payload


def test_rule_based_extractor_splits_labelled_examples_into_atomic_facts() -> None:
    extractor = get_extractor("rule_based")

    result = extractor.extract(
        "My disposable virtual card isn't working. label: 28 "
        "A transfer to my account shows as still pending. label: 18",
        scope="memoryagentbench:test",
        raw_input_id="raw_1",
    )

    assert [fact["text"] for fact in result.facts] == [
        "My disposable virtual card isn't working. label: 28",
        "A transfer to my account shows as still pending. label: 18",
    ]
    assert result.facts[0]["tags"] == ["observation", "labelled_example"]
    assert result.facts[0]["refs"] == [Ref("raw_1", "source")]


def test_rule_based_extractor_splits_long_plain_text() -> None:
    extractor = get_extractor("rule_based")
    text = " ".join(f"word{i}" for i in range(90))

    result = extractor.extract(text, scope="project:test")

    assert len(result.facts) == 2
    assert len(str(result.facts[0]["text"]).split()) == 80
    assert len(str(result.facts[1]["text"]).split()) == 10


def test_llm_extractor_requires_explicit_policy_and_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    extractor = get_extractor("llm")

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        extractor.extract("FACT: user likes SQLite", scope="project:test")


def test_llm_extraction_safety_blocks_uncommitted_decisions() -> None:
    result = parse_llm_extraction_payload(
        '{"facts":[{"text":"User likes SQLite"}],"decisions":[{"key":"project.db","value":"SQLite","commit":true}]}',
        scope="project:test",
        refs=[Ref("raw_1", "source")],
        allow_committed_decisions=False,
        max_facts=4,
        max_decisions=4,
    )

    assert result.facts[0]["text"] == "User likes SQLite"
    assert result.decisions[0]["commit"] is False


def test_llm_extraction_allows_decision_with_external_commit_gate() -> None:
    result = parse_llm_extraction_payload(
        '{"decisions":[{"key":"project.db","value":"SQLite","commit":true}]}',
        scope="project:test",
        refs=[],
        allow_committed_decisions=True,
        max_facts=4,
        max_decisions=4,
    )

    assert result.decisions[0]["commit"] is True
