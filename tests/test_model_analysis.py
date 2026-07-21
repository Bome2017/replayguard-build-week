from types import SimpleNamespace

import openai

from replayguard.models import (
    AnalysisMode,
    CitationMapping,
    ReplayKind,
    SemanticAssessment,
    SemanticAssessmentBatch,
)
from replayguard.runner import run_fixture


class FakeUsage:
    def model_dump(self, mode="json"):
        return {"input_tokens": 500, "output_tokens": 200, "total_tokens": 700}


class FakeResponses:
    def __init__(self, capture, *, fail_first_schema=False):
        self.capture = capture
        self.fail_first_schema = fail_first_schema
        self.calls = 0

    def parse(self, **kwargs):
        self.calls += 1
        self.capture.update(kwargs)
        if self.fail_first_schema and self.calls == 1:
            return SimpleNamespace(output_parsed=None)
        assessments = [
            SemanticAssessment(
                replay=replay,
                evidence_contract_valid=True,
                baseline_normalized_claims=["employees receive transit reimbursement"],
                replay_normalized_claims=["employees receive transit reimbursement"],
                claims_materially_equivalent=replay
                in {ReplayKind.EQUIVALENT, ReplayKind.DISTRACTOR},
                answer_relation=(
                    "equivalent"
                    if replay in {ReplayKind.EQUIVALENT, ReplayKind.DISTRACTOR}
                    else "weakened"
                ),
                citations_supported_by_packet=True,
                citation_mappings=[
                    CitationMapping(
                        citation_id="transit-policy",
                        evidence_id="transit-policy",
                        supported=True,
                        explanation="The cited document supports the normalized claim.",
                    )
                ],
                unsupported_claims=[],
                explanation="Structured semantic assessment completed.",
                confidence=0.96,
            )
            for replay in (
                ReplayKind.EQUIVALENT,
                ReplayKind.DISTRACTOR,
                ReplayKind.SUPPORT_REMOVED,
                ReplayKind.NO_EVIDENCE,
            )
        ]
        return SimpleNamespace(
            output_parsed=SemanticAssessmentBatch(assessments=assessments),
            id="synthetic-response-id",
            model="gpt-5.6-sol",
            usage=FakeUsage(),
        )


def test_gpt56_path_uses_responses_parse_and_records_metadata(clean_fixture_path, monkeypatch):
    capture = {}
    fake_client = SimpleNamespace(responses=FakeResponses(capture))
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")
    monkeypatch.setattr(openai, "OpenAI", lambda: fake_client)

    result = run_fixture(clean_fixture_path, analysis_mode=AnalysisMode.MODEL)

    assert result.summary.overall_pass is True
    assert capture["model"] == "gpt-5.6"
    assert capture["reasoning"] == {"effort": "low"}
    assert capture["store"] is False
    assert capture["text_format"] is SemanticAssessmentBatch
    assert result.metadata.model.used is True
    assert result.metadata.model.response_id == "synthetic-response-id"
    assert result.metadata.model.model_returned == "gpt-5.6-sol"
    assert result.metadata.model.usage["total_tokens"] == 700
    assert result.metadata.model.structured_output_attempts == 1
    assert any(
        check.source == "model_assisted"
        for evaluation in result.evaluations[1:]
        for check in evaluation.checks
    )


def test_gpt56_retries_one_unparsed_structured_output(clean_fixture_path, monkeypatch):
    capture = {}
    responses = FakeResponses(capture, fail_first_schema=True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")
    monkeypatch.setattr(openai, "OpenAI", lambda: SimpleNamespace(responses=responses))

    result = run_fixture(clean_fixture_path, analysis_mode=AnalysisMode.MODEL)

    assert result.summary.overall_pass is True
    assert responses.calls == 2
    assert result.metadata.model.structured_output_attempts == 2
