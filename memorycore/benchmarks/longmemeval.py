from __future__ import annotations

from memorycore.benchmarks.base import BenchmarkAdapter, BenchmarkExample
from memorycore.benchmarks.json_loader import load_json_records, record_to_example
from memorycore.benchmarks.toy import ToyBenchmark


class LongMemEvalBenchmark(BenchmarkAdapter):
    name = "longmemeval"

    def load(self) -> list[BenchmarkExample]:
        if self.data_path is None:
            examples = ToyBenchmark().load()
            for example in examples:
                example.meta["fixture"] = "tiny_longmemeval_compatible"
            return examples
        return [
            record_to_example(record, fallback_scope="benchmark:longmemeval")
            for record in load_json_records(self.data_path)
        ]

