from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Literal, Protocol

ReaderKind = Literal["smoke", "openai-chat"]


@dataclass(frozen=True, slots=True)
class ReaderRequest:
    question: str
    context: str
    expected_answer: str | None = None


@dataclass(frozen=True, slots=True)
class ReaderResult:
    answer: str
    reader_policy: str
    latency_seconds: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class ReaderPlugin(Protocol):
    @property
    def policy(self) -> str:
        """Reader policy identifier for metrics and reports."""

    def answer(self, request: ReaderRequest) -> ReaderResult:
        """Return an answer from the selected benchmark reader backend."""


@dataclass(frozen=True, slots=True)
class SmokeOracleSubstringReader:
    policy: str = "smoke_oracle_substring_reader"

    def answer(self, request: ReaderRequest) -> ReaderResult:
        start = perf_counter()
        expected_answer = request.expected_answer or ""
        answer = expected_answer if normalize(expected_answer) in normalize(request.context) else ""
        return ReaderResult(
            answer=answer,
            reader_policy=self.policy,
            latency_seconds=round(perf_counter() - start, 6),
        )


@dataclass(frozen=True, slots=True)
class OpenAIChatReader:
    base_url: str
    model: str
    timeout_seconds: float = 60.0
    max_tokens: int = 64
    temperature: float = 0.0
    policy: str = "openai_chat"

    def answer(self, request: ReaderRequest) -> ReaderResult:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Answer the question using only the provided context. "
                        "Return only the short answer. If the context is insufficient, "
                        "return UNKNOWN."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Context:\n{request.context}\n\nQuestion:\n{request.question}\n\nAnswer:"
                    ),
                },
            ],
        }
        start = perf_counter()
        response = post_json(
            f"{self.base_url.rstrip('/')}/chat/completions",
            payload,
            timeout_seconds=self.timeout_seconds,
        )
        usage = response.get("usage", {})
        return ReaderResult(
            answer=extract_chat_answer(response),
            reader_policy=self.policy,
            latency_seconds=round(perf_counter() - start, 6),
            prompt_tokens=optional_int(usage, "prompt_tokens"),
            completion_tokens=optional_int(usage, "completion_tokens"),
            total_tokens=optional_int(usage, "total_tokens"),
        )


def build_reader(
    reader: ReaderKind,
    *,
    base_url: str,
    model: str | None,
    timeout_seconds: float,
    max_tokens: int,
) -> ReaderPlugin:
    if reader == "smoke":
        return SmokeOracleSubstringReader()
    if model is None:
        raise ValueError("--reader-model is required when --reader openai-chat is used")
    return OpenAIChatReader(
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
    )


def post_json(url: str, payload: dict[str, object], *, timeout_seconds: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"reader request failed: {url}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"reader response must be a JSON object: {url}")
    return data


def extract_chat_answer(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return ""
    message = first_choice.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return str(content).strip() if content is not None else ""


def optional_int(data: object, key: str) -> int | None:
    if not isinstance(data, dict):
        return None
    value = data.get(key)
    return value if isinstance(value, int) else None


def normalize(text: str) -> str:
    return " ".join(text.lower().split())
