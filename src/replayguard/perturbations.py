"""Deterministic construction and validation of the four MVP replay cases."""

from __future__ import annotations

from replayguard.models import Fixture, ReplayCase, ReplayKind


def build_replay_cases(fixture: Fixture) -> list[ReplayCase]:
    baseline = list(fixture.evidence.baseline)
    decisive_ids = {document.id for document in baseline if document.decisive}
    retained_ids = set(fixture.perturbations.support_removed_retain_ids)
    retained_context = [document for document in baseline if document.id in retained_ids]

    replacements_by_original = {
        document.equivalent_to: document for document in fixture.evidence.equivalent
    }
    equivalent = [
        replacements_by_original.get(document.id, document)
        if document.id in decisive_ids
        else document
        for document in baseline
    ]

    cases = [
        ReplayCase(
            kind=ReplayKind.BASELINE,
            label="Baseline",
            evidence_state="Supported",
            expected_transition="Establish baseline",
            evidence=baseline,
        ),
        ReplayCase(
            kind=ReplayKind.EQUIVALENT,
            label="Equivalent evidence",
            evidence_state="Meaning preserved",
            expected_transition="Remain stable",
            evidence=equivalent,
            added_evidence_ids=[document.id for document in fixture.evidence.equivalent],
            removed_evidence_ids=sorted(decisive_ids),
        ),
        ReplayCase(
            kind=ReplayKind.DISTRACTOR,
            label="Distractor added",
            evidence_state="Support plus noise",
            expected_transition="Remain stable and ignore distractor",
            evidence=baseline + list(fixture.evidence.distractor),
            added_evidence_ids=[document.id for document in fixture.evidence.distractor],
        ),
        ReplayCase(
            kind=ReplayKind.SUPPORT_REMOVED,
            label="Decisive support removed",
            evidence_state="Decisive evidence absent",
            expected_transition="Weaken, change, or abstain",
            evidence=retained_context,
            removed_evidence_ids=sorted(decisive_ids),
        ),
        ReplayCase(
            kind=ReplayKind.NO_EVIDENCE,
            label="No usable evidence",
            evidence_state="Empty packet",
            expected_transition="Abstain as insufficient evidence",
            evidence=[],
            removed_evidence_ids=[document.id for document in baseline],
        ),
    ]
    return cases


def validate_replay_cases(fixture: Fixture, cases: list[ReplayCase]) -> dict[ReplayKind, list[str]]:
    """Return deterministic contract defects by replay; an empty list means structurally valid."""

    issues: dict[ReplayKind, list[str]] = {case.kind: [] for case in cases}
    case_map = {case.kind: case for case in cases}
    baseline_ids = {document.id for document in case_map[ReplayKind.BASELINE].evidence}
    decisive_ids = {
        document.id
        for document in fixture.evidence.baseline
        if document.decisive and document.supports_claim
    }

    equivalent = case_map[ReplayKind.EQUIVALENT]
    equivalent_targets = {document.equivalent_to for document in equivalent.evidence}
    if not decisive_ids.issubset(equivalent_targets):
        issues[ReplayKind.EQUIVALENT].append(
            "not every decisive baseline document has an equivalent replacement"
        )
    if not any(document.supports_claim for document in equivalent.evidence):
        issues[ReplayKind.EQUIVALENT].append("equivalent packet lost all declared support")

    distractor = case_map[ReplayKind.DISTRACTOR]
    distractor_ids = {document.id for document in distractor.evidence}
    if not baseline_ids.issubset(distractor_ids):
        issues[ReplayKind.DISTRACTOR].append("distractor replay did not preserve baseline evidence")
    if any(
        document.role == "distractor" and (document.decisive or document.supports_claim)
        for document in distractor.evidence
    ):
        issues[ReplayKind.DISTRACTOR].append("a distractor was marked as claim-supporting")

    support_removed = case_map[ReplayKind.SUPPORT_REMOVED]
    expected_retained_ids = set(fixture.perturbations.support_removed_retain_ids)
    actual_retained_ids = {document.id for document in support_removed.evidence}
    if actual_retained_ids != expected_retained_ids:
        issues[ReplayKind.SUPPORT_REMOVED].append(
            "support-removed packet does not match its hand-authored retain-ID list"
        )
    if any(document.decisive or document.supports_claim for document in support_removed.evidence):
        issues[ReplayKind.SUPPORT_REMOVED].append(
            "support-removed packet retained declared claim support"
        )

    if case_map[ReplayKind.NO_EVIDENCE].evidence:
        issues[ReplayKind.NO_EVIDENCE].append("no-evidence packet is not empty")

    return issues
