from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PatchVerificationResult:
    ok: bool
    touched_files: tuple[str, ...]
    test_files: tuple[str, ...]
    benchmark_noise_files: tuple[str, ...]
    matched_required_terms: tuple[str, ...]
    missing_required_terms: tuple[str, ...]
    required_files_present: tuple[str, ...]
    missing_required_files: tuple[str, ...]
    unexpected_files: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "touched_files": list(self.touched_files),
            "test_files": list(self.test_files),
            "benchmark_noise_files": list(self.benchmark_noise_files),
            "matched_required_terms": list(self.matched_required_terms),
            "missing_required_terms": list(self.missing_required_terms),
            "required_files_present": list(self.required_files_present),
            "missing_required_files": list(self.missing_required_files),
            "unexpected_files": list(self.unexpected_files),
        }


def verify_patch(
    patch_text: str,
    *,
    required_terms: tuple[str, ...] = (),
    required_files: tuple[str, ...] = (),
    allowed_files: tuple[str, ...] = (),
    flag_benchmark_noise: bool = False,
) -> PatchVerificationResult:
    touched_files = parse_touched_files(patch_text)
    normalized_patch = patch_text.lower()
    test_files = tuple(path for path in touched_files if is_test_file(path))
    benchmark_noise_files = test_files if flag_benchmark_noise else ()

    matched_required_terms = tuple(
        term for term in required_terms if term.lower() in normalized_patch
    )
    missing_required_terms = tuple(
        term for term in required_terms if term.lower() not in normalized_patch
    )
    touched_file_set = set(touched_files)
    required_files_present = tuple(path for path in required_files if path in touched_file_set)
    missing_required_files = tuple(path for path in required_files if path not in touched_file_set)
    allowed_file_set = set(allowed_files)
    unexpected_files = (
        tuple(path for path in touched_files if path not in allowed_file_set)
        if allowed_files
        else ()
    )
    ok = (
        not missing_required_terms
        and not missing_required_files
        and not unexpected_files
        and not benchmark_noise_files
    )
    return PatchVerificationResult(
        ok=ok,
        touched_files=touched_files,
        test_files=test_files,
        benchmark_noise_files=benchmark_noise_files,
        matched_required_terms=matched_required_terms,
        missing_required_terms=missing_required_terms,
        required_files_present=required_files_present,
        missing_required_files=missing_required_files,
        unexpected_files=unexpected_files,
    )


def parse_touched_files(patch_text: str) -> tuple[str, ...]:
    files: list[str] = []
    seen: set[str] = set()
    for line in patch_text.splitlines():
        path = path_from_diff_line(line)
        if path and path not in seen:
            seen.add(path)
            files.append(path)
    return tuple(files)


def path_from_diff_line(line: str) -> str | None:
    if line.startswith("diff --git "):
        parts = line.split()
        if len(parts) >= 4:
            return normalize_diff_path(parts[3])
    if line.startswith("+++ "):
        return normalize_diff_path(line[4:].strip())
    return None


def normalize_diff_path(path: str) -> str | None:
    if path == "/dev/null":
        return None
    if path.startswith("b/"):
        return path[2:]
    return path


def is_test_file(path: str) -> bool:
    parts = path.split("/")
    filename = parts[-1] if parts else path
    stem = filename.rsplit(".", 1)[0]
    if any(part in {"test", "tests", "testing"} for part in parts[:-1]):
        return True
    return (
        filename.startswith("test_")
        or filename.endswith("_test.py")
        or filename.endswith(".test.js")
        or stem.startswith("test_")
        or stem.endswith("_test")
    )
