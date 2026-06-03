from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_SEPARATORS = (",", ";")
UNSUPPORTED_LLM_EVALUATORS = {"llm_abstention_checker", "llm_gotchas_checker"}


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    correct: bool | None
    supported: bool
    evaluator: str
    reason: str | None = None


def score_answer(prediction: str, answer: str, eval_function: str) -> EvaluationResult:
    name, options = parse_eval_function(eval_function)
    if name == "exact_match":
        return supported_result(normalize_text(prediction) == normalize_text(answer), name)
    if name == "norm_phrase_set_match":
        return supported_result(norm_phrase_set_match(prediction, answer, options), name)
    if name == "norm_phrase_set_match_ordered":
        return supported_result(norm_phrase_set_match_ordered(prediction, answer, options), name)
    if name == "mc_choice_match":
        return supported_result(mc_choice_match(prediction, answer, options), name)
    if name == "mc_choice_set_match":
        return supported_result(mc_choice_set_match(prediction, answer, options), name)
    if name in UNSUPPORTED_LLM_EVALUATORS:
        return EvaluationResult(
            correct=None,
            supported=False,
            evaluator=name,
            reason="LLM judge evaluator is not implemented in the local deterministic POC scorer.",
        )
    raise ValueError(f"unsupported eval function: {eval_function}")


def supported_result(correct: bool, evaluator: str) -> EvaluationResult:
    return EvaluationResult(correct=correct, supported=True, evaluator=evaluator)


def parse_eval_function(spec: str) -> tuple[str, dict[str, object]]:
    parts = [part.strip() for part in spec.split("|")]
    name = parts[0]
    if not name:
        raise ValueError("eval function is missing a name")
    options: dict[str, object] = {}
    for part in parts[1:]:
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"invalid eval function option: {part}")
        key, value = part.split("=", 1)
        options[key.strip()] = parse_eval_value(key.strip(), value.strip())
    return name, options


def parse_eval_value(key: str, value: str) -> object:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if key in {"separator", "separators"}:
        return tuple(ch for ch in value if not ch.isspace())
    return value


def norm_phrase_set_match(prediction: str, answer: str, options: dict[str, object]) -> bool:
    normalized_prediction = normalize_phrase(prediction, options)
    answer_phrases = split_phrases(answer, options)
    if require_non_empty(options) and (not normalized_prediction or not answer_phrases):
        return False
    return all(contains_phrase(normalized_prediction, phrase) for phrase in set(answer_phrases))


def norm_phrase_set_match_ordered(prediction: str, answer: str, options: dict[str, object]) -> bool:
    normalized_prediction = normalize_phrase(prediction, options)
    answer_phrases = split_phrases(answer, options)
    if require_non_empty(options) and (not normalized_prediction or not answer_phrases):
        return False
    start = 0
    for phrase in answer_phrases:
        match = re.search(word_pattern(phrase), normalized_prediction[start:])
        if match is None:
            return False
        start += match.end()
    return True


def split_phrases(text: str, options: dict[str, object]) -> list[str]:
    separators = options.get("separators", DEFAULT_SEPARATORS)
    if not isinstance(separators, tuple) or not separators:
        normalized = normalize_phrase(text, options)
        return [normalized] if normalized else []
    pattern = "|".join(re.escape(separator) for separator in separators)
    return [
        normalized
        for normalized in (normalize_phrase(part, options) for part in re.split(pattern, text))
        if normalized
    ]


def normalize_phrase(text: str, options: dict[str, object]) -> str:
    normalized = text
    if bool(options.get("lower", True)):
        normalized = normalized.lower()
    if bool(options.get("normalize_hyphen", True)):
        normalized = normalized.replace("-", " ").replace("_", " ")
    normalized = re.sub(r"[,;]", " ", normalized)
    if bool(options.get("strip_punct", True)):
        normalized = re.sub(r"[^\w\s]", "", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def contains_phrase(text: str, phrase: str) -> bool:
    return re.search(word_pattern(phrase), text) is not None


def word_pattern(phrase: str) -> str:
    return rf"\b{re.escape(phrase)}\b"


def mc_choice_match(prediction: str, answer: str, options: dict[str, object]) -> bool:
    cleaned_prediction = boxed_or_full_answer(prediction)
    cleaned_prediction = re.sub(r"\b(choice|option)\b", "", cleaned_prediction, flags=re.IGNORECASE)
    for char in str(options.get("strip_chars", ".")):
        cleaned_prediction = cleaned_prediction.replace(char, "")
    normalized_prediction = cleaned_prediction.strip().upper()
    normalized_answer = answer.strip().upper()
    if require_non_empty(options) and (not normalized_prediction or not normalized_answer):
        return False
    return normalized_prediction == normalized_answer


def mc_choice_set_match(prediction: str, answer: str, options: dict[str, object]) -> bool:
    prediction_letters = extract_choice_letters(prediction)
    answer_letters = extract_choice_letters(answer)
    if require_non_empty(options) and (not prediction_letters or not answer_letters):
        return False
    return set(prediction_letters) == set(answer_letters)


def boxed_or_full_answer(text: str) -> str:
    match = re.search(r"\\boxed\{([^}]*)\}", text, flags=re.IGNORECASE)
    return match.group(1) if match else text


def extract_choice_letters(text: str) -> list[str]:
    filler = {"AND", "ANSWER", "ANSWERS", "CHOICE", "CHOICES", "FINAL", "OPTION", "OPTIONS"}
    letters: list[str] = []
    for chunk in re.findall(r"[A-Z]+", text.upper()):
        if chunk in filler:
            continue
        letters.extend(chunk)
    return letters


def require_non_empty(options: dict[str, object]) -> bool:
    return bool(options.get("require_non_empty", True))


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())
