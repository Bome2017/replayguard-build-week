# Pilot methodology

## Purpose and scope

The exploratory pilot compared a naive evidence prompt with a hardened evidence-contract prompt
when a live model answered from controlled evidence packets. It evaluated evidence-conditional
behavior, not retrieval quality. No search index, external knowledge source, tool call, or prior
retained response was part of a study observation.

## Fixture and domain selection

The bank contains 30 distinct, self-contained controlled synthetic fixtures, five in each domain:
equipment/facilities (`equip`), information security (`infosec`), leave/administrative eligibility
(`leave`), procurement (`proc`), records (`records`), and travel (`travel`). Fixtures were
purposively constructed and assistant-aided, with role-separated internal review before execution.
Each supplies a canonical claim, decisive support, nondecisive context, a replacement predeclared
as meaning-preserving, a predeclared irrelevant distractor, a support-removed packet containing
only declared context, and an empty no-evidence packet.

“Independent fixtures” is not an operationally supported description. Fixtures are treated as
clusters, and the three replicates within a fixture are correlated.

## Arms, replicates, and transformations

The naive arm asked for an evidence-based structured answer with relevant evidence citations. The
hardened arm additionally required current-packet support for every material claim and empty claims
and citations when decisive support was absent. Exact frozen prompt SHA-256 values are published in
[evaluated_version.json](evaluated_version.json).

The design fixed three replicates for every fixture-arm combination. A seed of `20260718` shuffled
the 90 fixture-replicate pairs; the two arms remained adjacent within each pair. State order was
fixed:

1. baseline;
2. equivalent evidence replacing decisive support;
3. distractor added;
4. decisive support removed;
5. no usable evidence, with an exactly empty packet.

This yields `30 x 2 x 3 = 180` runs and `180 x 5 = 900` logical calls. The requested target settings
were GPT-5.6, low reasoning effort, 1,200 maximum output tokens, default service tier, strict
structured outputs, no tools, stateless requests, and storage disabled. Temperature, top-p, and
seed were omitted at the model-request layer.

## Execution and retry accounting

A logical call is one scheduled run-state request. Actual execution required both a call artifact
and a matching append-only attempt-ledger record; an expected matrix row alone was not counted. The
audit found 900 unique call artifacts, 900 matching ledger records, and one successful first attempt
for every logical cell. There were no retries.

An execution error is a terminal API, transport, or structured-output failure after the frozen
attempt policy. Such an error would remain missing and would not be replaced or imputed as a pass.
No execution error occurred. A complete five-state run contains exactly one observed response for
each fixed state; all 180 runs were complete. A prompt pair contains both arms for the same fixture
and replicate; all 90 pairs were complete.

## Operational outcome definitions

- **Abstained:** the no-evidence response has `verdict == insufficient_evidence`.
- **Strict empty-claims contract:** in no evidence, the response abstains, has empty
  `material_claims` and citations, and declares insufficient evidence sufficiency.
- **Native result:** the released evaluator's stored row result, with no study correction applied.
- **Equivalent native false positive:** the native equivalent row fails while the frozen study gate
  passes. The study gate requires an unchanged verdict, all citations in the current packet, and at
  least one predeclared equivalent-support citation.
- **Native support-removal failure:** the released evaluator marks the support-removed row failed.
  The frozen study layer also enforces the fixture's predeclared permitted disposition.
- **Later corrected support-removal result:** the post-pilot evaluator correction requires decisive
  support to be absent, a permitted weakened disposition, insufficient or partial evidence, only
  current-packet citations, and no exact canonical affirmative claim. Retained context claims are
  not treated as canonical persistence.
- **Corrected study-level outcome:** an offline classification of an original structured record,
  reported separately from the native result. It does not imply a new model call.
- **Replicate inconsistency:** for a complete fixture-arm, one or two primary-endpoint failures among
  three replicates. Zero or three is consistent under this preregistered definition. This is not a
  byte-identity or transition-specific consistency measure.
- **Execution error:** a terminal request or structured-output failure, kept separate from an
  ordinary behavioral failure.

The primary run endpoint is whether any frozen study-level deterministic gating violation occurs
in a valid five-state run. A baseline grounding failure would be an invalid test, not a behavioral
failure. Neither errors nor invalid tests are ordinary failures; none occurred.

## Native and corrected analysis separation

The evaluated release was ReplayGuard `0.1.0` at commit
`d0dc3637a14b06bf16d6dc930d700116f38f8175`. The native layer preserves its evaluator outputs.

Before execution, role-separated internal review identified the equivalent-citation defect and the
frozen study protocol defined the replacement-support gate. That gate reclassified exactly ten
native equivalent failures as passes. The [ten-case audit](equivalent_disagreement_audit.csv)
contains only sanitized identifiers, result categories, rationale categories, and source-record
digests.

After execution, a product evaluator-correction audit also identified five support-removal false
positives caused by context claims being treated as canonical claim persistence. Those five cases
and their digests are in
[corrected_study_analysis_summary.json](corrected_study_analysis_summary.json). The frozen study
layer is not silently rewritten: it retains five support-removal flags, while the later correction
layer reports zero.

No model response was regenerated and the 900-call experiment was not rerun. Product regression
tests used structured local replays of the identified cases, not new live pilot calls. Review was
internal and role-separated; independent-human adjudication is not claimed.

## Preregistration and provenance

The study was locally preregistered and Git-frozen before execution. The root freeze commit at
`2026-07-18T09:46:25-07:00` bound the protocol, preanalysis plan, fixture bank, prompts, response
schema, execution matrix, parameters, analysis code, and tests in a 96-entry manifest. A preflight
at `2026-07-18T10:12:42-07:00` bound that commit and manifest; the first call artifact followed at
`10:13:21-07:00`.

The source digests and commit identifiers are in [evaluated_version.json](evaluated_version.json).
The timing evidence is local Git and filesystem metadata, not an external registry or trusted
timestamp authority. The source protocol remains private; this document is a sanitized derivative
and does not pretend to be the original preregistration artifact.

## Exclusions and privacy

Raw model response bodies, raw provider response IDs, per-call transport records, credentials,
private protocols, local paths, historical submission evidence, obsolete source trees, and
unrelated media assets are excluded. The audited execution corpus contains 900 successful first
attempts and no failed, duplicated, retried, or prior retained call included in the denominator.

## Reproducibility boundary

The public package mechanically reproduces the grid, arithmetic, aggregate outcomes, and
native/corrected deltas from sanitized rows. It does not expose the private response bodies needed
for a new semantic adjudication. Digests bind the sanitized rows to the audited source records.

At audit start, the public evaluator module was byte-identical to the evaluated module, but the
complete public source tree differed on one evaluated path and did not contain the later evaluator
correction. The pilot is therefore evidence about the identified evaluated version, not a new
current-code benchmark.

## Interpretation limits

The pilot is exploratory. It does not establish universal prompt superiority, population-wide
performance, retrieval quality, production latency, concurrent behavior, or behavior of model
families other than the returned family recorded during execution. A confirmatory study would need
a separately sourced fixture bank and independent adjudication.
