# Build Week changelog

All dates are in the 2026 OpenAI Build Week submission period.

## July 17 — concept boundary and first vertical slice

- Read the private historical evidence-replay README and perturbation-contract notes for concepts
  only; made no changes to those sources.
- Wrote an isolated implementation plan with a stop-before-scope-expansion kill gate.
- Implemented the smallest end-to-end path: one fixture, baseline plus four replays, one sample
  target, deterministic final verdicts, CLI output, JSON, and a visible brittle HTML report.
- Added a required GPT-5.6 semantic-assessment path with typed Structured Outputs and fail-closed
  behavior when the model is unavailable.

## July 17 — hardening and productization

- Added the custom JSON HTTP target boundary, compliant and deliberately brittle behaviors, four
  self-authored fixtures, exact evidence-transition explanations, structured logs, environment
  configuration, pinned dependencies, and CI.
- Added tests for perturbation contracts, verdict rules, missing-model behavior, GPT request
  parameters and metadata, HTTP I/O validation, report generation, and CLI exit codes.
- Verified the pinned install in a second clean virtual environment; clean target exited `0`,
  brittle target exited `1`, required-model-without-key exited `2`.
- Visually checked the report at desktop and mobile widths and confirmed a clean browser console.

## July 17 — standalone-repository correction

- Established this standalone repository as the canonical submission repository.
- Added explicit documentation of pre-existing concepts versus Build Week implementation.
- Made the support-removed replay packet an explicit hand-authored fixture selection.
- Made GPT-5.6 normalized claim extraction and citation mapping explicit in the typed schema, with
  one bounded schema retry before an `execution_error`.
- Confirmed that the canonical repository contains only ReplayGuard product and submission files;
  no private research files are included.

## July 17 — live model acceptance

- Completed the clean and deliberately brittle live model-assisted acceptance runs.
- Verified that both runs used the model successfully on the first structured-output attempt and
  that deterministic ReplayGuard code issued the final verdicts and exit statuses.
- Retained sanitized HTML reports and a public verification summary while keeping raw result JSON
  and full API response IDs private.

## July 17 — HTTP contract compatibility correction

- Corrected a v1.0 evaluator mismatch: valid paraphrased target prose could not satisfy the
  baseline's hidden normalized-exact material-claim gate.
- Removed that redundant prose gate: the existing request already supplies `claim_under_test`, and
  the existing `verdict` is the target's structured disposition toward it.
- Made cross-replay claim-prose differences advisory while keeping verdict transitions, citation
  grounding, support removal, result category, and exit status deterministic. Schema remains v1.0.

## Remaining external acceptance

- Record the Codex `/feedback` session ID.
- Publish or share the existing repository commits after final approval.
- Record and publish the narrated under-three-minute YouTube demo.
