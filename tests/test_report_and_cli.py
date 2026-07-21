import json
from pathlib import Path

from typer.testing import CliRunner

from replayguard.cli import app
from replayguard.models import AnalysisMode
from replayguard.report import write_report
from replayguard.runner import run_fixture


def test_report_contains_transition_matrix_and_machine_readable_result(
    brittle_fixture_path, tmp_path
):
    result = run_fixture(brittle_fixture_path, analysis_mode=AnalysisMode.DETERMINISTIC)
    html_path, json_path = write_report(result, tmp_path / "report")

    html = html_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert "Transition matrix" in html
    assert "Brittleness detected" in html
    assert "Decisive support removed" in html
    assert "Deterministic transition rules own the final verdict" in html
    assert "confidence delta" in html
    assert "diagnostic only because the verdict class changed" in html
    assert payload["summary"]["brittle"] == 3
    assert payload["evaluations"][2]["verdict"] == "brittle"
    support_removed = next(
        evaluation
        for evaluation in payload["evaluations"]
        if evaluation["kind"] == "support_removed"
    )
    confidence_check = next(
        check for check in support_removed["checks"] if check["name"] == "confidence delta"
    )
    assert confidence_check["gating"] is False
    assert not Path(payload["report_directory"]).is_absolute()


def test_cli_exit_codes_and_report_paths(clean_fixture_path, brittle_fixture_path, tmp_path):
    runner = CliRunner()
    clean_output = tmp_path / "clean"
    clean = runner.invoke(
        app,
        [
            "test",
            str(clean_fixture_path),
            "--analysis-mode",
            "deterministic",
            "--output",
            str(clean_output),
        ],
    )
    assert clean.exit_code == 0
    assert "4 passed, 0 brittle" in clean.stdout
    assert (clean_output / "index.html").exists()

    brittle_output = tmp_path / "brittle"
    brittle = runner.invoke(
        app,
        [
            "test",
            str(brittle_fixture_path),
            "--analysis-mode",
            "deterministic",
            "--output",
            str(brittle_output),
        ],
    )
    assert brittle.exit_code == 1
    assert "1 passed, 3 brittle" in brittle.stdout
    assert (brittle_output / "result.json").exists()
