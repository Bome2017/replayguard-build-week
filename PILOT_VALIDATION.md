# ReplayGuard pilot validation

## Technical summary

ReplayGuard's exploratory pilot is supported by a sanitized aggregate evidence package. The study
used 30 distinct, self-contained controlled synthetic fixtures across six domains, two prompt arms,
three replicates per fixture and arm, and five evidence states per run:

```text
30 fixtures x 2 arms x 3 replicates = 180 five-state runs
180 runs x 5 states = 900 live model calls
```

The execution evidence contains 180 complete runs and 900 successful first attempts, with zero
execution errors, retries, missing or duplicate run-state cells, missing prompt pairs, or replicate
inconsistencies under the preregistered primary-endpoint definition. The requested model alias was
`gpt-5.6`; all 900 execution records identify the returned model as `gpt-5.6-sol`.

The most important finding is a strict no-evidence gate difference in the empty-evidence state. All
180 responses abstained. All 90 hardened responses also returned empty `material_claims`; all 90
naive responses returned nonempty `material_claims` and therefore failed the strict empty-claims
contract. None of the naive responses retained the canonical claim under the deterministic check.

This is an exploratory synthetic-fixture pilot, not confirmatory evidence of general model or
production performance.

## Key findings

The table reports failure counts out of 90 valid evaluations per arm and transformation. The three
layers are intentionally separate.

| Analysis layer | Arm | Equivalent | Distractor | Support removed | No evidence |
| --- | --- | ---: | ---: | ---: | ---: |
| Native released evaluator | Naive | 4 | 0 | 5 | 90 |
| Native released evaluator | Hardened | 6 | 0 | 0 | 0 |
| Frozen preregistered study | Naive | 0 | 0 | 5 | 90 |
| Frozen preregistered study | Hardened | 0 | 0 | 0 | 0 |
| Later evaluator-correction audit | Naive | 0 | 0 | 0 | 90 |
| Later evaluator-correction audit | Hardened | 0 | 0 | 0 | 0 |

The released evaluator produced ten false failures on equivalent-evidence transitions: four in the
naive arm and six in the hardened arm. In every case, the replay cited declared equivalent support
plus valid retained context. The released gate incorrectly conditioned all replay citations on the
stochastic baseline citation set. The frozen study gate required an unchanged verdict, citations
confined to the current packet, and at least one declared equivalent-support citation; all ten then
passed. The exact cases and source-record digests are in the
[equivalent disagreement audit](validation/pilot/equivalent_disagreement_audit.csv).

The native evaluator also flagged five naive support-removal responses. The frozen study analysis
preserved those native flags. A later evaluator-correction audit found that all five retained only
permitted context claims rather than the canonical claim, and reclassified them as evaluator false
positives. Accordingly, “five support-removal failures” is accurate only as a native/frozen flag
count; it is not the later corrected behavioral result. The five-case audit is embedded in the
[corrected study summary](validation/pilot/corrected_study_analysis_summary.json).

The preregistered study gate was applied offline to the original structured records, and no full
model rerun occurred after the later product correction. Native results remain available in a
separate [machine-readable summary](validation/pilot/native_released_evaluator_summary.json).

## Scope, data, and definitions

- A run is one fixture, arm, and replicate evaluated in baseline, equivalent, distractor,
  support-removed, and no-evidence states.
- A prompt pair is the naive and hardened run for the same fixture and replicate; all 90 pairs are
  complete.
- An abstention is `verdict == insufficient_evidence` in the no-evidence response.
- The strict empty-claims contract additionally requires empty claims and citations with
  insufficient evidence sufficiency.
- Replicate inconsistency is defined on the frozen run-level primary endpoint: one or two failures
  among three replicates for a fixture-arm. The observed count is zero. This does not assert
  byte-identical responses or transition-level consistency.
- Fixtures are correlated, purposively constructed synthetic clusters. They are not statistically
  independent samples from a real-policy population.

The full operational definitions and exclusions are in
[METHODOLOGY.md](validation/pilot/METHODOLOGY.md). The
[fixture manifest](validation/pilot/fixture_manifest.csv) and
[run manifest](validation/pilot/run_manifest.csv) expose the exact sanitized grid.

## Version and preregistration evidence

The study was locally preregistered and Git-frozen before execution. Its root freeze commit was
`bf56bb34c4b1a1d1c301fbc8ff2d0be795a8d6b8` at `2026-07-18T09:46:25-07:00`. A preflight bound that
commit and the frozen manifest before the first call artifact. This was not an external registry or
trusted timestamp service; the chronology relies on local Git and filesystem metadata plus
cryptographic digests.

The evaluated ReplayGuard package was version `0.1.0` at commit
`d0dc3637a14b06bf16d6dc930d700116f38f8175`. Its evaluator-module SHA-256 is
`93c3c663c01e35a09d211dea79d92f5df1b7bdb9ea06adac62de3ecfda9b433c`. At the public audit start,
the public evaluator module matched those bytes, but the complete public source tree was not
byte-identical on every evaluated path. The later evaluator correction was also absent from public
source. Exact safe bindings and the one source-path difference are recorded in
[evaluated_version.json](validation/pilot/evaluated_version.json).

## Offline verification

No credential, model call, or private response record is needed to verify the committed package:

```bash
python scripts/validate_pilot_package.py
```

The validator checks package hashes, the full fixture-arm-replicate grid, call arithmetic, all
headline counts, native/corrected separation, the exact ten-case equivalent disagreement set, and
forbidden-data patterns. See the [package README](validation/pilot/README.md) and
[claim-evidence matrix](validation/pilot/CLAIM_EVIDENCE_MATRIX.md).

## Limitations and nonclaims

- The pilot is exploratory and uses a purposively constructed, assistant-aided synthetic fixture
  bank. It does not establish population-wide external validity.
- Replicates within a fixture are correlated. The 30 fixtures, not the 90 replicate rows per arm,
  are the analysis clusters.
- The preregistration has a coherent local Git-and-hash chain but no external timestamp authority.
- Review was role-separated and internal; no independent-human adjudication ledger is claimed.
- Aggregate records and digests permit count and lineage checks, but private model response bodies
  are deliberately excluded, so the public package does not enable a full semantic re-adjudication.
- The study does not measure retrieval quality, concurrency, production latency, other model
  families, or current-code performance.
- The later evaluator correction is documented as an audit layer; this package does not claim that
  current public product code contains that correction.

## Judge evidence index

- [Judge quickstart](JUDGE_TEST.md)
- [Deterministic brittle example](reports/examples/brittle/index.html)
- [Deterministic clean example](reports/examples/clean/index.html)
- [Pilot summary](#technical-summary)
- [Pilot package README](validation/pilot/README.md)
- [Methodology](validation/pilot/METHODOLOGY.md)
- [Native released-evaluator summary](validation/pilot/native_released_evaluator_summary.json)
- [Corrected study analysis](validation/pilot/corrected_study_analysis_summary.json)
- [Equivalent disagreement audit](validation/pilot/equivalent_disagreement_audit.csv)
- [Artifact manifest](validation/pilot/artifact_manifest.json)
- [Offline validation](#offline-verification): `python scripts/validate_pilot_package.py`
- [Limitations and nonclaims](#limitations-and-nonclaims)
