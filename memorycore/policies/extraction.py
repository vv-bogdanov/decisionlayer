from __future__ import annotations

import re
from dataclasses import dataclass, field

from memorycore.core.models import Ref

DECISION_RE = re.compile(
    r"^(?P<commit>COMMIT\s+)?DECISION:\s*(?P<key>[A-Za-z0-9_.:-]+)\s*=\s*(?P<value>.+)$",
    re.IGNORECASE,
)


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
        if fact_text:
            result.facts.append(
                {
                    "text": fact_text,
                    "scope": scope,
                    "tags": [tag],
                    "refs": source_refs,
                }
            )
        return result


class ManualOracleExtractor(RuleBasedExtractor):
    name = "manual_oracle"


def get_extractor(name: str | None) -> RuleBasedExtractor:
    if name in {None, "rule_based"}:
        return RuleBasedExtractor()
    if name == "manual_oracle":
        return ManualOracleExtractor()
    raise ValueError(f"unknown extractor policy: {name}")

