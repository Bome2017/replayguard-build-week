# ReplayGuard implementation plan

Date: 2026-07-17
Scope: OpenAI Build Week qualifying work only.

## Product slice

Build one local-first metamorphic CI runner that:

1. loads a compact YAML fixture;
2. creates baseline, equivalent-evidence, distractor, support-removed, and no-evidence cases;
3. executes a target adapter against every case;
4. optionally asks GPT-5.6 for one structured semantic assessment of the run;
5. applies deterministic transition and citation rules;
6. writes stable JSON and a judge-readable HTML transition report;
7. exits `0` only when every required contract passes.

## Implementation order

1. Schemas and fixture validation.
2. Deterministic perturbation construction.
3. Sample targets and a custom JSON HTTP target adapter using ReplayGuard's request/response
   contract.
4. GPT-5.6 structured semantic assessment with reproducibility metadata.
5. Deterministic verdict engine.
6. CLI, JSON artifact, and HTML report.
7. Passing and deliberately brittle fixtures.
8. Tests, clean-install verification, demo script, and submission checklist.

## Mandatory vertical-slice kill gate

Do not expand to more adapters, hosted deployment, benchmark datasets, or generalized repository auditing until one fixture runs all four replay contracts end to end and produces a visible brittle result.

Mandatory completion means: one hand-authored fixture, one target adapter, one deliberately
brittle target, one GPT-5.6 semantic assessment, deterministic final verdicts, one CLI command,
one readable transition report, correct CI exit status, and core verdict tests.

After that vertical slice, stretch work proceeds only in this order: report polish, a compliant
comparison target, additional self-authored fixtures, and additional adapters. Model-generated
perturbations remain experimental and are not part of the deterministic demo foundation.

## Isolation

This repository is the canonical qualifying submission repository. Historical
evidence-replay research is read-only input context and stays frozen. No private workspace material
is included in this repository.
