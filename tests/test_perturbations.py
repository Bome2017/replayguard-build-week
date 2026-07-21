from replayguard.fixtures import load_fixture
from replayguard.models import ReplayKind
from replayguard.perturbations import build_replay_cases, validate_replay_cases


def test_all_four_replays_obey_structural_contracts(clean_fixture_path):
    fixture, _ = load_fixture(clean_fixture_path)
    cases = build_replay_cases(fixture)
    by_kind = {case.kind: case for case in cases}

    assert [case.kind for case in cases] == [
        ReplayKind.BASELINE,
        ReplayKind.EQUIVALENT,
        ReplayKind.DISTRACTOR,
        ReplayKind.SUPPORT_REMOVED,
        ReplayKind.NO_EVIDENCE,
    ]
    assert {document.id for document in by_kind[ReplayKind.EQUIVALENT].evidence} == {
        "transit-policy-plain-language",
        "reimbursement-process",
    }
    assert {document.id for document in by_kind[ReplayKind.DISTRACTOR].evidence} == {
        "transit-policy",
        "reimbursement-process",
        "cafeteria-hours",
    }
    assert [document.id for document in by_kind[ReplayKind.SUPPORT_REMOVED].evidence] == [
        "reimbursement-process"
    ]
    assert fixture.perturbations.support_removed_retain_ids == ["reimbursement-process"]
    assert by_kind[ReplayKind.NO_EVIDENCE].evidence == []
    assert all(not issues for issues in validate_replay_cases(fixture, cases).values())
