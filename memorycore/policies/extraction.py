from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.request import Request, urlopen

from memorycore.core.models import Ref

DECISION_RE = re.compile(
    r"^(?P<commit>COMMIT\s+)?DECISION:\s*(?P<key>[A-Za-z0-9_.:-]+)\s*=\s*(?P<value>.+)$",
    re.IGNORECASE,
)
LABELLED_EXAMPLE_RE = re.compile(
    r"(?P<text>.*?)(?:\s+label:\s*(?P<label>[A-Za-z0-9_.-]+))(?=\s|$)",
    re.IGNORECASE | re.DOTALL,
)
SENTENCE_SPLIT_RE = re.compile(r"(?:\n+|(?<=[.!?])\s+)")
DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_LLM_URL = "https://api.openai.com/v1/responses"
MAX_RULE_FACT_WORDS = 80


@dataclass(slots=True)
class ExtractionResult:
    facts: list[dict[str, object]] = field(default_factory=list)
    decisions: list[dict[str, object]] = field(default_factory=list)


class RuleBasedExtractor:
    name = "rule_based"

    def extract(self, text: str, *, scope: str, raw_input_id: str | None = None) -> ExtractionResult:
        result = ExtractionResult()
        source_refs = [Ref(raw_input_id, "source")] if raw_input_id else []
        stripped = text.strip()
        decision_match = DECISION_RE.match(stripped)
        if decision_match:
            result.decisions.append(
                {
                    "key": decision_match.group("key").strip(),
                    "value": decision_match.group("value").strip(),
                    "scope": scope,
                    "refs": source_refs,
                    "commit": bool(decision_match.group("commit")),
                }
            )
            return result
        tag = "observation"
        fact_text = stripped
        upper = stripped.upper()
        for prefix, candidate_tag in (
            ("FACT:", "observation"),
            ("HYPOTHESIS:", "hypothesis"),
            ("ERROR:", "error"),
            ("EVIDENCE:", "evidence"),
        ):
            if upper.startswith(prefix):
                fact_text = stripped[len(prefix) :].strip()
                tag = candidate_tag
                break
        for fact_text, tags in split_rule_based_facts(fact_text, tag):
            result.facts.append(
                {
                    "text": fact_text,
                    "scope": scope,
                    "tags": tags,
                    "refs": source_refs,
                }
            )
        return result


class ManualOracleExtractor(RuleBasedExtractor):
    name = "manual_oracle"


class LLMExtractor(RuleBasedExtractor):
    name = "llm"

    def __init__(
        self,
        *,
        model: str = DEFAULT_LLM_MODEL,
        url: str = DEFAULT_LLM_URL,
        max_facts: int = 12,
        max_decisions: int = 4,
    ) -> None:
        self.model = model
        self.url = url
        self.max_facts = max_facts
        self.max_decisions = max_decisions

    def extract(self, text: str, *, scope: str, raw_input_id: str | None = None) -> ExtractionResult:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("extractor_policy=llm requires OPENAI_API_KEY")
        source_refs = [Ref(raw_input_id, "source")] if raw_input_id else []
        payload = json.dumps({"model": self.model, "input": llm_extraction_prompt(text)}).encode("utf-8")
        request = Request(
            self.url,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=60) as response:
            response_data = json.loads(response.read().decode("utf-8"))
        return parse_llm_extraction_payload(
            extract_response_text(response_data),
            scope=scope,
            refs=source_refs,
            allow_committed_decisions=has_explicit_commit_signal(text),
            max_facts=self.max_facts,
            max_decisions=self.max_decisions,
        )


def llm_extraction_prompt(text: str) -> str:
    return (
        "Extract durable memory facts and explicit committed decisions from the input. "
        "Return strict JSON with keys facts and decisions. "
        "facts is a list of objects with text and optional tags. "
        "decisions is a list of objects with key, value, and commit. "
        "Set commit=true only when the input explicitly asks to commit a decision.\n\n"
        f"Input:\n{text}"
    )


def parse_llm_extraction_payload(
    payload: str,
    *,
    scope: str,
    refs: list[Ref],
    allow_committed_decisions: bool,
    max_facts: int,
    max_decisions: int,
) -> ExtractionResult:
    data = parse_json_object(payload)
    result = ExtractionResult()
    for item in list_value(data.get("facts"))[:max_facts]:
        if not isinstance(item, dict):
            continue
        fact_text = str(item.get("text") or "").strip()
        if not fact_text:
            continue
        tags = [str(tag) for tag in list_value(item.get("tags"))] or ["observation"]
        result.facts.append({"text": fact_text, "scope": scope, "tags": tags, "refs": refs})

    for item in list_value(data.get("decisions"))[:max_decisions]:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        value = str(item.get("value") or "").strip()
        if not key or not value:
            continue
        result.decisions.append(
            {
                "key": key,
                "value": value,
                "scope": scope,
                "refs": refs,
                "commit": bool(item.get("commit")) and allow_committed_decisions,
            }
        )
    return result


def parse_json_object(payload: str) -> dict[str, Any]:
    stripped = payload.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end >= start:
        stripped = stripped[start : end + 1]
    data = json.loads(stripped)
    if not isinstance(data, dict):
        raise ValueError("LLM extraction response must be a JSON object")
    return data


def list_value(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def split_rule_based_facts(text: str, tag: str) -> list[tuple[str, list[str]]]:
    stripped = text.strip()
    if not stripped:
        return []
    labelled_examples = split_labelled_examples(stripped)
    if labelled_examples:
        return [
            (f"{example_text} label: {label}", [tag, "labelled_example"]) for example_text, label in labelled_examples
        ]
    return [(chunk, [tag]) for chunk in split_plain_fact_text(stripped)]


def split_labelled_examples(text: str) -> list[tuple[str, str]]:
    examples: list[tuple[str, str]] = []
    for match in LABELLED_EXAMPLE_RE.finditer(text):
        example_text = match.group("text").strip()
        label = match.group("label").strip()
        if example_text and label:
            examples.append((example_text, label))
    return examples


def split_plain_fact_text(text: str) -> list[str]:
    parts = [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]
    if not parts:
        return []
    chunks: list[str] = []
    for part in parts:
        chunks.extend(split_long_fact(part))
    return chunks


def split_long_fact(text: str) -> list[str]:
    words = text.split()
    if len(words) <= MAX_RULE_FACT_WORDS:
        return [text]
    return [" ".join(words[index : index + MAX_RULE_FACT_WORDS]) for index in range(0, len(words), MAX_RULE_FACT_WORDS)]


def has_explicit_commit_signal(text: str) -> bool:
    match = DECISION_RE.match(text.strip())
    return bool(match and match.group("commit"))


def extract_response_text(data: dict[str, Any]) -> str:
    if isinstance(data.get("output_text"), str):
        return str(data["output_text"])
    chunks: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks)


def get_extractor(
    name: str | None,
    *,
    model: str = DEFAULT_LLM_MODEL,
    url: str = DEFAULT_LLM_URL,
    max_facts: int = 12,
    max_decisions: int = 4,
) -> RuleBasedExtractor:
    if name in {None, "rule_based"}:
        return RuleBasedExtractor()
    if name == "manual_oracle":
        return ManualOracleExtractor()
    if name == "llm":
        return LLMExtractor(model=model, url=url, max_facts=max_facts, max_decisions=max_decisions)
    raise ValueError(f"unknown extractor policy: {name}")
