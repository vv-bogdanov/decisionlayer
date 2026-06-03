import json

from decision_layer.cli import main


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
