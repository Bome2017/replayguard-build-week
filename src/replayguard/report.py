"""Machine-readable JSON and polished single-file HTML reporting."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, StrictUndefined, select_autoescape

from replayguard.models import RunResult


def _safe_report_directory(path: Path) -> str:
    """Record a useful report path without leaking an unrelated absolute workspace path."""

    resolved = path.resolve()
    try:
        return str(resolved.relative_to(Path.cwd().resolve()))
    except ValueError:
        return path.name


def write_report(result: RunResult, output_directory: Path) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    result.report_directory = _safe_report_directory(output_directory)

    json_path = output_directory / "result.json"
    json_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    template_source = (
        files("replayguard").joinpath("templates/report.html.j2").read_text(encoding="utf-8")
    )
    environment = Environment(
        autoescape=select_autoescape(default=True),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = environment.from_string(template_source)
    html = template.render(result=result.model_dump(mode="json"))
    html_path = output_directory / "index.html"
    html_path.write_text(html, encoding="utf-8")
    return html_path, json_path
