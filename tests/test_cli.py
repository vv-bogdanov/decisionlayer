import json
from pathlib import Path

from decision_layer.cli import main

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "longmemeval_v2"


def test_cli_add_list_brief_and_remove(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    state_path = tmp_path / "state.json"

    assert main(["--state", str(state_path), "add", "Use Python for the POC."]) == 0
    add_output = json.loads(capsys.readouterr().out)
    decision_id = add_output["decision_id"]

    assert main(["--state", str(state_path), "list"]) == 0
    list_output = json.loads(capsys.readouterr().out)
    assert list_output[0]["text"] == "Use Python for the POC."

    assert main(["--state", str(state_path), "brief"]) == 0
    brief_output = capsys.readouterr().out
    assert "Decision Brief" in brief_output
    assert "Use Python for the POC." in brief_output

    assert main(["--state", str(state_path), "remove", decision_id]) == 0
    capsys.readouterr()
    assert main(["--state", str(state_path), "list"]) == 0
    assert json.loads(capsys.readouterr().out) == []


def test_cli_run_poc_accepts_question_id_file(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    id_file = tmp_path / "question_ids.txt"
    id_file.write_text("# comment\nq_workflow # inline comment\n", encoding="utf-8")
    output_dir = tmp_path / "run"

    assert (
        main(
            [
                "run-poc",
                "--data-root",
                str(FIXTURE_ROOT),
                "--output-dir",
                str(output_dir),
                "--mode",
                "D0",
                "--question-id-file",
                str(id_file),
            ]
        )
        == 0
    )
    capsys.readouterr()

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["question_ids"] == ["q_workflow"]
