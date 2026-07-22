#!/usr/bin/env python3
"""Offline, standard-library validation for the public ReplayGuard pilot package."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = "1.0"
ARMS = ("naive", "hardened")
DOMAINS = ("equip", "infosec", "leave", "proc", "records", "travel")
REPLICATES = (1, 2, 3)
STATES = ("baseline", "equivalent", "distractor", "support_removed", "no_evidence")
TRANSITIONS = STATES[1:]
RESULT_VALUES = {"pass", "fail"}
HEX_64 = re.compile(r"[0-9a-f]{64}")
HEX_40 = re.compile(r"[0-9a-f]{40}")
RUN_ID = re.compile(r"r([123])-(naive|hardened)-([a-z]+-[0-9]{2})")
FIXTURE_ID = re.compile(r"([a-z]+)-([0-9]{2})")
ZERO_HASH = "0" * 64

EVALUATED_COMMIT = "d0dc3637a14b06bf16d6dc930d700116f38f8175"
CORRECTION_COMMIT = "a3629ba547c3665aefe17729e90f11bf7c5f6673"
AUDIT_START_COMMIT = "920c01371be4f64ba963ff02c8302e45aed48ca1"
EVALUATED_EVALUATOR_SHA256 = "93c3c663c01e35a09d211dea79d92f5df1b7bdb9ea06adac62de3ecfda9b433c"
CORRECTED_EVALUATOR_SHA256 = "0fb7ea83355ca74d7c749c421601b33a2c2ff96fdfd0fb4030095ad9d85e11bf"
EXECUTION_PREFLIGHT_SHA256 = "579adb354dcac70f35e9abe128abfefd1688c1f38360161d2024259d4802e351"
ATTEMPT_LEDGER_SHA256 = "10aef25f06851072a0720ac469925a6b73ddc3dbf3b1f013b81d83f4d7cf0857"
FROZEN_ANALYSIS_SHA256 = "6dcac829b274c994333e5bd21dcd3495e0361ea38c8f1dc9bc506ad789a5bbde"
CORRECTION_TEST_SHA256 = "823b19dcd7a2103a639df89de5d09aab41ac62d415c35b4c153412282c39231f"
EVALUATED_SOURCE_TREE_SHA256 = "b9059503a2246d1630504a2df8458731042e7adecc040c1ac163c0bdb967edea"
EVALUATED_GIT_TREE_SHA1 = "431126e0fc09cef9633fdc054747f26afef9373b"
CURRENT_SOURCE_TREE_SHA256 = "3be157114b629d02699a9530dcdd18e506f987201df68eb512f79e7422990fb2"
EVALUATED_ADAPTER_SHA256 = "897e089fc529119c25fa83187df136427f68736c5e45eee2138dcae8b5a90b7d"
PUBLIC_ADAPTER_SHA256 = "502e49e7f3b230f7b65b6139363668ff84f85a5f717edbb6100f6a0ada90a36d"
FIXTURE_BANK_SHA256 = "713a1f89d652644d0409ccd546eab6528cc47b34cfecd6b875c4f3b2cc97fcb7"
EXECUTION_MATRIX_SHA256 = "514b4a39ff9229bf27ad684d8726658ceb61f27fea7410a9ab0d9fe14450f55d"
STUDY_COMMIT = "bf56bb34c4b1a1d1c301fbc8ff2d0be795a8d6b8"
STUDY_MANIFEST_SHA256 = "9ebd27eb516df7bf4e309d28b1fa759c2855a58ff2ac09db56182db80b584615"
PREANALYSIS_PLAN_SHA256 = "15b6873741d200e5a3348d3bdb3f4e691766f48dada794b6a0685a703ebfd25c"
STUDY_PROTOCOL_SHA256 = "a18bcb22d7b5492eac4340f7b6b3b7f81902c418601d694f85c826a83f8043be"
NAIVE_PROMPT_SHA256 = "5eb04983348f972384100514b1b06bede42f9d156aae59bd38282308dbaccbaf"
HARDENED_PROMPT_SHA256 = "8940835784c5dbdbb0e64129b6411d1cc3cd630f095ffcf56a83803ec6977b85"
TARGET_PARAMETERS_SHA256 = "30d15d97f6faa631f2dcbf027a52873b2eb1ff91c4b9475ef73142d32f74fa4d"
ANALYSIS_START = "2026-07-18T17:13:34.855247+00:00"
ANALYSIS_END = "2026-07-18T17:58:29.279673+00:00"
STUDY_COMMIT_TIME = "2026-07-18T09:46:25-07:00"
EXECUTION_PREFLIGHT_TIME = "2026-07-18T17:12:42.154119+00:00"
FIRST_CALL_ARTIFACT_TIME = "2026-07-18T10:13:21.967240-07:00"

EXACT_EQUIVALENT_DISAGREEMENTS = {
    "r1-hardened-leave-03",
    "r1-hardened-leave-04",
    "r1-naive-proc-04",
    "r2-hardened-leave-03",
    "r2-hardened-leave-04",
    "r2-naive-leave-05",
    "r2-naive-records-05",
    "r3-hardened-leave-03",
    "r3-hardened-leave-04",
    "r3-naive-proc-04",
}

EXACT_SUPPORT_REMOVAL_CORRECTIONS = {
    "r1-naive-travel-04",
    "r2-naive-leave-03",
    "r2-naive-leave-04",
    "r2-naive-travel-01",
    "r3-naive-leave-03",
}

PACKAGE_FILES = {
    "PILOT_VALIDATION.md": ("judge_summary", "text/markdown"),
    "scripts/validate_pilot_package.py": ("offline_validator", "text/x-python"),
    "tests/test_pilot_package.py": ("validator_test", "text/x-python"),
    "validation/pilot/CLAIM_EVIDENCE_MATRIX.md": (
        "claim_evidence_matrix",
        "text/markdown",
    ),
    "validation/pilot/METHODOLOGY.md": ("methodology", "text/markdown"),
    "validation/pilot/README.md": ("package_index", "text/markdown"),
    "validation/pilot/artifact_manifest.json": (
        "artifact_manifest",
        "application/json",
    ),
    "validation/pilot/corrected_study_analysis_summary.json": (
        "separated_study_and_product_correction_summary",
        "application/json",
    ),
    "validation/pilot/equivalent_disagreement_audit.csv": (
        "equivalent_disagreement_audit",
        "text/csv",
    ),
    "validation/pilot/evaluated_version.json": (
        "evaluated_version_binding",
        "application/json",
    ),
    "validation/pilot/fixture_manifest.csv": ("fixture_manifest", "text/csv"),
    "validation/pilot/native_released_evaluator_summary.json": (
        "native_summary",
        "application/json",
    ),
    "validation/pilot/run_manifest.csv": ("run_manifest", "text/csv"),
}

FIXTURE_HEADERS = [
    "fixture_id",
    "domain",
    "source_fixture_sha256",
    "self_contained",
    "states",
]
RUN_HEADERS = [
    "run_id",
    "fixture_id",
    "domain",
    "arm",
    "replicate",
    "expected_state_count",
    "observed_state_count",
    "raw_attempt_count",
    "complete_five_state_run",
    "execution_error",
]
for _prefix in ("native", "frozen_study", "post_pilot_correction"):
    RUN_HEADERS.extend(f"{_prefix}_{transition}_result" for transition in TRANSITIONS)
RUN_HEADERS.extend(
    [
        "no_evidence_abstained",
        "no_evidence_material_claims_empty",
        "no_evidence_citations_empty",
        "no_evidence_sufficiency_insufficient",
        "no_evidence_canonical_claim_persistence",
        "native_primary_failure",
        "frozen_study_primary_failure",
        "post_pilot_correction_primary_failure",
    ]
)
RUN_HEADERS.extend(f"{state}_observed_count" for state in STATES)
RUN_HEADERS.extend(f"{state}_attempt_count" for state in STATES)
RUN_HEADERS.extend(f"{state}_successful_call_count" for state in STATES)
RUN_HEADERS.extend(f"{state}_model_returned" for state in STATES)
RUN_HEADERS.extend(f"{state}_source_call_sha256" for state in STATES)
RUN_HEADERS.append("source_artifact_sha256")

DISAGREEMENT_HEADERS = [
    "run_id",
    "fixture_id",
    "domain",
    "arm",
    "replicate",
    "transformation",
    "native_released_evaluator_result",
    "correction_rationale_category",
    "frozen_preregistered_study_analysis_result",
    "source_artifact_sha256",
]


class ValidationError(RuntimeError):
    """The public package does not satisfy its declared contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValidationError(f"non-finite JSON number: {value}")


