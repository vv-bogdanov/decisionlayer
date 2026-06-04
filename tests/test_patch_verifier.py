import json
from pathlib import Path

from decision_layer.cli import main
from decision_layer.patch_verifier import parse_touched_files, verify_patch

PATCH = """diff --git a/sphinx/pycode/ast.py b/sphinx/pycode/ast.py
--- a/sphinx/pycode/ast.py
+++ b/sphinx/pycode/ast.py
@@ -1,3 +1,5 @@
+def visit_Subscript(self, node):
+    return "ok"
diff --git a/sphinx/domains/python.py b/sphinx/domains/python.py
--- a/sphinx/domains/python.py
+++ b/sphinx/domains/python.py
@@ -1,3 +1,4 @@
+annotation = "changed"
"""


def test_parse_touched_files_from_unified_diff() -> None:
    assert parse_touched_files(PATCH) == (
        "sphinx/pycode/ast.py",
        "sphinx/domains/python.py",
    )


def test_verify_patch_flags_missing_terms_and_unexpected_files() -> None:
    result = verify_patch(
        PATCH,
        required_terms=("visit_Subscript", "is_simple_tuple"),
        required_files=("sphinx/pycode/ast.py",),
        allowed_files=("sphinx/pycode/ast.py",),
    )

    assert result.ok is False
    assert result.matched_required_terms == ("visit_Subscript",)
    assert result.missing_required_terms == ("is_simple_tuple",)
    assert result.required_files_present == ("sphinx/pycode/ast.py",)
    assert result.unexpected_files == ("sphinx/domains/python.py",)
    assert result.test_files == ()
    assert result.benchmark_noise_files == ()


def test_verify_patch_flags_test_files_as_benchmark_noise() -> None:
    patch = """diff --git a/tests/test_backend_svg.py b/tests/test_backend_svg.py
--- a/tests/test_backend_svg.py
+++ b/tests/test_backend_svg.py
@@ -1,2 +1,3 @@
+def test_new_behavior():
+    pass
"""

    result = verify_patch(patch, flag_benchmark_noise=True)

    assert result.ok is False
    assert result.test_files == ("tests/test_backend_svg.py",)
    assert result.benchmark_noise_files == ("tests/test_backend_svg.py",)


def test_cli_verify_patch_returns_nonzero_on_failed_check(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    patch_path = tmp_path / "patch.diff"
    patch_path.write_text(PATCH, encoding="utf-8")

    assert (
        main(
            [
                "verify-patch",
                "--patch",
                str(patch_path),
                "--require-term",
                "is_simple_tuple",
                "--allow-file",
                "sphinx/pycode/ast.py",
            ]
        )
        == 1
    )

    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is False
    assert output["missing_required_terms"] == ["is_simple_tuple"]
    assert output["unexpected_files"] == ["sphinx/domains/python.py"]
