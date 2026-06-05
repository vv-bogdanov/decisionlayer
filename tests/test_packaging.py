from __future__ import annotations

import pathlib
import tomllib


ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_pyproject_exposes_cli_entrypoint() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert data["build-system"]["build-backend"] == "hatchling.build"
    assert data["project"]["scripts"]["repo-decisions"] == "repo_decisions.cli:main"
    assert data["project"]["urls"]["Repository"] == "https://github.com/vv-bogdanov/memorycore"
    assert data["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "repo_decisions"
    ]


def test_release_scripts_cover_wheel_install_smoke() -> None:
    check = (ROOT / "scripts/check").read_text(encoding="utf-8")
    check_wheel = ROOT / "scripts/check-wheel"

    assert check_wheel.exists()
    assert "scripts/check-wheel" in check
    assert "repo-decisions\" --help" in check_wheel.read_text(encoding="utf-8")
