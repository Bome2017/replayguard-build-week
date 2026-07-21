"""Deterministic metamorphic transition rules with explicit model-assisted inputs."""

from __future__ import annotations

import re
import unicodedata

from replayguard.models import (
    CheckResult,
    ComparisonDetails,
    Fixture,
    ReplayCase,
    ReplayEvaluation,
    ReplayKind,
    ReplayVerdict,
    RowResult,
    SemanticAssessment,
    TargetResponse,
    TargetVerdict,
)


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def normalized_claims(response: TargetResponse) -> set[str]:
    return {normalize_text(claim) for claim in response.material_claims if claim.strip()}


def observed_transition(baseline: TargetResponse, replay: TargetResponse) -> str:
    if replay.verdict == baseline.verdict:
        return f"verdict unchanged ({replay.verdict.value})"
    if replay.verdict == TargetVerdict.INSUFFICIENT_EVIDENCE:
        return "changed to insufficient evidence"
    if replay.verdict == TargetVerdict.REFUTED:
        return "reversed to refuted"
    return f"changed from {baseline.verdict.value} to {replay.verdict.value}"


def _citations_resolve(response: TargetResponse, case: ReplayCase) -> tuple[bool, list[str]]:
    available = {document.id for document in case.evidence}
    missing = sorted(set(response.citations) - available)
    return not missing, missing


def _material_claims_advisory(
    baseline: TargetResponse,
    replay: TargetResponse,
    semantic: SemanticAssessment | None,
) -> CheckResult:
    exact = normalized_claims(baseline) == normalized_claims(replay)
    if exact:
        return CheckResult(
            name="material claim prose comparison",
            passed=True,
            gating=False,
            detail="normalized material-claim sets match",
        )
    if semantic and semantic.claims_materially_equivalent and semantic.confidence >= 0.7:
        return CheckResult(
            name="material claim prose comparison",
            passed=True,
            gating=False,
            source="model_assisted",
            detail=(
                f"GPT-5.6 judged the prose materially equivalent "
                f"(confidence {semantic.confidence:.2f})"
            ),
        )
    return CheckResult(
        name="material claim prose comparison",
        passed=False,
        gating=False,
        source="model_assisted" if semantic else "deterministic",
        detail="material-claim prose differs; advisory only because verdict expresses disposition",
    )


def _comparison_details(
    baseline: TargetResponse,
    replay: TargetResponse,
    case: ReplayCase,
    semantic: SemanticAssessment | None,
) -> ComparisonDetails:
    same_answer = normalize_text(baseline.answer) == normalize_text(replay.answer)
    same_claims = normalized_claims(baseline) == normalized_claims(replay)
    citations_ok, missing = _citations_resolve(replay, case)
    surviving = [document.id for document in case.evidence if document.supports_claim]
    answer_detail = "normalized answer unchanged" if same_answer else "answer text changed"
    if semantic:
        answer_detail += f"; GPT-5.6 relation={semantic.answer_relation}"
    claim_detail = "normalized material claims match" if same_claims else "material claims differ"
    if semantic:
        claim_detail += (
            f"; GPT-5.6 extracted {len(semantic.baseline_normalized_claims)} baseline and "
            f"{len(semantic.replay_normalized_claims)} replay claim(s)"
        )
    citation_detail = (
        "all citation IDs resolve in the replay packet"
        if citations_ok
        else f"citations missing from replay packet: {', '.join(missing)}"
    )
    support_detail = (
        f"declared support survives in: {', '.join(surviving)}"
        if surviving
        else "no declared claim support survives in the replay packet"
    )
    return ComparisonDetails(
        answer=answer_detail,
        claims=claim_detail,
        citations=citation_detail,
        surviving_support=support_detail,
    )


def _failure_explanation(checks: list[CheckResult], prefix: str) -> str:
    failed = [check.detail for check in checks if not check.passed]
    return f"{prefix}: " + "; ".join(failed)


