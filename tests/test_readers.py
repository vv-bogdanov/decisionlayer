import json

import pytest

from decision_layer.readers import (
    OpenAIChatReader,
    ReaderRequest,
    SmokeOracleSubstringReader,
    build_reader,
)


def test_smoke_reader_returns_expected_answer_only_when_context_contains_it() -> None:
    reader = SmokeOracleSubstringReader()

    hit = reader.answer(
        ReaderRequest(
            question="Which checkout option is the default?",
            context="Guest checkout is selected by default.",
            expected_answer="Guest checkout",
        )
    )
    miss = reader.answer(
        ReaderRequest(
            question="Which checkout option is the default?",
            context="Registered account checkout is selected by default.",
            expected_answer="Guest checkout",
        )
    )

    assert hit.answer == "Guest checkout"
    assert miss.answer == ""


def test_openai_chat_reader_posts_prompt_and_reads_usage(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured = {}

    class FakeResponse:
        def __enter__(self):  # type: ignore[no-untyped-def]
            return self

        def __exit__(self, exc_type, exc, traceback):  # type: ignore[no-untyped-def]
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [{"message": {"content": "Guest checkout"}}],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 2,
                        "total_tokens": 12,
                    },
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    reader = OpenAIChatReader(
        base_url="http://localhost:18080/v1/",
        model="local-model",
        timeout_seconds=7.0,
        max_tokens=9,
    )
    result = reader.answer(
        ReaderRequest(
            question="Which checkout option is the default?",
            context="Guest checkout is selected by default.",
        )
    )

    assert result.answer == "Guest checkout"
    assert result.prompt_tokens == 10
    assert result.completion_tokens == 2
    assert result.total_tokens == 12
    assert captured["url"] == "http://localhost:18080/v1/chat/completions"
    assert captured["timeout"] == 7.0
    assert captured["payload"]["model"] == "local-model"
    assert captured["payload"]["max_tokens"] == 9


def test_openai_chat_reader_requires_model() -> None:
    with pytest.raises(ValueError, match="--reader-model is required"):
        build_reader(
            "openai-chat",
            base_url="http://localhost:18080/v1",
            model=None,
            timeout_seconds=60.0,
            max_tokens=64,
        )
