"""ReplayGuard command-line interface."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer

from replayguard.adapters import TargetExecutionError
from replayguard.fixtures import FixtureError
from replayguard.logging_utils import configure_logging
from replayguard.models import AnalysisMode, ReplayKind, RowResult
from replayguard.report import write_report
from replayguard.runner import run_fixture

app = typer.Typer(
    name="replayguard",
    help="Metamorphic regression testing for evidence-grounded AI systems.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def main() -> None:
    """Run evidence-grounding contracts in local development or CI."""


@app.command("test")
def test_fixture(
    fixture: Annotated[
        Path,
        typer.Argument(
            ...,
            exists=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            help="YAML fixture defining the claim, evidence, transformations, and target.",
        ),
    ],
    target: Annotated[
        str | None,
        typer.Option(
            "--target",
            help="Override the fixture target with a ReplayGuard JSON HTTP endpoint.",
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Report directory. Defaults to reports/<fixture-name>.",
        ),
    ] = None,
    analysis_mode: Annotated[
        AnalysisMode,
        typer.Option(
            "--analysis-mode",
            help=(
                "auto uses GPT-5.6 when a key exists; model fails closed; deterministic is offline."
            ),
        ),
    ] = AnalysisMode.AUTO,
    model: Annotated[
        str,
        typer.Option("--model", help="OpenAI model for the structured semantic assessment."),
    ] = os.getenv("REPLAYGUARD_MODEL", "gpt-5.6"),
    reasoning_effort: Annotated[
        str,
        typer.Option("--reasoning-effort", help="Explicit GPT-5.6 reasoning effort."),
    ] = os.getenv("REPLAYGUARD_REASONING_EFFORT", "low"),
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Emit structured execution logs to stderr."),
    ] = False,
) -> None:
    configure_logging(verbose=verbose)
    report_directory = output or Path("reports") / fixture.stem
    try:
        result = run_fixture(
            fixture,
            target_override=target,
            analysis_mode=analysis_mode,
            model=model,
            reasoning_effort=reasoning_effort,
        )
        html_path, _ = write_report(result, report_directory)
    except (FixtureError, TargetExecutionError) as exc:
        typer.echo(f"ReplayGuard configuration error\n{exc}", err=True)
        raise typer.Exit(code=2) from exc

    typer.echo(f"ReplayGuard: {result.title}\n")
    for evaluation in result.evaluations:
        if evaluation.kind == ReplayKind.BASELINE:
            continue
        display_result = {
            RowResult.PASS: "PASS",
            RowResult.FAIL: "FAIL",
            RowResult.INVALID: "INVALID",
            RowResult.ERROR: "ERROR",
        }[evaluation.row_result]
        typer.echo(f"{evaluation.label:<28} {display_result:<7} {evaluation.verdict.value}")

    typer.echo(
        f"\n{result.summary.passed} passed, {result.summary.brittle} brittle, "
        f"{result.summary.invalid} invalid, {result.summary.errors} errors"
    )
    model_status = (
        f"used ({result.metadata.model.model_returned or result.metadata.model.model_requested})"
        if result.metadata.model.used
        else "not used"
    )
    typer.echo(f"GPT-5.6 semantic assessment: {model_status}")
    if result.metadata.model.warning:
        typer.echo(f"Warning: {result.metadata.model.warning}")
    typer.echo(f"Report: {html_path.resolve()}")
    typer.echo(f"Exit status: {result.exit_code}")
    raise typer.Exit(code=result.exit_code)