def evaluate_baseline(
    fixture: Fixture,
    case: ReplayCase,
    response: TargetResponse,
) -> ReplayEvaluation:
    citations_ok, missing = _citations_resolve(response, case)
    supported_citations = {document.id for document in case.evidence if document.supports_claim}
    checks = [
        CheckResult(
            name="expected baseline verdict",
            passed=response.verdict == fixture.assertions.expected_baseline_verdict,
            detail=(
                f"observed {response.verdict.value}; expected "
                f"{fixture.assertions.expected_baseline_verdict.value}"
            ),
        ),
        CheckResult(
            name="baseline citations resolve",
            passed=citations_ok,
            detail=(
                "all baseline citations resolve"
                if citations_ok
                else f"missing citation IDs: {', '.join(missing)}"
            ),
        ),
        CheckResult(
            name="baseline cites declared support",
            passed=bool(set(response.citations) & supported_citations),
            detail="at least one citation points to declared claim support",
        ),
        CheckResult(
            name="verdict allowed by output contract",
            passed=response.verdict in fixture.output_contract.allowed_verdicts,
            detail=f"verdict={response.verdict.value}",
        ),
    ]
    valid = all(check.passed for check in checks)
    return ReplayEvaluation(
        kind=case.kind,
        label=case.label,
        evidence_state=case.evidence_state,
        expected_transition=case.expected_transition,
        observed_transition=f"baseline verdict={response.verdict.value}",
        row_result=RowResult.BASELINE if valid else RowResult.INVALID,
        verdict=ReplayVerdict.BASELINE if valid else ReplayVerdict.INVALID_TEST,
        target_response=response,
        evidence=case.evidence,
        comparison=ComparisonDetails(
            answer="baseline captured",
            claims=f"{len(response.material_claims)} material claim(s)",
            citations="all citation IDs resolve" if citations_ok else "baseline citation failure",
            surviving_support=f"{len(supported_citations)} declared supporting document(s)",
        ),
        checks=checks,
        explanation=(
            "Baseline is valid and can anchor metamorphic comparisons."
            if valid
            else _failure_explanation(checks, "Baseline cannot anchor a valid test")
        ),
    )