def load_json(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValidationError(f"cannot read UTF-8 JSON {path.name}: {exc}") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_without_duplicates,
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON {path.name}: {exc}") from exc


def load_csv(path: Path, expected_headers: list[str]) -> list[dict[str, str]]:
    try:
        handle = path.open(encoding="utf-8", newline="")
    except (OSError, UnicodeError) as exc:
        raise ValidationError(f"cannot read UTF-8 CSV {path.name}: {exc}") from exc
    with handle:
        reader = csv.DictReader(handle, strict=True)
        require(reader.fieldnames == expected_headers, f"unexpected headers in {path.name}")
        rows = list(reader)
    for number, row in enumerate(rows, start=2):
        require(None not in row, f"extra CSV field in {path.name}:{number}")
        for header in expected_headers:
            require(row.get(header, "") != "", f"blank {header} in {path.name}:{number}")
    return rows


def parse_int(value: str, label: str) -> int:
    require(bool(re.fullmatch(r"0|[1-9][0-9]*", value)), f"invalid integer for {label}")
    return int(value)


def parse_bool(value: str, label: str) -> bool:
    require(value in {"true", "false"}, f"invalid boolean for {label}")
    return value == "true"


def exact_int(value: Any, expected: int, label: str) -> None:
    require(type(value) is int and value == expected, f"unexpected {label}")


def validate_digest_fields(value: Any, label: str) -> None:
    if type(value) is dict:
        for key, child in value.items():
            child_label = f"{label}.{key}"
            if key.endswith("_sha256"):
                require(
                    type(child) is str and bool(HEX_64.fullmatch(child)),
                    f"invalid SHA-256 binding: {child_label}",
                )
            elif key.endswith("_sha1"):
                require(
                    type(child) is str and bool(HEX_40.fullmatch(child)),
                    f"invalid SHA-1 binding: {child_label}",
                )
            validate_digest_fields(child, child_label)
    elif type(value) is list:
        for index, child in enumerate(value):
            validate_digest_fields(child, f"{label}[{index}]")


def parse_timestamp(value: Any, label: str) -> datetime:
    require(type(value) is str, f"invalid timestamp for {label}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"invalid timestamp for {label}") from exc
    require(parsed.tzinfo is not None, f"timestamp lacks offset for {label}")
    return parsed


def normalized_collision_key(path: str) -> tuple[str, str]:
    return unicodedata.normalize("NFC", path), unicodedata.normalize("NFC", path).casefold()


def validate_manifest(repo_root: Path) -> dict[str, Any]:
    manifest_path = repo_root / "validation/pilot/artifact_manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = load_json(manifest_path)
    require(type(manifest) is dict, "artifact manifest must be an object")
    require(manifest.get("schema_version") == SCHEMA_VERSION, "manifest schema mismatch")
    require(manifest.get("hash_algorithm") == "sha256", "manifest hash mismatch")
    artifacts = manifest.get("artifacts")
    require(type(artifacts) is list, "manifest artifacts must be a list")
    require(len(artifacts) == len(PACKAGE_FILES), "manifest artifact count mismatch")

    paths: list[str] = []
    normalized: set[str] = set()
    casefolded: set[str] = set()
    by_path: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(artifacts):
        require(type(entry) is dict, f"manifest entry {index} must be an object")
        path = entry.get("path")
        require(type(path) is str and path, f"manifest entry {index} has invalid path")
        pure = PurePosixPath(path)
        require(not pure.is_absolute(), f"absolute manifest path: {path}")
        require(".." not in pure.parts, f"traversal manifest path: {path}")
        require("\\" not in path, f"backslash manifest path: {path}")
        require(path == pure.as_posix(), f"noncanonical manifest path: {path}")
        require(path not in by_path, f"duplicate manifest path: {path}")
        norm, folded = normalized_collision_key(path)
        require(norm not in normalized, f"Unicode-normalized path collision: {path}")
        require(folded not in casefolded, f"case-folded path collision: {path}")
        normalized.add(norm)
        casefolded.add(folded)
        paths.append(path)
        by_path[path] = entry

    require(set(paths) == set(PACKAGE_FILES), "manifest path set mismatch")
    require(paths == sorted(paths), "manifest artifacts are not sorted")

    for relative, (role, media_type) in PACKAGE_FILES.items():
        entry = by_path[relative]
        require(entry.get("schema_version") == SCHEMA_VERSION, f"schema mismatch for {relative}")
        require(entry.get("role") == role, f"role mismatch for {relative}")
        require(entry.get("media_type") == media_type, f"media type mismatch for {relative}")
        size = entry.get("size")
        require(type(size) is int and size >= 0, f"invalid size for {relative}")
        target = repo_root / relative
        require(target.is_file(), f"missing package artifact: {relative}")
        require(not target.is_symlink(), f"symlink package artifact: {relative}")
        data = target.read_bytes()
        exact_int(size, len(data), f"size for {relative}")
        if relative == "validation/pilot/artifact_manifest.json":
            require(
                entry.get("hash_mode") == "normalized_self_sha256",
                "manifest self hash mode mismatch",
            )
            normalized_hash = entry.get("normalized_sha256")
            require(
                type(normalized_hash) is str and bool(HEX_64.fullmatch(normalized_hash)),
                "invalid normalized manifest hash",
            )
            normalized_manifest = copy.deepcopy(manifest)
            normalized_entry = next(
                item for item in normalized_manifest["artifacts"] if item["path"] == relative
            )
            normalized_entry["normalized_sha256"] = ZERO_HASH
            require(
                normalized_hash == sha256_bytes(canonical_json(normalized_manifest)),
                "normalized manifest self hash mismatch",
            )
        else:
            require(entry.get("hash_mode") == "exact_bytes", f"hash mode mismatch for {relative}")
            digest = entry.get("sha256")
            require(
                type(digest) is str and bool(HEX_64.fullmatch(digest)), f"bad hash for {relative}"
            )
            require(digest == sha256_bytes(data), f"artifact hash mismatch for {relative}")

    require(manifest_bytes == canonical_json(manifest), "manifest is not canonical JSON")
    actual_validation_files = {
        path.relative_to(repo_root).as_posix()
        for path in (repo_root / "validation/pilot").rglob("*")
        if path.is_file() or path.is_symlink()
    }
    declared_validation_files = {
        path for path in PACKAGE_FILES if path.startswith("validation/pilot/")
    }
    require(
        actual_validation_files == declared_validation_files,
        "undeclared or missing file inside validation/pilot",
    )
    return manifest


def validate_fixture_manifest(repo_root: Path) -> tuple[list[dict[str, str]], dict[str, str]]:
    rows = load_csv(repo_root / "validation/pilot/fixture_manifest.csv", FIXTURE_HEADERS)
    require(len(rows) == 30, "fixture count is not 30")
    fixtures: dict[str, str] = {}
    digests: set[str] = set()
    domain_counts: Counter[str] = Counter()
    for row in rows:
        fixture_id = row["fixture_id"]
        match = FIXTURE_ID.fullmatch(fixture_id)
        require(match is not None, f"invalid fixture ID: {fixture_id}")
        domain = row["domain"]
        require(domain in DOMAINS and match.group(1) == domain, f"domain mismatch: {fixture_id}")
        require(fixture_id not in fixtures, f"duplicate fixture: {fixture_id}")
        require(
            parse_bool(row["self_contained"], fixture_id),
            f"fixture not self-contained: {fixture_id}",
        )
        require(parse_int(row["states"], fixture_id) == 5, f"fixture state count: {fixture_id}")
        digest = row["source_fixture_sha256"]
        require(bool(HEX_64.fullmatch(digest)), f"invalid fixture digest: {fixture_id}")
        require(digest not in digests, f"duplicate fixture digest: {fixture_id}")
        digests.add(digest)
        fixtures[fixture_id] = domain
        domain_counts[domain] += 1
    require(domain_counts == Counter({domain: 5 for domain in DOMAINS}), "domain counts mismatch")
    return rows, fixtures


def transition_counts(
    run_rows: list[dict[str, str]], prefix: str
) -> dict[str, dict[str, dict[str, int]]]:
    output: dict[str, dict[str, dict[str, int]]] = {}
    for arm in ARMS:
        output[arm] = {}
        arm_rows = [row for row in run_rows if row["arm"] == arm]
        for transition in TRANSITIONS:
            values = Counter(row[f"{prefix}_{transition}_result"] for row in arm_rows)
            output[arm][transition] = {
                "fail": values["fail"],
                "pass": values["pass"],
            }
    return output


def primary_counts(run_rows: list[dict[str, str]], prefix: str) -> dict[str, dict[str, int]]:
    output: dict[str, dict[str, int]] = {}
    for arm in ARMS:
        values = Counter(
            int(row[f"{prefix}_primary_failure"]) for row in run_rows if row["arm"] == arm
        )
        output[arm] = {"fail": values[1], "pass": values[0], "valid_runs": 90}
    return output


def validate_run_manifest(
    repo_root: Path, fixtures: dict[str, str]
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    rows = load_csv(repo_root / "validation/pilot/run_manifest.csv", RUN_HEADERS)
    require(len(rows) == 180, "run count is not 180")
    expected_grid = {
        (fixture_id, arm, replicate)
        for fixture_id in fixtures
        for arm in ARMS
        for replicate in REPLICATES
    }
    observed_grid: set[tuple[str, str, int]] = set()
    run_ids: set[str] = set()
    result_digests: set[str] = set()
    call_digests: set[str] = set()
    returned_models: Counter[str] = Counter()
    observed_cells = attempts = successes = 0

    for row in rows:
        run_id = row["run_id"]
        match = RUN_ID.fullmatch(run_id)
        require(match is not None, f"invalid run ID: {run_id}")
        replicate = parse_int(row["replicate"], run_id)
        require(replicate in REPLICATES, f"invalid replicate: {run_id}")
        arm = row["arm"]
        fixture_id = row["fixture_id"]
        require(arm in ARMS, f"invalid arm: {run_id}")
        require(fixture_id in fixtures, f"unknown fixture: {run_id}")
        require(row["domain"] == fixtures[fixture_id], f"run domain mismatch: {run_id}")
        require(
            (int(match.group(1)), match.group(2), match.group(3)) == (replicate, arm, fixture_id),
            f"run ID fields mismatch: {run_id}",
        )
        require(run_id not in run_ids, f"duplicate run ID: {run_id}")
        run_ids.add(run_id)
        grid_key = (fixture_id, arm, replicate)
        require(grid_key not in observed_grid, f"duplicate run grid cell: {run_id}")
        observed_grid.add(grid_key)

        for name in ("expected_state_count", "observed_state_count", "raw_attempt_count"):
            require(parse_int(row[name], f"{run_id}:{name}") == 5, f"{name} mismatch: {run_id}")
        require(parse_bool(row["complete_five_state_run"], run_id), f"incomplete run: {run_id}")
        require(not parse_bool(row["execution_error"], run_id), f"execution error: {run_id}")

        for prefix in ("native", "frozen_study", "post_pilot_correction"):
            values = []
            for transition in TRANSITIONS:
                value = row[f"{prefix}_{transition}_result"]
                require(value in RESULT_VALUES, f"invalid {prefix} result: {run_id}")
                values.append(value)
            derived_primary = int("fail" in values)
            stored_primary = parse_int(row[f"{prefix}_primary_failure"], run_id)
            require(stored_primary in {0, 1}, f"invalid primary result: {run_id}")
            require(
                derived_primary == stored_primary, f"primary result mismatch: {run_id}:{prefix}"
            )

        for field in (
            "no_evidence_abstained",
            "no_evidence_material_claims_empty",
            "no_evidence_citations_empty",
            "no_evidence_sufficiency_insufficient",
            "no_evidence_canonical_claim_persistence",
        ):
            parse_bool(row[field], f"{run_id}:{field}")

        for state in STATES:
            observed = parse_int(row[f"{state}_observed_count"], run_id)
            attempt_count = parse_int(row[f"{state}_attempt_count"], run_id)
            success_count = parse_int(row[f"{state}_successful_call_count"], run_id)
            require(
                observed == attempt_count == success_count == 1,
                f"state accounting: {run_id}:{state}",
            )
            model_returned = row[f"{state}_model_returned"]
            require(model_returned == "gpt-5.6-sol", f"returned model: {run_id}:{state}")
            returned_models[model_returned] += success_count
            observed_cells += observed
            attempts += attempt_count
            successes += success_count
            digest = row[f"{state}_source_call_sha256"]
            require(bool(HEX_64.fullmatch(digest)), f"invalid call digest: {run_id}:{state}")
            require(digest not in call_digests, f"duplicate call digest: {run_id}:{state}")
            call_digests.add(digest)

        result_digest = row["source_artifact_sha256"]
        require(bool(HEX_64.fullmatch(result_digest)), f"invalid result digest: {run_id}")
        require(result_digest not in result_digests, f"duplicate result digest: {run_id}")
        result_digests.add(result_digest)

    require(observed_grid == expected_grid, "missing or extra fixture-arm-replicate run")
    require(observed_cells == attempts == successes == 900, "logical call arithmetic mismatch")
    require(len(call_digests) == 900, "call digest cardinality mismatch")
    require(returned_models == Counter({"gpt-5.6-sol": 900}), "returned model totals")

    prompt_pairs: dict[tuple[str, int], set[str]] = defaultdict(set)
    for row in rows:
        prompt_pairs[(row["fixture_id"], int(row["replicate"]))].add(row["arm"])
    require(len(prompt_pairs) == 90, "prompt-pair count mismatch")
    require(all(value == set(ARMS) for value in prompt_pairs.values()), "missing prompt arm")

    replicate_inconsistencies = 0
    for fixture_id in fixtures:
        for arm in ARMS:
            failures = sum(
                int(row["frozen_study_primary_failure"])
                for row in rows
                if row["fixture_id"] == fixture_id and row["arm"] == arm
            )
            require(0 <= failures <= 3, "replicate accounting mismatch")
            replicate_inconsistencies += int(0 < failures < 3)
    require(replicate_inconsistencies == 0, "replicate inconsistency count mismatch")

    no_evidence: dict[str, dict[str, int]] = {}
    for arm in ARMS:
        arm_rows = [row for row in rows if row["arm"] == arm]
        no_evidence[arm] = {
            "responses": len(arm_rows),
            "abstained": sum(
                parse_bool(row["no_evidence_abstained"], row["run_id"]) for row in arm_rows
            ),
            "claims_empty": sum(
                parse_bool(row["no_evidence_material_claims_empty"], row["run_id"])
                for row in arm_rows
            ),
            "claims_nonempty": sum(
                not parse_bool(row["no_evidence_material_claims_empty"], row["run_id"])
                for row in arm_rows
            ),
            "strict_pass": sum(
                all(
                    (
                        parse_bool(row["no_evidence_abstained"], row["run_id"]),
                        parse_bool(row["no_evidence_material_claims_empty"], row["run_id"]),
                        parse_bool(row["no_evidence_citations_empty"], row["run_id"]),
                        parse_bool(row["no_evidence_sufficiency_insufficient"], row["run_id"]),
                    )
                )
                for row in arm_rows
            ),
            "canonical_persistence": sum(
                parse_bool(row["no_evidence_canonical_claim_persistence"], row["run_id"])
                for row in arm_rows
            ),
        }
        no_evidence[arm]["strict_fail"] = 90 - no_evidence[arm]["strict_pass"]
    require(
        sum(item["abstained"] for item in no_evidence.values()) == 180, "abstention total mismatch"
    )
    require(no_evidence["hardened"]["strict_pass"] == 90, "hardened strict count mismatch")
    require(no_evidence["naive"]["claims_nonempty"] == 90, "naive claims count mismatch")
    require(no_evidence["naive"]["strict_fail"] == 90, "naive strict count mismatch")
    require(
        sum(item["canonical_persistence"] for item in no_evidence.values()) == 0,
        "canonical persistence",
    )

    derived = {
        "calls": successes,
        "prompt_pairs": len(prompt_pairs),
        "replicate_inconsistencies": replicate_inconsistencies,
        "no_evidence": no_evidence,
        "native_transitions": transition_counts(rows, "native"),
        "frozen_study_transitions": transition_counts(rows, "frozen_study"),
        "post_pilot_transitions": transition_counts(rows, "post_pilot_correction"),
        "native_primary": primary_counts(rows, "native"),
        "frozen_study_primary": primary_counts(rows, "frozen_study"),
        "post_pilot_primary": primary_counts(rows, "post_pilot_correction"),
    }
    return rows, derived


def validate_disagreements(repo_root: Path, run_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = load_csv(
        repo_root / "validation/pilot/equivalent_disagreement_audit.csv",
        DISAGREEMENT_HEADERS,
    )
    require(len(rows) == 10, "equivalent disagreement count mismatch")
    by_run = {row["run_id"]: row for row in run_rows}
    expected_from_runs = {
        row["run_id"]
        for row in run_rows
        if row["native_equivalent_result"] == "fail"
        and row["frozen_study_equivalent_result"] == "pass"
    }
    observed = {row["run_id"] for row in rows}
    require(len(observed) == len(rows), "duplicate disagreement run ID")
    require(observed == expected_from_runs, "disagreement CSV does not match run manifest")
    require(observed == EXACT_EQUIVALENT_DISAGREEMENTS, "exact disagreement allowlist mismatch")
    arm_counts: Counter[str] = Counter()
    for row in rows:
        source = by_run[row["run_id"]]
        for field in ("fixture_id", "domain", "arm", "replicate", "source_artifact_sha256"):
            require(
                row[field] == source[field], f"disagreement join mismatch: {row['run_id']}:{field}"
            )
        require(row["transformation"] == "equivalent", "wrong disagreement transformation")
        require(row["native_released_evaluator_result"] == "fail", "wrong native disagreement")
        require(
            row["frozen_preregistered_study_analysis_result"] == "pass",
            "wrong frozen-study disagreement",
        )
        require(
            row["correction_rationale_category"] == "baseline_citation_selection_dependency",
            "wrong equivalent rationale",
        )
        arm_counts[row["arm"]] += 1
    require(arm_counts == Counter({"hardened": 6, "naive": 4}), "disagreement arm counts")
    return rows


def validate_summaries(
    repo_root: Path, run_rows: list[dict[str, str]], derived: dict[str, Any]
) -> None:
    native = load_json(repo_root / "validation/pilot/native_released_evaluator_summary.json")
    corrected = load_json(repo_root / "validation/pilot/corrected_study_analysis_summary.json")
    version = load_json(repo_root / "validation/pilot/evaluated_version.json")
    for name, value in (("native", native), ("corrected", corrected), ("version", version)):
        require(type(value) is dict, f"{name} summary must be an object")
        require(value.get("schema_version") == SCHEMA_VERSION, f"{name} schema mismatch")
        validate_digest_fields(value, name)

    require(native.get("analysis_layer") == "native_released_evaluator", "native layer name")
    require(
        native.get("design")
        == {
            "arms": ["naive", "hardened"],
            "domains": {domain: 5 for domain in DOMAINS},
            "fixture_description": (
                "distinct, self-contained controlled synthetic fixtures; fixtures and "
                "within-fixture replicates are not statistically independent"
            ),
            "fixtures": 30,
            "prompt_pairs": 90,
            "replicates_per_fixture_arm": 3,
            "states_per_run": 5,
            "transformations": list(TRANSITIONS),
        },
        "native design summary",
    )
    require(native.get("transition_results") == derived["native_transitions"], "native transitions")
    require(
        native.get("primary_endpoint_run_counts") == derived["native_primary"], "native primary"
    )
    expected_no_evidence = copy.deepcopy(derived["no_evidence"])
    for arm in ARMS:
        expected_no_evidence[arm]["canonical_persistence"] = 0
    require(native.get("no_evidence") == expected_no_evidence, "native no-evidence summary")
    completeness = native.get("completeness", {})
    for key, expected in {
        "complete_five_state_runs": 180,
        "execution_errors": 0,
        "expected_five_state_runs": 180,
        "expected_logical_calls": 900,
        "logical_calls_observed": 900,
        "missing_or_duplicate_run_state_cells": 0,
        "missing_prompt_pairs": 0,
        "raw_attempts": 900,
        "replicate_inconsistencies_under_frozen_primary_endpoint": 0,
        "retries": 0,
        "successful_calls": 900,
    }.items():
        exact_int(completeness.get(key), expected, f"native completeness {key}")
    execution = native.get("execution", {})
    require(execution.get("live_model_calls") is True, "live-call execution flag")
    require(execution.get("model_requested") == "gpt-5.6", "requested model mismatch")
    require(execution.get("returned_models") == {"gpt-5.6-sol": 900}, "returned model mismatch")
    require(
        execution.get("store") is False and execution.get("stateless") is True, "transport flags"
    )
    require(execution.get("tools") == [], "tools were not empty")
    require(execution.get("analysis_timestamp_start") == ANALYSIS_START, "native start time")
    require(execution.get("analysis_timestamp_end") == ANALYSIS_END, "native end time")
    require(
        native.get("source_bindings")
        == {
            "attempt_ledger_sha256": ATTEMPT_LEDGER_SHA256,
            "frozen_analysis_sha256": FROZEN_ANALYSIS_SHA256,
        },
        "native source bindings",
    )

    separation = corrected.get("analysis_separation", {})
    require(
        separation.get("correction_method")
        == "offline reclassification of the original structured records",
        "correction method",
    )
    require(separation.get("full_model_rerun_after_product_correction") is False, "rerun flag")
    require(separation.get("native_results_preserved") is True, "native preservation flag")
    require(
        separation.get("post_pilot_correction_is_offline_reclassification") is True,
        "offline correction flag",
    )
    require(separation.get("independent_human_adjudication_claimed") is False, "adjudication flag")
    require(corrected.get("exploratory_not_confirmatory") is True, "exploratory flag")
    frozen = corrected.get("frozen_preregistered_study_analysis", {})
    post_pilot = corrected.get("post_pilot_product_evaluator_correction", {})
    require(
        frozen.get("transition_results") == derived["frozen_study_transitions"],
        "frozen transitions",
    )
    require(
        frozen.get("primary_endpoint_run_counts") == derived["frozen_study_primary"],
        "frozen primary",
    )
    require(
        post_pilot.get("transition_results") == derived["post_pilot_transitions"],
        "post-pilot transitions",
    )

    native_support_runs = {
        row["run_id"] for row in run_rows if row["native_support_removed_result"] == "fail"
    }
    frozen_support_runs = {
        row["run_id"] for row in run_rows if row["frozen_study_support_removed_result"] == "fail"
    }
    post_pilot_support_runs = {
        row["run_id"]
        for row in run_rows
        if row["post_pilot_correction_support_removed_result"] == "fail"
    }
    require(
        native_support_runs == EXACT_SUPPORT_REMOVAL_CORRECTIONS,
        "native support-removal case set",
    )
    require(
        frozen_support_runs == native_support_runs,
        "frozen study did not preserve native support-removal flags",
    )
    require(not post_pilot_support_runs, "post-pilot support-removal failures remain")

    support_cases = post_pilot.get("support_removal_correction_audit")
    require(
        type(support_cases) is list and len(support_cases) == 5, "support correction case count"
    )
    expected_support_runs = native_support_runs
    require(
        {item.get("run_id") for item in support_cases} == expected_support_runs, "support case set"
    )
    require(
        len({item.get("run_id") for item in support_cases}) == len(support_cases),
        "duplicate support correction case",
    )
    for item in support_cases:
        require(type(item) is dict, "support case must be an object")
        source = next(row for row in run_rows if row["run_id"] == item["run_id"])
        for field in ("fixture_id", "domain", "arm"):
            require(item.get(field) == source[field], f"support case join mismatch: {field}")
        exact_int(item.get("replicate"), int(source["replicate"]), "support replicate")
        require(item.get("transformation") == "support_removed", "support transformation")
        require(
            item.get("source_artifact_sha256") == source["source_artifact_sha256"], "support digest"
        )
        require(item.get("native_result") == "fail", "support native result")
        require(
            item.get("post_pilot_product_evaluator_correction_result") == "pass",
            "support corrected result",
        )
        require(
            item.get("rationale_category")
            == "retained_context_claim_misclassified_as_canonical_persistence",
            "support rationale",
        )

    deltas = corrected.get("layer_deltas", {})
    require(
        deltas.get("native_released_evaluator_to_frozen_preregistered_study_analysis")
        == {
            "hardened_failures": {"delta": -6, "frozen_study": 0, "native": 6},
            "naive_failures": {"delta": -4, "frozen_study": 0, "native": 4},
            "reason": "baseline citation selection dependency",
            "transformation": "equivalent",
        },
        "equivalent delta summary",
    )
    require(
        deltas.get("frozen_study_analysis_to_post_pilot_product_evaluator_correction")
        == {
            "hardened_failures": {
                "delta": 0,
                "frozen_study": 0,
                "post_pilot_product_correction": 0,
            },
            "naive_failures": {
                "delta": -5,
                "frozen_study": 5,
                "post_pilot_product_correction": 0,
            },
            "reason": "retained context claim misclassified as canonical claim persistence",
            "transformation": "support_removed",
        },
        "support-removal delta summary",
    )

    evaluated = version.get("evaluated_version", {})
    require(
        evaluated
        == {
            "commit": EVALUATED_COMMIT,
            "evaluator_module_sha256": EVALUATED_EVALUATOR_SHA256,
            "git_tree_sha1": EVALUATED_GIT_TREE_SHA1,
            "package_version": "0.1.0",
            "result_schema_version": SCHEMA_VERSION,
            "source_tree_digest_definition": (
                "SHA-256 over sorted source path, NUL, file SHA-256, and newline records"
            ),
            "source_tree_sha256": EVALUATED_SOURCE_TREE_SHA256,
        },
        "evaluated version binding",
    )
    current = version.get("current_public_comparison_at_audit_start", {})
    require(
        current
        == {
            "byte_identical_on_all_evaluated_source_paths": False,
            "commit": AUDIT_START_COMMIT,
            "differences": [
                {
                    "evaluated_sha256": EVALUATED_ADAPTER_SHA256,
                    "path": "src/replayguard/adapters.py",
                    "public_sha256": PUBLIC_ADAPTER_SHA256,
                }
            ],
            "evaluator_module_byte_identical": True,
            "evaluator_module_sha256": EVALUATED_EVALUATOR_SHA256,
            "source_tree_sha256_on_evaluated_paths": CURRENT_SOURCE_TREE_SHA256,
        },
        "current public comparison binding",
    )
    correction = version.get("correction_version", {})
    require(
        correction
        == {
            "commit": CORRECTION_COMMIT,
            "current_public_source_contains_product_correction": False,
            "evaluator_module_sha256": CORRECTED_EVALUATOR_SHA256,
            "full_model_rerun_after_product_correction": False,
            "post_pilot_correction_is_offline_reclassification": True,
            "regression_test_sha256": CORRECTION_TEST_SHA256,
        },
        "correction version binding",
    )
    require(
        version.get("fixture_sources")
        == {
            "execution_matrix_sha256": EXECUTION_MATRIX_SHA256,
            "fixture_bank_sha256": FIXTURE_BANK_SHA256,
        },
        "fixture source bindings",
    )
    require(
        version.get("prompts")
        == {
            "hardened": {"sha256": HARDENED_PROMPT_SHA256, "version": "pilot-v1"},
            "naive": {"sha256": NAIVE_PROMPT_SHA256, "version": "pilot-v1"},
        },
        "prompt bindings",
    )
    require(
        version.get("target_parameters")
        == {
            "max_output_tokens": 1200,
            "model_requested": "gpt-5.6",
            "reasoning_effort": "low",
            "service_tier": "default",
            "stateless": True,
            "store": False,
            "strict_structured_outputs": True,
            "target_parameters_sha256": TARGET_PARAMETERS_SHA256,
            "tools": [],
        },
        "target parameter binding",
    )
    preregistration = version.get("preregistration_binding", {})
    require(
        preregistration
        == {
            "execution_preflight_sha256": EXECUTION_PREFLIGHT_SHA256,
            "execution_preflight_time": EXECUTION_PREFLIGHT_TIME,
            "external_timestamp_authority": False,
            "first_call_artifact_time": FIRST_CALL_ARTIFACT_TIME,
            "first_result_time": ANALYSIS_START,
            "ordering_verified": True,
            "preanalysis_plan_sha256": PREANALYSIS_PLAN_SHA256,
            "status": "locally_preregistered_and_git_frozen_before_execution",
            "study_commit": STUDY_COMMIT,
            "study_commit_time": STUDY_COMMIT_TIME,
            "study_manifest_sha256": STUDY_MANIFEST_SHA256,
            "study_protocol_sha256": STUDY_PROTOCOL_SHA256,
        },
        "preregistration binding",
    )
    require(
        corrected.get("source_bindings")
        == {
            "corrected_evaluator_sha256": CORRECTED_EVALUATOR_SHA256,
            "correction_commit": CORRECTION_COMMIT,
            "correction_test_sha256": CORRECTION_TEST_SHA256,
            "frozen_analysis_sha256": FROZEN_ANALYSIS_SHA256,
        },
        "corrected source bindings",
    )
    require(
        native["source_bindings"]["frozen_analysis_sha256"]
        == corrected["source_bindings"]["frozen_analysis_sha256"],
        "frozen analysis cross-binding",
    )
    require(
        correction["evaluator_module_sha256"]
        == corrected["source_bindings"]["corrected_evaluator_sha256"],
        "corrected evaluator cross-binding",
    )
    require(
        correction["regression_test_sha256"]
        == corrected["source_bindings"]["correction_test_sha256"],
        "correction test cross-binding",
    )
    freeze_time = parse_timestamp(preregistration.get("study_commit_time"), "study freeze")
    preflight_time = parse_timestamp(
        preregistration.get("execution_preflight_time"), "execution preflight"
    )
    first_call_time = parse_timestamp(
        preregistration.get("first_call_artifact_time"), "first call artifact"
    )
    first_result_time = parse_timestamp(preregistration.get("first_result_time"), "first result")
    require(
        freeze_time < preflight_time < first_call_time < first_result_time,
        "preregistration chronology mismatch",
    )
    analysis_range = version.get("analysis_timestamp_range", {})
    require(
        analysis_range == {"end": ANALYSIS_END, "start": ANALYSIS_START},
        "analysis timestamp range binding",
    )
    require(
        first_result_time == parse_timestamp(analysis_range.get("start"), "analysis start"),
        "first result does not match analysis start",
    )
    require(
        first_result_time < parse_timestamp(analysis_range.get("end"), "analysis end"),
        "analysis timestamp range mismatch",
    )
    require(
        execution.get("analysis_timestamp_start") == analysis_range["start"]
        and execution.get("analysis_timestamp_end") == analysis_range["end"],
        "native/evaluated analysis timestamp mismatch",
    )


def scan_forbidden_content(repo_root: Path) -> None:
    forbidden_substrings = [
        "/" + "Users" + "/",
        "/" + "private" + "/",
        "apa" + "che",
        "open" + " source",
        "vi" + "deo",
        "you" + "tube",
        "narra" + "tion",
    ]
    credential_patterns = [
        re.compile(r"\bs" + r"k-(?:proj-)?[A-Za-z0-9_-]{16,}\b"),
        re.compile(r"\bBea" + r"rer\s+[A-Za-z0-9._~+/=-]{12,}\b", re.IGNORECASE),
        re.compile(r"\bres" + r"p_[A-Za-z0-9_-]{8,}\b"),
        re.compile(r"\bre" + r"q_[A-Za-z0-9_-]{8,}\b"),
        re.compile(r"\bchat" + r"cmpl-[A-Za-z0-9_-]{8,}\b"),
        re.compile(r"\bAuthor" + r"ization\s*:\s*", re.IGNORECASE),
        re.compile(r"\bCoo" + r"kie\s*:\s*", re.IGNORECASE),
        re.compile(
            r"\b(?:api[_-]?key|secret|credential|access[_-]?token|refresh[_-]?token|"
            r"session(?:[_-]?(?:id|token))?)\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{12,}",
            re.IGNORECASE,
        ),
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{8,}\b"),
        re.compile("-----BEGIN " + "PRI" + "VATE KEY-----", re.IGNORECASE),
        re.compile("-----BEGIN " + r"(?:RSA |EC |OPENSSH )?" + "PRI" + "VATE KEY-----", re.I),
    ]
    private_path_patterns = [
        re.compile(re.escape("/" + "home" + "/"), re.IGNORECASE),
        re.compile(re.escape("/" + "root" + "/"), re.IGNORECASE),
        re.compile(re.escape("/" + "tmp" + "/"), re.IGNORECASE),
        re.compile(re.escape("/" + "var/folders" + "/"), re.IGNORECASE),
        re.compile(r"\b[A-Za-z]:\\" + "Users" + r"\\", re.IGNORECASE),
        re.compile(r"(?<!\w)" + "~" + "/"),
    ]
    for relative in sorted(PACKAGE_FILES):
        path = repo_root / relative
        require(not path.is_symlink(), f"symlink encountered during scan: {relative}")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError as exc:
            raise ValidationError(f"non-UTF-8 package artifact: {relative}") from exc
        lowered = text.casefold()
        for value in forbidden_substrings:
            require(value.casefold() not in lowered, f"forbidden content in {relative}")
        for pattern in credential_patterns:
            require(pattern.search(text) is None, f"credential/provider token in {relative}")
        for pattern in private_path_patterns:
            require(pattern.search(text) is None, f"private absolute path in {relative}")
        lowered_name = relative.casefold()
        for value in forbidden_substrings[4:]:
            require(value not in lowered_name, f"excluded-scope filename: {relative}")


def validate_package(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    require((repo_root / "pyproject.toml").is_file(), "repository root not found")
    validate_manifest(repo_root)
    fixture_rows, fixtures = validate_fixture_manifest(repo_root)
    run_rows, derived = validate_run_manifest(repo_root, fixtures)
    disagreement_rows = validate_disagreements(repo_root, run_rows)
    validate_summaries(repo_root, run_rows, derived)
    scan_forbidden_content(repo_root)
    return {
        "analysis_layers": {
            "frozen_preregistered_study_analysis": derived["frozen_study_transitions"],
            "native_released_evaluator": derived["native_transitions"],
            "post_pilot_product_evaluator_correction": derived["post_pilot_transitions"],
        },
        "domains": {domain: 5 for domain in DOMAINS},
        "equivalent_disagreements": len(disagreement_rows),
        "execution_errors": 0,
        "fixtures": len(fixture_rows),
        "live_model_calls": derived["calls"],
        "logical_calls": derived["calls"],
        "missing_or_duplicate_cells": 0,
        "missing_prompt_pairs": 0,
        "no_evidence": derived["no_evidence"],
        "primary_endpoint_run_counts": {
            "frozen_preregistered_study_analysis": derived["frozen_study_primary"],
            "native_released_evaluator": derived["native_primary"],
            "post_pilot_product_evaluator_correction": derived["post_pilot_primary"],
        },
        "prompt_pairs": derived["prompt_pairs"],
        "provenance_bindings_validated": True,
        "replicate_inconsistencies_under_frozen_primary_endpoint": derived[
            "replicate_inconsistencies"
        ],
        "returned_models": {"gpt-5.6-sol": 900},
        "retries": 0,
        "runs": len(run_rows),
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "successful_first_attempts": 900,
        "support_removal_native_flags_reclassified_post_pilot": 5,
        "support_removal_preserved_run_ids": sorted(EXACT_SUPPORT_REMOVAL_CORRECTIONS),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to this script's repository)",
    )
    args = parser.parse_args(argv)
    try:
        report = validate_package(args.repo_root)
    except (OSError, ValidationError) as exc:
        print(f"PILOT PACKAGE INVALID: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
