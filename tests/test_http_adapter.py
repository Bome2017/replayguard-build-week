import json

import pytest

import replayguard.adapters as adapters_module
from replayguard.adapters import HttpTargetAdapter, TargetExecutionError
from replayguard.fixtures import load_fixture
from replayguard.models import EvidenceSufficiency, TargetVerdict
from replayguard.perturbations import build_replay_cases


def test_http_adapter_sends_explicit_evidence_and_validates_output(clean_fixture_path, monkeypatch):
    captured = {}
    fixture, _ = load_fixture(clean_fixture_path)

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps(
                {
                    "verdict": "supported",
                    "answer": "Employees may receive up to $100 per month.",
                    "material_claims": [
                        "Employees may receive up to $100 per month for "
                        "public-transit commuting costs."
                    ],
                    "citations": ["transit-policy"],
                    "confidence": 0.9,
                    "evidence_sufficiency": "sufficient",
                }
            ).encode()

    def fake_urlopen(request, timeout):
        captured.update(json.loads(request.data))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(adapters_module, "urlopen", fake_urlopen)
    baseline = build_replay_cases(fixture)[0]
    adapter = HttpTargetAdapter(
        url="http://target.test/answer",
        timeout_seconds=2,
    )
    response = adapter.answer(fixture, baseline)

    assert response.verdict == TargetVerdict.SUPPORTED
    assert response.evidence_sufficiency == EvidenceSufficiency.SUFFICIENT
    assert captured["question"] == fixture.question
    assert captured["claim_under_test"] == fixture.claim
    assert captured["evidence"][0]["id"] == "transit-policy"
    assert "output_schema" in captured
    assert captured["timeout"] == 2


def test_http_adapter_fails_closed_when_verdict_is_missing(clean_fixture_path, monkeypatch):
    fixture, _ = load_fixture(clean_fixture_path)

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps(
                {
                    "answer": "The allowance is available.",
                    "material_claims": ["Workers qualify for the transit benefit."],
                    "citations": ["transit-policy"],
                    "confidence": 0.9,
                    "evidence_sufficiency": "sufficient",
                }
            ).encode()

    monkeypatch.setattr(adapters_module, "urlopen", lambda request, timeout: FakeResponse())
    baseline = build_replay_cases(fixture)[0]
    adapter = HttpTargetAdapter(url="http://target.test/answer")

    with pytest.raises(TargetExecutionError, match="verdict"):
        adapter.answer(fixture, baseline)


def test_http_adapter_rejects_non_http_url():
    with pytest.raises(TargetExecutionError, match="must use http or https"):
        HttpTargetAdapter(url="file:///tmp/not-an-http-target")
