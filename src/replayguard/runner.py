"""End-to-end orchestration for a single ReplayGuard fixture."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from replayguard import __version__
from replayguard.adapters import TargetExecutionError, build_target_adapter
from replayguard.analysis import (
    PROMPT_VERSION,
    SemanticAnalysisError,
    _prompt_hash,
    analyze_with_gpt56,
)
from replayguard.fixtures import load_fixture
from replayguard.logging_utils import log_event
from replayguard.models import (
    AnalysisMode,
    ModelRunMetadata,
    ReplayEvaluation,
    ReplayKind,
    RowResult,
    RunMetadata,
    RunResult,
    RunSummary,
    TargetResponse,
    fixture_display_path,
)
from replayguard.perturbations import build_replay_cases, validate_replay_cases
from replayguard.verdicts import (
    evaluate_baseline,
    evaluate_replay,
    execution_error_evaluation,
    invalid_test_evaluation,
)

logger = logging.getLogger(__name__)


def run_fixture(
    fixture_path: Path,
    *,
    target_override: str | None = None,
    analysis_mode: AnalysisMode = AnalysisMode.AUTO,
    model: str | None = None,
    reasoning_effort: str | None = None,
) -> RunResult:
    fixture, fixture_hash = load_fixture(fixture_path)
    cases = build_replay_cases(fixture)
    case_issues = validate_replay_cases(fixture, cases)
    adapter = build_target_adapter(fixture, target_override)
    log_event(
        logger,
        "run_started",
        fixture_id=fixture.id,
        fixture_sha256=fixture_hash,
        target_adapter=adapter.name,
        analysis_mode=analysis_mode.value,
    )

    responses: dict[ReplayKind, TargetResponse] = {}
    target_errors: dict[ReplayKind, str] = {}
    for case in cases:
        try:
            response = adapter.answer(fixture, case)
            if response.verdict not in fixture.output_contract.allowed_verdicts:
                raise TargetExecutionError(
                    f"target verdict {response.verdict.value!r} is not allowed by the fixture"
                )
            responses[case.kind] = response
            log_event(
                logger,
                "target_case_completed",
                fixture_id=fixture.id,
                replay=case.kind.value,
                target_verdict=response.verdict.value,
            )
        except TargetExecutionError as exc:
            target_errors[case.kind] = str(exc)
            log_event(
                logger,
                "target_case_failed",
                fixture_id=fixture.id,
                replay=case.kind.value,
                error=str(exc),
            )
        except Exception as exc:  # fail closed at the external target boundary
            target_errors[case.kind] = f"unexpected target error: {type(exc).__name__}: {exc}"
            log_event(
                logger,
                "target_case_failed",
                fixture_id=fixture.id,
                replay=case.kind.value,
                error=target_errors[case.kind],
            )

    selected_model = model or os.getenv("REPLAYGUARD_MODEL", "gpt-5.6")
    selected_effort = reasoning_effort or os.getenv("REPLAYGUARD_REASONING_EFFORT", "low")
    semantic = {}
    effective_mode = AnalysisMode.DETERMINISTIC
    model_metadata = ModelRunMetadata(
        requested=analysis_mode in {AnalysisMode.AUTO, AnalysisMode.MODEL},
        used=False,
        model_requested=(
            selected_model if analysis_mode in {AnalysisMode.AUTO, AnalysisMode.MODEL} else None
        ),
        reasoning_effort=(
            selected_effort if analysis_mode in {AnalysisMode.AUTO, AnalysisMode.MODEL} else None
        ),
        prompt_version=(
            PROMPT_VERSION if analysis_mode in {AnalysisMode.AUTO, AnalysisMode.MODEL} else None
        ),
        prompt_sha256=(
            _prompt_hash() if analysis_mode in {AnalysisMode.AUTO, AnalysisMode.MODEL} else None
        ),
    )
    semantic_error: str | None = None
    if not target_errors:
        try:
            semantic, model_metadata, effective_mode = analyze_with_gpt56(
                fixture,
                cases,
                responses,
                mode=analysis_mode,
                model=selected_model,
                reasoning_effort=selected_effort,
            )
        except SemanticAnalysisError as exc:
            semantic_error = str(exc)
            model_metadata.warning = semantic_error
            effective_mode = analysis_mode
    elif analysis_mode == AnalysisMode.MODEL:
        semantic_error = "GPT-5.6 analysis was not attempted because target execution failed"
        model_metadata.warning = semantic_error
        effective_mode = AnalysisMode.MODEL
    else:
        model_metadata.warning = "model analysis skipped because target execution failed"

    evaluations: list[ReplayEvaluation] = []
    baseline_case = cases[0]
    baseline_response = responses.get(ReplayKind.BASELINE)
    if baseline_response is None:
        baseline_evaluation = execution_error_evaluation(
            baseline_case,
            target_errors.get(ReplayKind.BASELINE, "baseline target response is unavailable"),
        )
    else:
        baseline_evaluation = evaluate_baseline(fixture, baseline_case, baseline_response)
    evaluations.append(baseline_evaluation)

    baseline_valid = (
        baseline_evaluation.row_result == RowResult.BASELINE and baseline_response is not None
    )
    for case in cases[1:]:
        replay_response = responses.get(case.kind)
        if replay_response is None:
            evaluations.append(
                execution_error_evaluation(
                    case,
                    target_errors.get(case.kind, "target response is unavailable"),
                )
            )
            continue
        if not baseline_valid:
            evaluations.append(
                invalid_test_evaluation(
                    case,
                    "the baseline failed its grounding contract, so this comparison is invalid",
                    replay_response,
                )
            )
            continue
        if semantic_error and analysis_mode == AnalysisMode.MODEL:
            evaluations.append(execution_error_evaluation(case, semantic_error))
            continue
        evaluations.append(
            evaluate_replay(
                fixture,
                case,
                baseline_response,
                replay_response,
                case_issues[case.kind],
                semantic.get(case.kind),
            )
        )

    required = evaluations[1:]
    summary = RunSummary(
        passed=sum(evaluation.row_result == RowResult.PASS for evaluation in required),
        brittle=sum(evaluation.row_result == RowResult.FAIL for evaluation in required),
        invalid=sum(evaluation.row_result == RowResult.INVALID for evaluation in required),
        errors=sum(evaluation.row_result == RowResult.ERROR for evaluation in required),
    )
    summary.overall_pass = (
        baseline_valid
        and summary.passed == summary.required_replays
        and not summary.brittle
        and not summary.invalid
        and not summary.errors
    )

    result = RunResult(
        fixture_id=fixture.id,
        title=fixture.title,
        question=fixture.question,
        claim=fixture.claim,
        metadata=RunMetadata(
            run_id=uuid4().hex[:12],
            created_at=datetime.now(UTC),
            replayguard_version=__version__,
            fixture_path=fixture_display_path(fixture_path),
            fixture_sha256=fixture_hash,
            target_adapter=adapter.name,
            target_endpoint=adapter.endpoint,
            analysis_mode_requested=analysis_mode,
            analysis_mode_effective=effective_mode,
            model=model_metadata,
        ),
        evaluations=evaluations,
        summary=summary,
    )
    log_event(
        logger,
        "run_completed",
        fixture_id=fixture.id,
        exit_code=result.exit_code,
        passed=summary.passed,
        brittle=summary.brittle,
        invalid=summary.invalid,
        errors=summary.errors,
        model_used=model_metadata.used,
    )
    return result
