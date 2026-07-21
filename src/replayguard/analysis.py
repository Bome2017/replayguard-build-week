"""One GPT-5.6 structured assessment that assists, but never owns, final verdicts."""

from __future__ import annotations

import hashlib
import json
import os

from pydantic import ValidationError

from replayguard.models import (
    AnalysisMode,
    Fixture,
    ModelRunMetadata,
    ReplayCase,
    ReplayKind,
    SemanticAssessment,
    SemanticAssessmentBatch,
    TargetResponse,
)

PROMPT_VERSION = "replayguard-semantic-v1"
SYSTEM_PROMPT = """You are the semantic comparison component inside ReplayGuard, a
metamorphic testing tool for evidence-grounded AI systems. The evidence packet supplied for
each replay is the entire evidential universe. Compare outputs and evidence; do not use outside
knowledge. Do not decide PASS, FAIL, or the final ReplayGuard verdict. For equivalent and
distractor cases, assess whether material claims remain semantically equivalent. For removed
support and no-evidence cases, identify affirmative claims that persist without packet support.
Extract concise normalized atomic claims from both baseline and replay outputs. Map every replay
citation to an evidence ID when possible and state whether that evidence supports the cited
claim. Treat an equivalent-evidence contract as valid only when its replacement preserves the
baseline evidence's operative meaning. Treat a distractor contract as valid only when the
addition is irrelevant to the claim. Return exactly one assessment for each of: equivalent,
distractor, support_removed, no_evidence."""


class SemanticAnalysisError(RuntimeError):
    """A required model-assisted analysis could not complete."""


def _prompt_hash() -> str:
    return hashlib.sha256(f"{PROMPT_VERSION}\n{SYSTEM_PROMPT}".encode()).hexdigest()


def _analysis_payload(
    fixture: Fixture,
    cases: list[ReplayCase],
    responses: dict[ReplayKind, TargetResponse],
) -> str:
    baseline = responses[ReplayKind.BASELINE]
    replays = []
    for case in cases:
        if case.kind == ReplayKind.BASELINE:
            continue
        replays.append(
            {
                "replay": case.kind.value,
                "expected_transition": case.expected_transition,
                "evidence": [
                    {
                        "id": document.id,
                        "text": document.text,
                        "declared_role": document.role,
                        "declared_supports_claim": document.supports_claim,
                        "equivalent_to": document.equivalent_to,
                    }
                    for document in case.evidence
                ],
                "target_output": responses[case.kind].model_dump(mode="json"),
            }
        )
    payload = {
        "question": fixture.question,
        "claim_under_test": fixture.claim,
        "baseline_evidence": [
            {"id": document.id, "text": document.text} for document in cases[0].evidence
        ],
        "baseline_output": baseline.model_dump(mode="json"),
        "replays": replays,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def analyze_with_gpt56(
    fixture: Fixture,
    cases: list[ReplayCase],
    responses: dict[ReplayKind, TargetResponse],
    *,
    mode: AnalysisMode,
    model: str,
    reasoning_effort: str,
) -> tuple[dict[ReplayKind, SemanticAssessment], ModelRunMetadata, AnalysisMode]:
    requested = mode in {AnalysisMode.AUTO, AnalysisMode.MODEL}
    metadata = ModelRunMetadata(
        requested=requested,
        used=False,
        model_requested=model if requested else None,
        reasoning_effort=reasoning_effort if requested else None,
        prompt_version=PROMPT_VERSION if requested else None,
        prompt_sha256=_prompt_hash() if requested else None,
    )

    if mode == AnalysisMode.DETERMINISTIC:
        return {}, metadata, AnalysisMode.DETERMINISTIC

    if not os.getenv("OPENAI_API_KEY"):
        message = (
            "OPENAI_API_KEY is not set; GPT-5.6 semantic assessment did not run. "
            "Use --analysis-mode model to fail closed when the model call is required."
        )
        if mode == AnalysisMode.MODEL:
            raise SemanticAnalysisError(message)
        metadata.warning = message
        return {}, metadata, AnalysisMode.DETERMINISTIC

    try:
        from openai import OpenAI

        client = OpenAI()
        response = None
        parsed = None
        for attempt in (1, 2):
            metadata.structured_output_attempts = attempt
            try:
                response = client.responses.parse(
                    model=model,
                    reasoning={"effort": reasoning_effort},
                    input=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": _analysis_payload(fixture, cases, responses)},
                    ],
                    text_format=SemanticAssessmentBatch,
                    max_output_tokens=3000,
                    store=False,
                )
                parsed = response.output_parsed
                if parsed is None:
                    raise SemanticAnalysisError("GPT-5.6 returned no parsed semantic assessment")
                break
            except (SemanticAnalysisError, ValidationError) as exc:
                if attempt == 2:
                    raise SemanticAnalysisError(
                        f"GPT-5.6 failed the structured assessment schema after two attempts: {exc}"
                    ) from exc

        if response is None or parsed is None:  # pragma: no cover - loop exhaustiveness guard
            raise SemanticAnalysisError("GPT-5.6 structured assessment was unavailable")

        metadata.used = True
        metadata.response_id = getattr(response, "id", None)
        metadata.model_returned = getattr(response, "model", None)
        usage = getattr(response, "usage", None)
        if usage is not None:
            metadata.usage = usage.model_dump(mode="json")
        assessments = {assessment.replay: assessment for assessment in parsed.assessments}
        return assessments, metadata, AnalysisMode.MODEL
    except SemanticAnalysisError:
        raise
    except Exception as exc:
        message = f"GPT-5.6 semantic assessment failed: {type(exc).__name__}: {exc}"
        if mode == AnalysisMode.MODEL:
            raise SemanticAnalysisError(message) from exc
        metadata.warning = message
        return {}, metadata, AnalysisMode.DETERMINISTIC
