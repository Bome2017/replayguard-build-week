import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_pilot_package.py"
EXPECTED_EQUIVALENT_DISAGREEMENTS = {
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
EXPECTED_SUPPORT_REMOVAL_CORRECTIONS = {
    "r1-naive-travel-04",
    "r2-naive-leave-03",
    "r2-naive-leave-04",
    "r2-naive-travel-01",
    "r3-naive-leave-03",
}


def run_validator() -> dict:
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR), "--repo-root", str(ROOT)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_pilot_package_validator_and_headline_counts() -> None:
    report = run_validator()

    assert report["status"] == "PASS"
    assert report["fixtures"] == 30
    assert report["domains"] == {
        "equip": 5,
        "infosec": 5,
        "leave": 5,
        "proc": 5,
        "records": 5,
        "travel": 5,
    }
    assert report["runs"] == 180
    assert report["runs"] == report["fixtures"] * 2 * 3
    assert report["logical_calls"] == 900
    assert report["logical_calls"] == report["runs"] * 5
    assert report["live_model_calls"] == 900
    assert report["successful_first_attempts"] == 900
    assert report["retries"] == 0
    assert report["returned_models"] == {"gpt-5.6-sol": 900}
    assert report["execution_errors"] == 0
    assert report["missing_or_duplicate_cells"] == 0
    assert report["missing_prompt_pairs"] == 0
    assert report["prompt_pairs"] == 90
    assert report["replicate_inconsistencies_under_frozen_primary_endpoint"] == 0
    assert report["equivalent_disagreements"] == 10
    assert report["support_removal_native_flags_reclassified_post_pilot"] == 5
    assert set(report["support_removal_preserved_run_ids"]) == (
        EXPECTED_SUPPORT_REMOVAL_CORRECTIONS
    )
    assert report["provenance_bindings_validated"] is True

    assert report["no_evidence"]["hardened"] == {
        "abstained": 90,
        "canonical_persistence": 0,
        "claims_empty": 90,
        "claims_nonempty": 0,
        "responses": 90,
        "strict_fail": 0,
        "strict_pass": 90,
    }
    assert report["no_evidence"]["naive"] == {
        "abstained": 90,
        "canonical_persistence": 0,
        "claims_empty": 0,
        "claims_nonempty": 90,
        "responses": 90,
        "strict_fail": 90,
        "strict_pass": 0,
    }

    pass_90 = {"fail": 0, "pass": 90}
    fail_90 = {"fail": 90, "pass": 0}
    layers = report["analysis_layers"]
    assert layers == {
        "native_released_evaluator": {
            "hardened": {
                "distractor": pass_90,
                "equivalent": {"fail": 6, "pass": 84},
                "no_evidence": pass_90,
                "support_removed": pass_90,
            },
            "naive": {
                "distractor": pass_90,
                "equivalent": {"fail": 4, "pass": 86},
                "no_evidence": fail_90,
                "support_removed": {"fail": 5, "pass": 85},
            },
        },
        "frozen_preregistered_study_analysis": {
            "hardened": {
                "distractor": pass_90,
                "equivalent": pass_90,
                "no_evidence": pass_90,
                "support_removed": pass_90,
            },
            "naive": {
                "distractor": pass_90,
                "equivalent": pass_90,
                "no_evidence": fail_90,
                "support_removed": {"fail": 5, "pass": 85},
            },
        },
        "post_pilot_product_evaluator_correction": {
            "hardened": {
                "distractor": pass_90,
                "equivalent": pass_90,
                "no_evidence": pass_90,
                "support_removed": pass_90,
            },
            "naive": {
                "distractor": pass_90,
                "equivalent": pass_90,
                "no_evidence": fail_90,
                "support_removed": pass_90,
            },
        },
    }
    assert report["primary_endpoint_run_counts"] == {
        "native_released_evaluator": {
            "hardened": {"fail": 6, "pass": 84, "valid_runs": 90},
            "naive": {"fail": 90, "pass": 0, "valid_runs": 90},
        },
        "frozen_preregistered_study_analysis": {
            "hardened": {"fail": 0, "pass": 90, "valid_runs": 90},
            "naive": {"fail": 90, "pass": 0, "valid_runs": 90},
        },
        "post_pilot_product_evaluator_correction": {
            "hardened": {"fail": 0, "pass": 90, "valid_runs": 90},
            "naive": {"fail": 90, "pass": 0, "valid_runs": 90},
        },
    }


def test_exact_equivalent_disagreement_set() -> None:
    with (ROOT / "validation/pilot/equivalent_disagreement_audit.csv").open(
        encoding="utf-8"
    ) as handle:
        rows = [line.split(",", 1)[0] for line in handle.read().splitlines()[1:] if line]
    assert set(rows) == EXPECTED_EQUIVALENT_DISAGREEMENTS
    assert len(rows) == 10
