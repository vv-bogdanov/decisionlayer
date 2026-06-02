from __future__ import annotations

from memorycore.benchmarks.base import BenchmarkAdapter
from memorycore.benchmarks.halumem import HaluMemBenchmark
from memorycore.benchmarks.locomo import LoCoMoBenchmark
from memorycore.benchmarks.longmemeval import LongMemEvalBenchmark
from memorycore.benchmarks.memoryagentbench import MemoryAgentBenchBenchmark
from memorycore.benchmarks.toy import ToyBenchmark


BENCHMARKS: dict[str, type[BenchmarkAdapter]] = {
    "toy": ToyBenchmark,
    "longmemeval": LongMemEvalBenchmark,
    "locomo": LoCoMoBenchmark,
    "halumem": HaluMemBenchmark,
    "memoryagentbench": MemoryAgentBenchBenchmark,
}


def get_benchmark(
    name: str,
    *,
    data_path: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> BenchmarkAdapter:
    try:
        benchmark_cls = BENCHMARKS[name]
    except KeyError as exc:
        known = ", ".join(sorted(BENCHMARKS))
        raise ValueError(f"unknown benchmark: {name}; known: {known}") from exc
    return benchmark_cls(data_path=data_path, limit=limit, offset=offset)
