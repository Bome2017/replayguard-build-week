"""Typed product contracts shared by fixtures, adapters, verdicts, and reports."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class StrictModel(BaseModel):
    """Reject undeclared fields so CI fixtures fail closed."""

    model_config = ConfigDict(extra="forbid")


class ReplayKind(StrEnum):
    BASELINE = "baseline"
    EQUIVALENT = "equivalent"
    DISTRACTOR = "distractor"
    SUPPORT_REMOVED = "support_removed"
    NO_EVIDENCE = "no_evidence"


class TargetVerdict(StrEnum):
    SUPPORTED = "supported"
    REFUTED = "refuted"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    MIXED = "mixed"


class EvidenceSufficiency(StrEnum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class ReplayVerdict(StrEnum):
    BASELINE = "baseline"
    STABLE = "stable"
    APPROPRIATELY_CHANGED = "appropriately_changed"
    BRITTLE = "brittle"
    INVALID_TEST = "invalid_test"
    EXECUTION_ERROR = "execution_error"


class RowResult(StrEnum):
    BASELINE = "baseline"
    PASS = "pass"  # noqa: S105 - result label, not a password
    FAIL = "fail"
    INVALID = "invalid"
    ERROR = "error"


class AnalysisMode(StrEnum):
    AUTO = "auto"
    MODEL = "model"
    DETERMINISTIC = "deterministic"


class EvidenceDocument(StrictModel):
    id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    text: str = Field(min_length=1)
    role: Literal["support", "context", "distractor"] = "context"
    decisive: bool = False
    supports_claim: bool = False
    equivalent_to: str | None = None

    @model_validator(mode="after")
    def check_role_contract(self) -> EvidenceDocument:
        if self.decisive and not self.supports_claim:
            raise ValueError("decisive evidence must set supports_claim=true")
        if self.role == "distractor" and (self.decisive or self.supports_claim):
            raise ValueError("distractor evidence cannot be decisive or claim-supporting")
        if self.equivalent_to and self.role != "support":
            raise ValueError("equivalent evidence must use role=support")
        return self


class EvidenceConfig(StrictModel):
    baseline: list[EvidenceDocument] = Field(min_length=1)
    equivalent: list[EvidenceDocument] = Field(min_length=1)
    distractor: list[EvidenceDocument] = Field(min_length=1)


class PerturbationConfig(StrictModel):
    equivalent: bool = True
    distractor: bool = True
    support_removed: bool = True
    support_removed_retain_ids: list[str] = Field(min_length=1)
    no_evidence: bool = True

    @model_validator(mode="after")
    def require_mvp_contracts(self) -> PerturbationConfig:
        if not all((self.equivalent, self.distractor, self.support_removed, self.no_evidence)):
            raise ValueError("ReplayGuard MVP fixtures must enable all four replay contracts")
        return self


class TargetConfig(StrictModel):
    adapter: Literal["sample", "http"] = "sample"
    behavior: Literal["compliant", "distractor_flip", "sticky_claim", "brittle_all"] = "compliant"
    url: HttpUrl | None = None
    api_key_env: str | None = None
    timeout_seconds: float = Field(default=30, gt=0, le=300)

    @model_validator(mode="after")
    def require_http_url(self) -> TargetConfig:
        if self.adapter == "http" and self.url is None:
            raise ValueError("HTTP target adapter requires target.url")
        return self


class OutputContract(StrictModel):
    required_fields: list[
        Literal[
            "verdict",
            "answer",
            "material_claims",
            "citations",
            "confidence",
            "evidence_sufficiency",
        ]
    ] = Field(min_length=5)
    allowed_verdicts: list[TargetVerdict] = Field(
        default_factory=lambda: list(TargetVerdict), min_length=1
    )


class AssertionRules(StrictModel):
    expected_baseline_verdict: TargetVerdict = TargetVerdict.SUPPORTED
    minimum_confidence_drop: float = Field(default=0.2, ge=0, le=1)
    require_resolved_citations: bool = True
    require_no_claims_without_evidence: bool = True


class Fixture(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    title: str = Field(min_length=1)
    question: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    evidence: EvidenceConfig
    perturbations: PerturbationConfig = Field(default_factory=PerturbationConfig)
    target: TargetConfig = Field(default_factory=TargetConfig)
    output_contract: OutputContract
    assertions: AssertionRules = Field(default_factory=AssertionRules)

    @model_validator(mode="after")
    def validate_evidence_graph(self) -> Fixture:
        all_documents = self.evidence.baseline + self.evidence.equivalent + self.evidence.distractor
        ids = [document.id for document in all_documents]
        if len(ids) != len(set(ids)):
            raise ValueError("evidence document IDs must be unique across the fixture")

        decisive_ids = {
            document.id
            for document in self.evidence.baseline
            if document.decisive and document.supports_claim
        }
        if not decisive_ids:
            raise ValueError("baseline evidence needs at least one decisive supporting document")

        baseline_by_id = {document.id: document for document in self.evidence.baseline}
        retained_ids = set(self.perturbations.support_removed_retain_ids)
        unknown_retained = retained_ids - set(baseline_by_id)
        if unknown_retained:
            raise ValueError(
                "support_removed_retain_ids contains unknown baseline IDs: "
                f"{sorted(unknown_retained)}"
            )
        invalid_retained = sorted(
            document_id
            for document_id in retained_ids
            if baseline_by_id[document_id].decisive or baseline_by_id[document_id].supports_claim
        )
        if invalid_retained:
            raise ValueError(
                "support_removed_retain_ids cannot retain declared claim support: "
                f"{invalid_retained}"
            )

        replaced_ids = {document.equivalent_to for document in self.evidence.equivalent}
        if None in replaced_ids or not decisive_ids.issubset(replaced_ids):
            raise ValueError("equivalent evidence must replace every decisive baseline document")
        if not all(document.role == "distractor" for document in self.evidence.distractor):
            raise ValueError("every distractor document must use role=distractor")

        required = set(self.output_contract.required_fields)
        minimum = {
            "verdict",
            "answer",
            "material_claims",
            "citations",
            "evidence_sufficiency",
        }
        if not minimum.issubset(required):
            missing = sorted(minimum - required)
            raise ValueError(f"output contract is missing required fields: {missing}")
        return self


class TargetResponse(StrictModel):
    verdict: TargetVerdict
    answer: str = Field(min_length=1)
    material_claims: list[str]
    citations: list[str]
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_sufficiency: EvidenceSufficiency = EvidenceSufficiency.UNKNOWN


class ReplayCase(StrictModel):
    kind: ReplayKind
    label: str
    evidence_state: str
    expected_transition: str
    evidence: list[EvidenceDocument]
    added_evidence_ids: list[str] = Field(default_factory=list)
    removed_evidence_ids: list[str] = Field(default_factory=list)


class CitationMapping(StrictModel):
    citation_id: str
    evidence_id: str | None = None
    supported: bool
    explanation: str


class SemanticAssessment(StrictModel):
    replay: ReplayKind
    evidence_contract_valid: bool
    baseline_normalized_claims: list[str]
    replay_normalized_claims: list[str]
    claims_materially_equivalent: bool
    answer_relation: Literal["equivalent", "weakened", "reversed", "unrelated"]
    citations_supported_by_packet: bool
    citation_mappings: list[CitationMapping]
    unsupported_claims: list[str]
    explanation: str
    confidence: float = Field(ge=0, le=1)


class SemanticAssessmentBatch(StrictModel):
    assessments: list[SemanticAssessment] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def require_each_replay(self) -> SemanticAssessmentBatch:
        expected = {
            ReplayKind.EQUIVALENT,
            ReplayKind.DISTRACTOR,
            ReplayKind.SUPPORT_REMOVED,
            ReplayKind.NO_EVIDENCE,
        }
        actual = {assessment.replay for assessment in self.assessments}
        if actual != expected:
            raise ValueError(f"semantic batch must contain exactly {sorted(expected)}")
        return self


class ModelRunMetadata(StrictModel):
    requested: bool = False
    used: bool = False
    provider: str = "openai"
    model_requested: str | None = None
    model_returned: str | None = None
    reasoning_effort: str | None = None
    response_id: str | None = None
    prompt_version: str | None = None
    prompt_sha256: str | None = None
    usage: dict[str, object] | None = None
    structured_output_attempts: int = 0
    warning: str | None = None


class CheckResult(StrictModel):
    name: str
    passed: bool
    gating: bool = True
    source: Literal["deterministic", "model_assisted"] = "deterministic"
    detail: str


class ComparisonDetails(StrictModel):
    answer: str
    claims: str
    citations: str
    surviving_support: str


class ReplayEvaluation(StrictModel):
    kind: ReplayKind
    label: str
    evidence_state: str
    expected_transition: str
    observed_transition: str
    row_result: RowResult
    verdict: ReplayVerdict
    target_response: TargetResponse | None
    evidence: list[EvidenceDocument]
    added_evidence_ids: list[str] = Field(default_factory=list)
    removed_evidence_ids: list[str] = Field(default_factory=list)
    comparison: ComparisonDetails
    checks: list[CheckResult]
    explanation: str


class RunSummary(StrictModel):
    passed: int = 0
    brittle: int = 0
    invalid: int = 0
    errors: int = 0
    required_replays: int = 4
    overall_pass: bool = False


class RunMetadata(StrictModel):
    run_id: str
    created_at: datetime
    replayguard_version: str
    fixture_path: str
    fixture_sha256: str
    target_adapter: str
    target_endpoint: str | None = None
    analysis_mode_requested: AnalysisMode
    analysis_mode_effective: AnalysisMode
    model: ModelRunMetadata


class RunResult(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    fixture_id: str
    title: str
    question: str
    claim: str
    metadata: RunMetadata
    evaluations: list[ReplayEvaluation] = Field(min_length=5, max_length=5)
    summary: RunSummary
    report_directory: str | None = None

    @property
    def exit_code(self) -> int:
        if self.summary.overall_pass:
            return 0
        if self.summary.errors or self.summary.invalid:
            return 2
        return 1


def fixture_display_path(path: Path) -> str:
    """Return a stable path without requiring the file to be inside the current directory."""

    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path.resolve())
