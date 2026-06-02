from __future__ import annotations

from memorycore.benchmarks.base import BenchmarkAdapter, BenchmarkExample
from memorycore.benchmarks.json_loader import load_json_records, record_to_example


class HaluMemBenchmark(BenchmarkAdapter):
    name = "halumem"

    def load(self) -> list[BenchmarkExample]:
        if self.data_path is None:
            raise ValueError("halumem requires data_path")
        return self.apply_window([
            record_to_example(record, fallback_scope="benchmark:halumem")
            for record in load_json_records(self.data_path)
        ])