def evaluate_replay(
    fixture: Fixture,
    case: ReplayCase,
    baseline: TargetResponse,
    replay: TargetResponse,
    structural_issues: list[str],
    semantic: SemanticAssessment | None,
) -> ReplayEvaluation:
    comparison = _comparison_details(baseline, replay, case, semantic)
    citations_ok, missing = _citations_resolve(replay, case)
    verdict_same = replay.verdict == baseline.verdict
    claims_advisory = _material_claims_advisory(baseline, replay, semantic)
    checks: list[CheckResult] = []

    if structural_issues:
        checks.append(
            CheckResult(
                name="deterministic perturbation contract",
                passed=False,
                detail="; ".join(structural_issues),
            )
        )
        return ReplayEvaluation(
            kind=case.kind,
            label=case.label,
            evidence_state=case.evidence_state,
            expected_transition=case.expected_transition,
            observed_transition=observed_transition(baseline, replay),
            row_result=RowResult.INVALID,
            verdict=ReplayVerdict.INVALID_TEST,
            target_response=replay,
            evidence=case.evidence,
            added_evidence_ids=case.added_evidence_ids,
            removed_evidence_ids=case.removed_evidence_ids,
            comparison=comparison,
            checks=checks,
            explanation=_failure_explanation(checks, "Replay fixture is structurally invalid"),
        )

    if case.kind in {ReplayKind.EQUIVALENT, ReplayKind.DISTRACTOR} and semantic:
        checks.append(
            CheckResult(
                name="semantic perturbation contract",
                passed=semantic.evidence_contract_valid,
                source="model_assisted",
                detail=semantic.explanation,
            )
        )
        if not semantic.evidence_contract_valid and semantic.confidence >= 0.8:
            return ReplayEvaluation(
                kind=case.kind,
                label=case.label,
                evidence_state=case.evidence_state,
                expected_transition=case.expected_transition,
                observed_transition=observed_transition(baseline, replay),
                row_result=RowResult.INVALID,
                verdict=ReplayVerdict.INVALID_TEST,
                target_response=replay,
                evidence=case.evidence,
                added_evidence_ids=case.added_evidence_ids,
                removed_evidence_ids=case.removed_evidence_ids,
                comparison=comparison,
                checks=checks,
                explanation="GPT-5.6 detected a high-confidence malformed semantic perturbation.",
            )

    if case.kind == ReplayKind.EQUIVALENT:
        equivalent_citation_map = {
            document.id: document.equivalent_to or document.id for document in case.evidence
        }
        baseline_citations = set(baseline.citations)
        citations_equivalent = (
            citations_ok
            and bool(replay.citations)
            and all(
                equivalent_citation_map.get(citation, citation) in baseline_citations
                for citation in replay.citations
            )
        )
        gates = [
            CheckResult(
                name="normalized verdict unchanged",
                passed=verdict_same,
                detail=observed_transition(baseline, replay),
            ),
            CheckResult(
                name="citations resolve to equivalent support",
                passed=citations_equivalent,
                detail=(
                    "replay citations resolve through the declared equivalence map"
                    if citations_equivalent
                    else "replay citations do not resolve to equivalent baseline support"
                ),
            ),
        ]
        checks.extend(gates)
        checks.append(claims_advisory)
        passed = all(check.passed for check in gates)
        verdict = ReplayVerdict.STABLE if passed else ReplayVerdict.BRITTLE
        explanation = (
            "The answer stayed stable while evidential meaning was preserved."
            if passed
            else _failure_explanation(gates, "Invariance contract failed")
        )

    elif case.kind == ReplayKind.DISTRACTOR:
        distractor_ids = {
            document.id for document in case.evidence if document.role == "distractor"
        }
        distractor_cited = bool(set(replay.citations) & distractor_ids)
        gates = [
            CheckResult(
                name="normalized verdict unchanged",
                passed=verdict_same,
                detail=observed_transition(baseline, replay),
            ),
            CheckResult(
                name="all citations resolve",
                passed=citations_ok,
                detail=(
                    "all citation IDs exist in the replay packet"
                    if citations_ok
                    else f"missing citation IDs: {', '.join(missing)}"
                ),
            ),
            CheckResult(
                name="distractor is not load-bearing",
                passed=not distractor_cited,
                detail=(
                    "distractor was ignored"
                    if not distractor_cited
                    else "target cited the declared distractor as evidence"
                ),
            ),
        ]
        checks.extend(gates)
        checks.append(claims_advisory)
        passed = all(check.passed for check in gates)
        verdict = ReplayVerdict.STABLE if passed else ReplayVerdict.BRITTLE
        explanation = (
            "The answer ignored non-dispositive evidence and remained stable."
            if passed
            else _failure_explanation(gates, "Distractor invariance contract failed")
        )

    elif case.kind == ReplayKind.SUPPORT_REMOVED:
        decisive_support_ids = {
            document.id
            for document in fixture.evidence.baseline
            if document.decisive and document.supports_claim
        }
        current_evidence_ids = {document.id for document in case.evidence}
        removed_evidence_ids = set(case.removed_evidence_ids)
        decisive_support_removed = decisive_support_ids.issubset(removed_evidence_ids) and not (
            decisive_support_ids & current_evidence_ids
        )
        removed_citations = sorted(set(replay.citations) & removed_evidence_ids)
        canonical_claim_forms = normalized_claims(baseline) | {normalize_text(fixture.claim)}
        unsupported_affirmative_claims = [
            claim
            for claim in replay.material_claims
            if normalize_text(claim) in canonical_claim_forms
        ]
        confidence_drop = None
        if baseline.confidence is not None and replay.confidence is not None:
            confidence_drop = baseline.confidence - replay.confidence
        disposition_changed_safely = (
            replay.verdict != baseline.verdict
            and replay.verdict != TargetVerdict.SUPPORTED
            and replay.verdict in fixture.output_contract.allowed_verdicts
        )
        sufficiency_indicates_evidence_loss = replay.evidence_sufficiency in {
            "insufficient",
            "partial",
        }
        gates = [
            CheckResult(
                name="decisive supporting evidence was removed",
                passed=decisive_support_removed,
                detail=(
                    "every decisive supporting document is absent and declared removed"
                    if decisive_support_removed
                    else "the support-removal packet did not remove every decisive support document"
                ),
            ),
            CheckResult(
                name="no declared support survives",
                passed=not any(document.supports_claim for document in case.evidence),
                detail="support-removed packet contains no declared claim support",
            ),
            CheckResult(
                name="affirmative conclusion does not persist unsupported",
                passed=disposition_changed_safely,
                detail=(
                    "target weakened or abstained after support removal"
                    if disposition_changed_safely
                    else "target preserved or replaced the conclusion without surviving support"
                ),
            ),
            CheckResult(
                name="evidence sufficiency responds to support removal",
                passed=sufficiency_indicates_evidence_loss,
                detail=f"evidence_sufficiency={replay.evidence_sufficiency.value}",
            ),
            CheckResult(
                name="no unsupported affirmative canonical claim",
                passed=not unsupported_affirmative_claims,
                detail=(
                    "no baseline or canonical affirmative material claim persists"
                    if not unsupported_affirmative_claims
                    else "unsupported affirmative material claims persist: "
                    + "; ".join(unsupported_affirmative_claims)
                ),
            ),
            CheckResult(
                name="citations resolve in reduced packet",
                passed=citations_ok,
                detail=(
                    "all remaining citations resolve"
                    if citations_ok
                    else f"citations point to removed evidence: {', '.join(missing)}"
                ),
            ),
            CheckResult(
                name="removed evidence is not cited",
                passed=not removed_citations,
                detail=(
                    "no removed evidence ID is cited"
                    if not removed_citations
                    else f"removed evidence IDs cited: {', '.join(removed_citations)}"
                ),
            ),
        ]
        checks.extend(gates)
        if confidence_drop is not None:
            checks.append(
                CheckResult(
                    name="confidence delta",
                    passed=confidence_drop >= fixture.assertions.minimum_confidence_drop,
                    gating=False,
                    detail=(
                        f"confidence changed by {confidence_drop:+.2f}; configured reference "
                        f"{fixture.assertions.minimum_confidence_drop:.2f}; diagnostic only "
                        "because the verdict class changed"
                    ),
                )
            )
        passed = all(check.passed for check in gates)
        verdict = ReplayVerdict.APPROPRIATELY_CHANGED if passed else ReplayVerdict.BRITTLE
        explanation = (
            "The target weakened appropriately after decisive support disappeared."
            if passed
            else _failure_explanation(gates, "Sensitivity contract failed")
        )

    elif case.kind == ReplayKind.NO_EVIDENCE:
        gates = [
            CheckResult(
                name="evidence packet is empty",
                passed=not case.evidence,
                detail="no evidence documents were supplied",
            ),
            CheckResult(
                name="target abstains",
                passed=replay.verdict == TargetVerdict.INSUFFICIENT_EVIDENCE,
                detail=(
                    "target abstained"
                    if replay.verdict == TargetVerdict.INSUFFICIENT_EVIDENCE
                    else f"target failed to abstain; observed verdict={replay.verdict.value}"
                ),
            ),
            CheckResult(
                name="target declares insufficiency",
                passed=replay.evidence_sufficiency == "insufficient",
                detail=f"evidence_sufficiency={replay.evidence_sufficiency.value}",
            ),
            CheckResult(
                name="no unsupported material claims",
                passed=not replay.material_claims,
                detail=f"material_claim_count={len(replay.material_claims)}",
            ),
            CheckResult(
                name="no orphan citations",
                passed=not replay.citations,
                detail=f"citation_count={len(replay.citations)}",
            ),
        ]
        checks.extend(gates)
        passed = all(check.passed for check in gates)
        verdict = ReplayVerdict.APPROPRIATELY_CHANGED if passed else ReplayVerdict.BRITTLE
        explanation = (
            "The target abstained when no usable evidence remained."
            if passed
            else _failure_explanation(gates, "No-evidence sensitivity contract failed")
        )
    else:  # pragma: no cover - exhaustive enum guard
        raise ValueError(f"unsupported replay kind: {case.kind}")

    if semantic:
        mapped = sum(mapping.supported for mapping in semantic.citation_mappings)
        checks.append(
            CheckResult(
                name="GPT-5.6 packet-support assessment",
                passed=semantic.citations_supported_by_packet and not semantic.unsupported_claims,
                gating=False,
                source="model_assisted",
                detail=(
                    semantic.explanation + f" Citation mappings supported: {mapped}/"
                    f"{len(semantic.citation_mappings)}."
                    + (
                        f" Unsupported claims: {semantic.unsupported_claims}"
                        if semantic.unsupported_claims
                        else ""
                    )
                ),
            )
        )

    return ReplayEvaluation(
        kind=case.kind,
        label=case.label,
        evidence_state=case.evidence_state,
        expected_transition=case.expected_transition,
        observed_transition=observed_transition(baseline, replay),
        row_result=RowResult.PASS if passed else RowResult.FAIL,
        verdict=verdict,
        target_response=replay,
        evidence=case.evidence,
        added_evidence_ids=case.added_evidence_ids,
        removed_evidence_ids=case.removed_evidence_ids,
        comparison=comparison,
        checks=checks,
        explanation=explanation,
    )


