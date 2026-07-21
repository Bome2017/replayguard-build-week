"""Target-system adapters for ReplayGuard's explicit evidence-in / structure-out contract."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from pydantic import ValidationError

from replayguard.models import (
    EvidenceSufficiency,
    Fixture,
    ReplayCase,
    ReplayKind,
    TargetResponse,
    TargetVerdict,
)


class TargetExecutionError(RuntimeError):
    """A target did not execute or did not honor the structured output contract."""


class TargetAdapter(Protocol):
    name: str
    endpoint: str | None

    def answer(self, fixture: Fixture, case: ReplayCase) -> TargetResponse: ...


@dataclass(slots=True)
class SampleTargetAdapter:
    """Reliable demo target with deliberately selectable failure modes."""

    behavior: str
    name: str = "sample"
    endpoint: str | None = None

    def answer(self, fixture: Fixture, case: ReplayCase) -> TargetResponse:
        has_declared_support = any(document.supports_claim for document in case.evidence)
        supporting_ids = [document.id for document in case.evidence if document.supports_claim]
        distractor_ids = [
            document.id for document in case.evidence if document.role == "distractor"
        ]

        flip_on_distractor = self.behavior in {"distractor_flip", "brittle_all"}
        persist_without_support = self.behavior in {"sticky_claim", "brittle_all"}

        if case.kind == ReplayKind.DISTRACTOR and flip_on_distractor:
            citation = distractor_ids[:1]
            return TargetResponse(
                verdict=TargetVerdict.REFUTED,
                answer=(
                    "The added operational note changes the conclusion, so the stated claim "
                    "should be treated as false."
                ),
                material_claims=[f"The following claim is false: {fixture.claim}"],
                citations=citation,
                confidence=0.88,
                evidence_sufficiency=EvidenceSufficiency.SUFFICIENT,
            )

        if not has_declared_support and persist_without_support:
            original_decisive_ids = [
                document.id for document in fixture.evidence.baseline if document.decisive
            ]
            return TargetResponse(
                verdict=TargetVerdict.SUPPORTED,
                answer=fixture.claim,
                material_claims=[fixture.claim],
                citations=original_decisive_ids[:1],
                confidence=0.92,
                evidence_sufficiency=EvidenceSufficiency.SUFFICIENT,
            )

        if has_declared_support:
            return TargetResponse(
                verdict=TargetVerdict.SUPPORTED,
                answer=fixture.claim,
                material_claims=[fixture.claim],
                citations=supporting_ids,
                confidence=0.94,
                evidence_sufficiency=EvidenceSufficiency.SUFFICIENT,
            )

        return TargetResponse(
            verdict=TargetVerdict.INSUFFICIENT_EVIDENCE,
            answer="The supplied evidence is insufficient to establish the claim.",
            material_claims=[],
            citations=[],
            confidence=0.12,
            evidence_sufficiency=EvidenceSufficiency.INSUFFICIENT,
        )


@dataclass(slots=True)
class HttpTargetAdapter:
    """ReplayGuard HTTP boundary: explicit evidence input, JSON-schema output."""

    url: str
    api_key_env: str | None = None
    timeout_seconds: float = 30
    name: str = "http"

    def __post_init__(self) -> None:
        parsed = urlsplit(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise TargetExecutionError("HTTP target URL must use http or https and include a host")

    @property
    def endpoint(self) -> str:
        return self.url

    def answer(self, fixture: Fixture, case: ReplayCase) -> TargetResponse:
        payload = {
            "question": fixture.question,
            "claim_under_test": fixture.claim,
            "evidence": [{"id": document.id, "text": document.text} for document in case.evidence],
            "output_schema": TargetResponse.model_json_schema(),
            "metadata": {"test_id": fixture.id, "replay": case.kind.value},
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key_env:
            token = os.getenv(self.api_key_env)
            if not token:
                raise TargetExecutionError(
                    f"target credential environment variable {self.api_key_env!r} is not set"
                )
            headers["Authorization"] = f"Bearer {token}"

        request = Request(  # noqa: S310 - __post_init__ restricts URLs to HTTP(S)
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise TargetExecutionError(f"target returned HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise TargetExecutionError(f"target request failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise TargetExecutionError(
                f"target timed out after {self.timeout_seconds:g} seconds"
            ) from exc

        try:
            return TargetResponse.model_validate_json(raw)
        except (ValidationError, ValueError) as exc:
            raise TargetExecutionError(f"target response violated output contract: {exc}") from exc


def build_target_adapter(fixture: Fixture, target_override: str | None = None) -> TargetAdapter:
    configured_timeout = fixture.target.timeout_seconds
    timeout_value = os.getenv("REPLAYGUARD_HTTP_TIMEOUT_SECONDS")
    if timeout_value:
        try:
            configured_timeout = float(timeout_value)
        except ValueError as exc:
            raise TargetExecutionError("REPLAYGUARD_HTTP_TIMEOUT_SECONDS must be a number") from exc
        if not 0 < configured_timeout <= 300:
            raise TargetExecutionError(
                "REPLAYGUARD_HTTP_TIMEOUT_SECONDS must be greater than 0 and at most 300"
            )
    if target_override:
        return HttpTargetAdapter(
            url=target_override,
            api_key_env=fixture.target.api_key_env,
            timeout_seconds=configured_timeout,
        )
    if fixture.target.adapter == "http":
        return HttpTargetAdapter(
            url=str(fixture.target.url),
            api_key_env=fixture.target.api_key_env,
            timeout_seconds=configured_timeout,
        )
    return SampleTargetAdapter(behavior=fixture.target.behavior)
