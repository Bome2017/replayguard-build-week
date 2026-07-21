from replayguard.adapters import SampleTargetAdapter
from replayguard.fixtures import load_fixture
from replayguard.models import (
    AnalysisMode,
    EvidenceSufficiency,
    ReplayKind,
    ReplayVerdict,
    RowResult,
    TargetResponse,
    TargetVerdict,
)
from replayguard.perturbations import build_replay_cases
from replayguard.runner import run_fixture
from replayguard.verdicts import evaluate_baseline, evaluate_replay


def test_compliant_target_passes_every_contract(clean_fixture_path):
    result = run_fixture(clean_fixture_path, analysis_mode=AnalysisMode.DETERMINISTIC)

    assert result.summary.overall_pass is True
    assert result.summary.passed == 4
    assert result.summary.brittle == 0
    assert result.exit_code == 0
    assert [evaluation.verdict for evaluation in result.evaluations[1:]] == [
        ReplayVerdict.STABLE,
        ReplayVerdict.STABLE,
        ReplayVerdict.APPROPRIATELY_CHANGED,
        ReplayVerdict.APPROPRIATELY_CHANGED,
    ]


def test_demo_target_surfaces_three_specific_brittle_transitions(brittle_fixture_path):
    result = run_fixture(brittle_fixture_path, analysis_mode=AnalysisMode.DETERMINISTIC)
    rows = {evaluation.kind: evaluation for evaluation in result.evaluations}

    assert result.summary.overall_pass is False
    assert result.summary.passed == 1
    assert result.summary.brittle == 3
    assert result.exit_code == 1
    assert rows[ReplayKind.EQUIVALENT].row_result == RowResult.PASS
    assert rows[ReplayKind.DISTRACTOR].verdict == ReplayVerdict.BRITTLE
    assert "distractor" in rows[ReplayKind.DISTRACTOR].explanation.lower()
    assert rows[ReplayKind.SUPPORT_REMOVED].verdict == ReplayVerdict.BRITTLE
    assert "without surviving support" in rows[ReplayKind.SUPPORT_REMOVED].explanation
    assert rows[ReplayKind.NO_EVIDENCE].verdict == ReplayVerdict.BRITTLE
    assert "failed to abstain" in rows[ReplayKind.NO_EVIDENCE].explanation


def test_required_model_mode_fails_closed_without_api_key(clean_fixture_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = run_fixture(clean_fixture_path, analysis_mode=AnalysisMode.MODEL)

    assert result.summary.errors == 4
    assert result.exit_code == 2
    assert result.metadata.model.requested is True
    assert result.metadata.model.used is False
    assert "OPENAI_API_KEY" in (result.metadata.model.warning or "")


def test_paraphrased_baseline_is_valid_when_disposition_and_citations_are_grounded(
    clean_fixture_path,
):
    fixture, _ = load_fixture(clean_fixture_path)
    baseline_case = build_replay_cases(fixture)[0]
    response = TargetResponse(
        verdict=TargetVerdict.SUPPORTED,
        answer="Qualifying staff can be reimbursed monthly for public transportation.",
        material_claims=["The policy offers a monthly transit reimbursement benefit."],
        citations=["transit-policy"],
        confidence=0.91,
        evidence_sufficiency=EvidenceSufficiency.SUFFICIENT,
    )

    evaluation = evaluate_baseline(fixture, baseline_case, response)

    assert fixture.claim not in response.material_claims
    assert evaluation.row_result == RowResult.BASELINE
    assert evaluation.verdict == ReplayVerdict.BASELINE


def test_unrelated_claim_with_unresolved_citation_fails_baseline_closed(clean_fixture_path):
    fixture, _ = load_fixture(clean_fixture_path)
    baseline_case = build_replay_cases(fixture)[0]
    response = TargetResponse(
        verdict=TargetVerdict.SUPPORTED,
        answer="Friday parking reservations are allowed.",
        material_claims=["Staff can book parking on Fridays."],
        citations=["parking-policy"],
        confidence=0.91,
        evidence_sufficiency=EvidenceSufficiency.SUFFICIENT,
    )

    evaluation = evaluate_baseline(fixture, baseline_case, response)

    assert evaluation.row_result == RowResult.INVALID
    assert evaluation.verdict == ReplayVerdict.INVALID_TEST
    assert any(
        check.name == "baseline citations resolve" and not check.passed
        for check in evaluation.checks
    )


def test_equivalent_replay_allows_paraphrased_human_readable_claims(clean_fixture_path):
    fixture, _ = load_fixture(clean_fixture_path)
    cases = build_replay_cases(fixture)
    baseline_case = cases[0]
    equivalent_case = next(case for case in cases if case.kind == ReplayKind.EQUIVALENT)
    baseline = TargetResponse(
        verdict=TargetVerdict.SUPPORTED,
        answer="Qualifying staff can recover monthly public-transport costs.",
        material_claims=["A monthly commuter reimbursement is available."],
        citations=["transit-policy"],
        confidence=0.91,
        evidence_sufficiency=EvidenceSufficiency.SUFFICIENT,
    )
    replay = TargetResponse(
        verdict=TargetVerdict.SUPPORTED,
        answer="The equivalent policy text still authorizes a monthly transit benefit.",
        material_claims=["Public-transit expenses qualify for recurring reimbursement."],
        citations=["transit-policy-plain-language"],
        confidence=0.90,
        evidence_sufficiency=EvidenceSufficiency.SUFFICIENT,
    )

    assert evaluate_baseline(fixture, baseline_case, baseline).row_result == RowResult.BASELINE
    evaluation = evaluate_replay(
        fixture,
        equivalent_case,
        baseline,
        replay,
        structural_issues=[],
        semantic=None,
    )

    assert baseline.material_claims != replay.material_claims
    assert evaluation.row_result == RowResult.PASS
    assert evaluation.verdict == ReplayVerdict.STABLE
    prose_check = next(
        check for check in evaluation.checks if check.name == "material claim prose comparison"
    )
    assert prose_check.passed is False
    assert prose_check.gating is False


def test_support_removed_accepts_a_supported_reversal(clean_fixture_path):
    fixture, _ = load_fixture(clean_fixture_path)
    cases = build_replay_cases(fixture)
    baseline = SampleTargetAdapter("compliant").answer(fixture, cases[0])
    support_removed = next(case for case in cases if case.kind == ReplayKind.SUPPORT_REMOVED)
    replay = TargetResponse(
        verdict=TargetVerdict.REFUTED,
        answer="The surviving evidence contradicts the original conclusion.",
        material_claims=["The original conclusion is false."],
        citations=["reimbursement-process"],
        confidence=0.50,
        evidence_sufficiency=EvidenceSufficiency.PARTIAL,
    )

    evaluation = evaluate_replay(
        fixture,
        support_removed,
        baseline,
        replay,
        structural_issues=[],
        semantic=None,
    )

    assert evaluation.verdict == ReplayVerdict.APPROPRIATELY_CHANGED
    assert evaluation.row_result == RowResult.PASS
