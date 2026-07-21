"""ReplayGuard: metamorphic regression tests for evidence-grounded AI systems."""

__version__ = "0.1.0"

from replayguard.models import RunResult  # noqa: E402
from replayguard.runner import run_fixture  # noqa: E402

__all__ = ["RunResult", "run_fixture"]
