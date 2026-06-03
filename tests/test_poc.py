import json
from pathlib import Path

from decision_layer.benchmarks.longmemeval_v2 import (
    LongMemEvalV2Example,
    LongMemEvalV2Question,
    LongMemEvalV2Trajectory,
)
from decision_layer.core import DecisionState, add_decision, render_decision_brief
from decision_layer.extraction import RuleBasedDecisionExtractor
from decision_layer.poc import (
    PocConfig,
    PocSuiteConfig,
    apply_automatic_decisions,
    build_reader_context,
    decision_relevant_to_question,
    retrieve_keyword_context,
    run_poc,
    run_poc_suite,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "longmemeval_v2"


def test_build_reader_context_skips_empty_decision_brief() -> None:
    context = "Baseline retrieved context."
    empty_brief = render_decision_brief(DecisionState())

    assert build_reader_context("D1", empty_brief, context) == context
    assert build_reader_context("D2", empty_brief, context) == context

    state, _trace = add_decision(
        DecisionState(),
        "Use the verified workflow.",
        authority="manual_api_commit",
    )
    decision_brief = render_decision_brief(state)

    assert build_reader_context("D0", decision_brief, context) == context
    assert build_reader_context("D1", decision_brief, context).startswith("Decision Brief")


def test_decision_relevance_rejects_neighboring_workflows() -> None:
    item_request_decision = (
        "For extra device item requests for agents selected from incident-report criteria, "
        "use Open Records > Items (Item Requests)."
    )
    item_request_question = (
        "In our company's typical workflow, if I am told to create extra device item "
        "requests for agents selected from incident-report criteria, which form should I go to?"
    )
    problem_request_question = (
        "For the task of navigating and creating problem requests from incident-report "
        "results, which fields are unimportant in our typical workflow?"
    )
    report_decision = (
        "To locate an incident-related performance report, use the All filter, type reports, "
        "open View/Run, then locate the relevant report."
    )
    report_question = (
        "My boss asks me to find a report with a specific title that shows agents' "
        "performance and then create and assign problems based on it."
    )

    assert decision_relevant_to_question(item_request_decision, item_request_question)
    assert not decision_relevant_to_question(item_request_decision, problem_request_question)
    assert decision_relevant_to_question(report_decision, report_question)
    assert not decision_relevant_to_question(report_decision, item_request_question)


def test_retrieve_keyword_context_respects_max_chars() -> None:
    question = LongMemEvalV2Question(
        id="q_large_context",
        domain="web",
        environment="forum",
        question_type="dynamic-environment",
        question="Does the alpha page have a textbox?",
        image=None,
        answer="false",
        eval_function="mc_choice_match|require_non_empty=true",
    )
    trajectory = LongMemEvalV2Trajectory(
        id="traj_large_context",
        domain="web",
        environment="forum",
        goal="Inspect the alpha page.",
        outcome="success",
        start_url="https://example.test",
        states=(
            {
                "thought": "alpha page",
                "action": "observe",
                "accessibility_tree": "alpha " + ("x" * 500),
            },
        ),
    )
    example = LongMemEvalV2Example(
        question=question,
        trajectory_ids=(trajectory.id,),
        trajectories=(trajectory,),
    )

    context = retrieve_keyword_context(example, max_items=1, max_chars=80)

    assert 0 < len(context) <= 80
    assert "alpha" in context


def test_automatic_decisions_skip_real_factual_question_types() -> None:
    question = LongMemEvalV2Question(
        id="q_static_real_type",
        domain="enterprise",
        environment="servicenow",
        question_type="static-environment",
        question="When ordering a Dell XPS, what is the extra dollar amount?",
        image=None,
        answer="300",
        eval_function="exact_match",
    )
    trajectory = LongMemEvalV2Trajectory(
        id="traj_workflow",
        domain="enterprise",
        environment="servicenow",
        goal=(
            'Referring to company protocol "Agent Workload Balancing" re-distribute '
            "the problems with hashtag=#PRB052840832."
        ),
        outcome="success",
        start_url="https://enterprise.example.test",
        states=(),
    )
    example = LongMemEvalV2Example(
        question=question,
        trajectory_ids=(trajectory.id,),
        trajectories=(trajectory,),
    )

    state, traces = apply_automatic_decisions(
        DecisionState(),
        example,
        RuleBasedDecisionExtractor(),
    )

    assert state.decisions == ()
    assert traces == [
        {
            "event": "automatic_decision_extraction_skipped",
            "question_id": "q_static_real_type",
            "question_type": "static-environment",
            "reason": "non_decision_question_type",
        }
    ]


def test_run_poc_writes_required_artifacts_for_all_modes(tmp_path: Path) -> None:
    oracle_path = FIXTURE_ROOT / "oracle_decisions.json"

    for mode in ("D0", "D1", "D2"):
        output_dir = tmp_path / mode
        result = run_poc(
            PocConfig(
                data_root=FIXTURE_ROOT,
                output_dir=output_dir,
                mode=mode,
                limit=1,
                oracle_decisions_path=oracle_path,
            )
        )

        assert result.metrics["examples"] == 1
        assert (output_dir / "config.json").exists()
        assert (output_dir / "manifest.json").exists()
        assert (output_dir / "metrics.json").exists()
        assert (output_dir / "predictions.jsonl").exists()
        assert (output_dir / "decision_trace.jsonl").exists()
        assert (output_dir / "brief_trace.jsonl").exists()
        assert (output_dir / "report.md").exists()

    d0_metrics = json.loads((tmp_path / "D0" / "metrics.json").read_text(encoding="utf-8"))
    d1_metrics = json.loads((tmp_path / "D1" / "metrics.json").read_text(encoding="utf-8"))
    d2_metrics = json.loads((tmp_path / "D2" / "metrics.json").read_text(encoding="utf-8"))

    assert d0_metrics["non_empty_decision_briefs"] == 0
    assert d1_metrics["non_empty_decision_briefs"] == 1
    assert d2_metrics["non_empty_decision_briefs"] == 1
    assert d2_metrics["processed_messages"] == 1
    assert d2_metrics["decision_candidates"] == 1
    assert d2_metrics["decision_add_events"] == 1


def test_run_poc_resumes_reader_results_by_default(tmp_path: Path) -> None:
    output_dir = tmp_path / "D0"
    first = run_poc(
        PocConfig(
            data_root=FIXTURE_ROOT,
            output_dir=output_dir,
            mode="D0",
            question_ids=("q_static",),
        )
    )

    assert first.metrics["reader_cache_hits"] == 0
    assert (output_dir / "reader_cache.jsonl").exists()

    second = run_poc(
        PocConfig(
            data_root=FIXTURE_ROOT,
            output_dir=output_dir,
            mode="D0",
            question_ids=("q_static",),
        )
    )

    assert second.metrics["reader_cache_hits"] == 1
    assert second.predictions[0]["reader_cache_hit"] is True


def test_run_poc_suite_writes_comparison_report(tmp_path: Path) -> None:
    result = run_poc_suite(
        PocSuiteConfig(
            data_root=FIXTURE_ROOT,
            output_dir=tmp_path,
            limit=1,
            oracle_decisions_path=FIXTURE_ROOT / "oracle_decisions.json",
        )
    )

    assert "delta_D1_minus_D0" in result.metrics
    assert "static_state_recall" in result.metrics["category_deltas"]
    assert (tmp_path / "suite_metrics.json").exists()
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "D0" / "metrics.json").exists()
    assert (tmp_path / "D1" / "metrics.json").exists()
    assert (tmp_path / "D2" / "metrics.json").exists()
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "Decision Layer POC Suite Report" in report
    assert "Category deltas" in report


