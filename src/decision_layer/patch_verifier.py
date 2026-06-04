from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PatchVerificationResult:
    ok: bool
    touched_files: tuple[str, ...]
    matched_required_terms: tuple[str, ...]
    missing_required_terms: tuple[str, ...]
    required_files_present: tuple[str, ...]
    missing_required_files: tuple[str, ...]
    unexpected_files: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "touched_files": list(self.touched_files),
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
) -> PatchVerificationResult:
    touched_files = parse_touched_files(patch_text)
    normalized_patch = patch_text.lower()

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
    ok = not missing_required_terms and not missing_required_files and not unexpected_files
    return PatchVerificationResult(
        ok=ok,
        touched_files=touched_files,
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
