from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def clean_fixture_path(project_root: Path) -> Path:
    return project_root / "fixtures" / "clean_policy.yaml"


@pytest.fixture
def brittle_fixture_path(project_root: Path) -> Path:
    return project_root / "fixtures" / "demo_brittle.yaml"
