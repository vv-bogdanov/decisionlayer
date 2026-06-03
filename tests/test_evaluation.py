from decision_layer.evaluation import score_answer


def test_norm_phrase_set_match_uses_all_answer_phrases_without_order() -> None:
    result = score_answer(
        "The labels are My Open Incidents and Incident Mobile.",
        "Incident Mobile, My Open Incidents",
        "norm_phrase_set_match|lower=true|normalize_hyphen=true|strip_punct=true|separators=,;|require_non_empty=true",
    )

    assert result.correct is True
    assert result.supported is True


def test_norm_phrase_set_match_ordered_requires_order() -> None:
    eval_function = (
        "norm_phrase_set_match_ordered|lower=true|normalize_hyphen=true|strip_punct=true|"
        "separators=;|require_non_empty=true"
    )

    assert score_answer("Reports; Problems", "Reports;Problems", eval_function).correct is True
    assert score_answer("Problems; Reports", "Reports;Problems", eval_function).correct is False


def test_mc_choice_match_accepts_boxed_choice() -> None:
    result = score_answer(
        "Final answer: \\boxed{B}.",
        "B",
        "mc_choice_match|require_non_empty=true",
    )

    assert result.correct is True


def test_mc_choice_set_match_ignores_order() -> None:
    result = score_answer(
        "Final choices: C and A",
        "AC",
        "mc_choice_set_match|require_non_empty=true",
    )

    assert result.correct is True


def test_llm_judge_eval_is_explicitly_unsupported() -> None:
    result = score_answer(
        "UNKNOWN",
        "The premise is wrong.",
        "llm_abstention_checker|require_non_empty=true",
    )

    assert result.correct is None
    assert result.supported is False
    assert result.reason is not None
