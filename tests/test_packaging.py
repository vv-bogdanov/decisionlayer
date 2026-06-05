from __future__ import annotations

import pathlib
import tomllib


ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_pyproject_exposes_cli_entrypoint() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert data["build-system"]["build-backend"] == "hatchling.build"
    assert data["project"]["scripts"]["repo-decisions"] == "repo_decisions.cli:main"
    assert data["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "repo_decisions"
    ]
