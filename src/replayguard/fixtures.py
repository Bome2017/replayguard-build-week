"""Fixture loading with fail-closed schema validation."""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml
from pydantic import ValidationError

from replayguard.models import Fixture


class FixtureError(ValueError):
    """Raised when a fixture cannot become a valid metamorphic test."""


def load_fixture(path: Path) -> tuple[Fixture, str]:
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        raise FixtureError(f"cannot read fixture {path}: {exc}") from exc

    try:
        payload = yaml.safe_load(raw_bytes)
    except yaml.YAMLError as exc:
        raise FixtureError(f"invalid YAML in {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise FixtureError(f"fixture {path} must contain a YAML object")

    try:
        fixture = Fixture.model_validate(payload)
    except ValidationError as exc:
        raise FixtureError(f"fixture schema validation failed:\n{exc}") from exc

    return fixture, hashlib.sha256(raw_bytes).hexdigest()
