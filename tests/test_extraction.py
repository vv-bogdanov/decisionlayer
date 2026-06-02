import pytest

from memorycore.core.models import Ref
from memorycore.policies.extraction import get_extractor, parse_llm_extraction_payload


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
