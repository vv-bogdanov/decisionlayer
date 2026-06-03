from pathlib import Path

import pytest

from decision_layer.benchmarks.longmemeval_v2 import load_longmemeval_v2_examples

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "longmemeval_v2"


def test_load_longmemeval_v2_subset_fixture() -> None:
    examples = load_longmemeval_v2_examples(FIXTURE_ROOT, tier="small", limit=1)

    assert len(examples) == 1
    example = examples[0]
    assert example.question.id == "q_static"
    assert example.question.question_type == "static_state_recall"
    assert example.question.answer == "Guest checkout"
    assert example.trajectory_ids == ("traj_shop_1",)
    assert example.trajectories[0].states[0]["accessibility_tree"] == (
        "Guest checkout is selected by default."
    )


def test_load_longmemeval_v2_subset_by_question_id() -> None:
    examples = load_longmemeval_v2_examples(
        FIXTURE_ROOT,
        tier="small",
        question_ids={"q_workflow"},
    )

    assert len(examples) == 1
    assert examples[0].question.id == "q_workflow"
    assert examples[0].trajectories[0].id == "traj_ticket_1"


def test_load_longmemeval_v2_rejects_unknown_question_id() -> None:
    with pytest.raises(ValueError, match="unknown question ids requested"):
        load_longmemeval_v2_examples(
            FIXTURE_ROOT,
            tier="small",
            question_ids={"missing"},
        )