def execution_error_evaluation(case: ReplayCase, message: str) -> ReplayEvaluation:
    return ReplayEvaluation(
        kind=case.kind,
        label=case.label,
        evidence_state=case.evidence_state,
        expected_transition=case.expected_transition,
        observed_transition="target execution failed",
        row_result=RowResult.ERROR,
        verdict=ReplayVerdict.EXECUTION_ERROR,
        target_response=None,
        evidence=case.evidence,
        added_evidence_ids=case.added_evidence_ids,
        removed_evidence_ids=case.removed_evidence_ids,
        comparison=ComparisonDetails(
            answer="unavailable",
            claims="unavailable",
            citations="unavailable",
            surviving_support="not evaluated",
        ),
        checks=[
            CheckResult(
                name="target execution",
                passed=False,
                detail=message,
            )
        ],
        explanation=message,
    )


def invalid_test_evaluation(
    case: ReplayCase,
    message: str,
    response: TargetResponse | None = None,
) -> ReplayEvaluation:
    return ReplayEvaluation(
        kind=case.kind,
        label=case.label,
        evidence_state=case.evidence_state,
        expected_transition=case.expected_transition,
        observed_transition="comparison not valid",
        row_result=RowResult.INVALID,
        verdict=ReplayVerdict.INVALID_TEST,
        target_response=response,
        evidence=case.evidence,
        added_evidence_ids=case.added_evidence_ids,
        removed_evidence_ids=case.removed_evidence_ids,
        comparison=ComparisonDetails(
            answer="not compared",
            claims="not compared",
            citations="not compared",
            surviving_support="not evaluated",
        ),
        checks=[
            CheckResult(
                name="valid metamorphic baseline",
                passed=False,
                detail=message,
            )
        ],
        explanation=message,
    )
