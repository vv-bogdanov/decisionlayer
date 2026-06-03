from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class LongMemEvalV2Question:
    id: str
    domain: str
    environment: str
    question_type: str
    question: str
    image: str | None
    answer: str
    eval_function: str


@dataclass(frozen=True, slots=True)
class LongMemEvalV2Trajectory:
    id: str
    domain: str
    environment: str
    goal: str
    outcome: str
    start_url: str
    states: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class LongMemEvalV2Example:
    question: LongMemEvalV2Question
    trajectory_ids: tuple[str, ...]
    trajectories: tuple[LongMemEvalV2Trajectory, ...]


def load_longmemeval_v2_examples(
    data_root: str | Path,
    *,
    tier: str = "small",
    limit: int | None = None,
    question_ids: set[str] | None = None,
) -> tuple[LongMemEvalV2Example, ...]:
    root = Path(data_root)
    questions = load_questions(root / "questions.jsonl")
    haystacks = load_haystacks(root / "haystacks" / f"lme_v2_{tier}.json")
    selected_questions = select_questions(
        questions, haystacks, limit=limit, question_ids=question_ids
    )
    required_trajectory_ids = {
        trajectory_id for question in selected_questions for trajectory_id in haystacks[question.id]
    }
    trajectories = load_trajectories(root / "trajectories.jsonl", required_trajectory_ids)

    examples: list[LongMemEvalV2Example] = []
    for question in selected_questions:
        trajectory_ids = tuple(str(trajectory_id) for trajectory_id in haystacks[question.id])
        examples.append(
            LongMemEvalV2Example(
                question=question,
                trajectory_ids=trajectory_ids,
                trajectories=tuple(trajectories[trajectory_id] for trajectory_id in trajectory_ids),
            )
        )
    return tuple(examples)


def load_questions(path: Path) -> dict[str, LongMemEvalV2Question]:
    records = {}
    for record in read_jsonl(path):
        question = LongMemEvalV2Question(
            id=str(record["id"]),
            domain=str(record["domain"]),
            environment=str(record["environment"]),
            question_type=str(record["question_type"]),
            question=str(record["question"]),
            image=str(record["image"]) if record.get("image") is not None else None,
            answer=str(record["answer"]),
            eval_function=str(record["eval_function"]),
        )
        records[question.id] = question
    return records


def load_haystacks(path: Path) -> dict[str, tuple[str, ...]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"haystack file must contain an object: {path}")
    haystacks: dict[str, tuple[str, ...]] = {}
    for question_id, trajectory_ids in data.items():
        if not isinstance(trajectory_ids, list):
            raise ValueError(f"haystack value must be a list for question id: {question_id}")
        haystacks[str(question_id)] = tuple(str(trajectory_id) for trajectory_id in trajectory_ids)
    return haystacks


def load_trajectories(
    path: Path,
    required_ids: set[str],
) -> dict[str, LongMemEvalV2Trajectory]:
    trajectories: dict[str, LongMemEvalV2Trajectory] = {}
    for record in read_jsonl(path):
        trajectory_id = str(record["id"])
        if trajectory_id not in required_ids:
            continue
        raw_states = record.get("states")
        states = tuple(dict(state) for state in raw_states) if isinstance(raw_states, list) else ()
        trajectories[trajectory_id] = LongMemEvalV2Trajectory(
            id=trajectory_id,
            domain=str(record["domain"]),
            environment=str(record["environment"]),
            goal=str(record["goal"]),
            outcome=str(record["outcome"]),
            start_url=str(record["start_url"]),
            states=states,
        )
        if len(trajectories) == len(required_ids):
            break

    missing = sorted(required_ids - set(trajectories))
    if missing:
        preview = ", ".join(missing[:5])
        raise ValueError(f"missing {len(missing)} trajectories referenced by haystack: {preview}")
    return trajectories


def select_questions(
    questions: dict[str, LongMemEvalV2Question],
    haystacks: dict[str, tuple[str, ...]],
    *,
    limit: int | None,
    question_ids: set[str] | None,
) -> tuple[LongMemEvalV2Question, ...]:
    selected = []
    for question_id in sorted(haystacks):
        if question_ids is not None and question_id not in question_ids:
            continue
        try:
            selected.append(questions[question_id])
        except KeyError as exc:
            raise ValueError(f"haystack references missing question id: {question_id}") from exc
        if limit is not None and len(selected) >= limit:
            break
    return tuple(selected)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        data = json.loads(line)
        if not isinstance(data, dict):
            raise ValueError(f"JSONL line must be an object at {path}:{line_number}")
        records.append(data)
    return records
