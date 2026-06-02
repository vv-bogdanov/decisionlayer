from __future__ import annotations

from memorycore.benchmarks.base import BenchmarkAdapter, BenchmarkExample, Message


class ToyBenchmark(BenchmarkAdapter):
    name = "toy"

    def load(self) -> list[BenchmarkExample]:
        return [
            BenchmarkExample(
                id="toy-1",
                scope="project:toy",
                messages=[
                    Message("user", "FACT: The MVP database choice is SQLite."),
                    Message("user", "COMMIT DECISION: project.db = SQLite"),
                    Message("assistant", "FACT: SQLite was selected because it is cheap to run."),
                ],
                question="Which database should the MVP use?",
                expected_answer="SQLite",
            ),
            BenchmarkExample(
                id="toy-2",
                scope="project:toy",
                messages=[
                    Message("user", "COMMIT DECISION: assistant.language = Russian"),
                    Message("user", "FACT: User wants concise engineering answers."),
                ],
                question="Which language should the assistant answer in?",
                expected_answer="Russian",
            ),
        ]

