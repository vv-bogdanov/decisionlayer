from __future__ import annotations

from memorycore.benchmarks.base import BenchmarkAdapter, BenchmarkExample
from memorycore.benchmarks.json_loader import load_json_records, record_to_example


class MemoryAgentBenchBenchmark(BenchmarkAdapter):
    name = "memoryagentbench"

    def load(self) -> list[BenchmarkExample]:
        if self.data_path is None:
            raise ValueError("memoryagentbench requires data_path")
        return self.apply_window(
            [
                record_to_example(record, fallback_scope="benchmark:memoryagentbench")
                for record in load_json_records(self.data_path)
            ]
        )