def test_run_poc_manifest_records_explicit_subset(tmp_path: Path) -> None:
    output_dir = tmp_path / "D0"
    run_poc(
        PocConfig(
            data_root=FIXTURE_ROOT,
            output_dir=output_dir,
            mode="D0",
            question_ids=("q_workflow",),
        )
    )

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    config = json.loads((output_dir / "config.json").read_text(encoding="utf-8"))

    assert manifest["source_question_rows"] == 2
    assert manifest["source_haystack_entries"] == 2
    assert manifest["selected_question_count"] == 1
    assert manifest["question_ids"] == ["q_workflow"]
    assert manifest["requested_question_ids"] == ["q_workflow"]
    assert manifest["selected_trajectory_count"] == 1
    assert config["question_ids"] == ["q_workflow"]


def test_run_poc_logs_decision_trace_and_final_decisions(tmp_path: Path) -> None:
    output_dir = tmp_path / "D2"
    run_poc(
        PocConfig(
            data_root=FIXTURE_ROOT,
            output_dir=output_dir,
            mode="D2",
            question_ids=("q_static",),
        )
    )

    decision_trace = [
        json.loads(line)
        for line in (output_dir / "decision_trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    brief_trace = [
        json.loads(line)
        for line in (output_dir / "brief_trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert any(trace["event"] == "message_processed" for trace in decision_trace)
    assert any(trace["event"] == "decision_candidate" for trace in decision_trace)
    assert any(trace["event"] == "decision_added" for trace in decision_trace)
    assert brief_trace[0]["final_decisions"][0]["text"] == (
        "use Guest checkout as the default checkout option"
    )


def test_run_poc_computes_decision_audit_metrics(tmp_path: Path) -> None:
    accepted_path = tmp_path / "accepted.json"
    accepted_path.write_text(
        json.dumps({"q_static": ["use Guest checkout as the default checkout option"]}),
        encoding="utf-8",
    )
    result = run_poc(
        PocConfig(
            data_root=FIXTURE_ROOT,
            output_dir=tmp_path / "D2",
            mode="D2",
            question_ids=("q_static",),
            accepted_decisions_path=accepted_path,
        )
    )

    assert result.metrics["decision_audit_enabled"] is True
    assert result.metrics["audited_decisions"] == 1
    assert result.metrics["false_decisions"] == 0
    assert result.metrics["false_decision_rate"] == 0.0
    assert result.metrics["decision_recall"] == 1.0
    assert result.metrics["missing_expected_decisions"] == 0
