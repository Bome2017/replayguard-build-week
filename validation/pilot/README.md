# ReplayGuard pilot evidence package

This directory is the sanitized, offline-auditable evidence package for the exploratory ReplayGuard
pilot summarized in [PILOT_VALIDATION.md](../../PILOT_VALIDATION.md).

Run the verifier from the repository root:

```bash
python scripts/validate_pilot_package.py
```

The command uses only the Python standard library. It makes no network or model request and needs no
credential.

## Package index

- [CLAIM_EVIDENCE_MATRIX.md](CLAIM_EVIDENCE_MATRIX.md) records the public verdict and approved
  boundary for every pilot headline and current judge-surface material claim.
- [METHODOLOGY.md](METHODOLOGY.md) defines the design, accounting, outcomes, corrections, and
  limitations.
- [fixture_manifest.csv](fixture_manifest.csv) lists 30 sanitized fixture identifiers, domains, and
  source digests.
- [run_manifest.csv](run_manifest.csv) lists all 180 fixture-arm-replicate runs, five-state
  completeness, and results at each analysis layer.
- [native_released_evaluator_summary.json](native_released_evaluator_summary.json) preserves native
  released-evaluator aggregates.
- [corrected_study_analysis_summary.json](corrected_study_analysis_summary.json) keeps the frozen
  study layer and later evaluator-correction layer distinct.
- [equivalent_disagreement_audit.csv](equivalent_disagreement_audit.csv) lists the exact ten
  equivalent-transition false failures and source-record digests.
- [evaluated_version.json](evaluated_version.json) binds the evaluated package, evaluator, prompts,
  fixture sources, parameters, analysis interval, and public-source comparison.
- [artifact_manifest.json](artifact_manifest.json) binds every file in the public pilot package.

## Data boundary

The package contains identifiers, counts, categorical outcomes, model names, and cryptographic
digests. It does not contain raw provider response IDs, credentials, request/response bodies,
retained call records, private protocols, local paths, or prior submission material. Source-record
digests bind each sanitized row without publishing the underlying private record.

The 900 calls were not rerun. Native results, the frozen preregistered study analysis, and the later
evaluator-correction audit are separate layers over the original execution records.

## Integrity convention

For ordinary files, `artifact_manifest.json` stores the SHA-256 of the exact file bytes. A manifest
cannot contain its own ordinary byte hash without a circular dependency, so its self-entry uses a
documented canonical convention: replace only its own `normalized_sha256` value with 64 zeroes,
serialize with the package's canonical JSON formatting, and hash those bytes. The offline validator
checks this convention and every listed byte size.
