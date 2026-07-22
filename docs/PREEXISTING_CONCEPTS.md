# Pre-existing concepts and Build Week boundary

## What predates Build Week

Before the OpenAI Build Week submission period, the author had private research notes exploring
controlled evidence replay and brittleness. The following conceptual ingredients predate this
repository:

- test answer invariance when evidential meaning is preserved;
- test answer sensitivity when decisive support is removed;
- use equivalent evidence, distractor evidence, support removal, and no-evidence interventions;
- distinguish a brittle target from an invalid intervention.

Those notes were research material, not a distributable developer product. They are not included
in this repository, imported at runtime, or required to install or test ReplayGuard.

## What was implemented during Build Week

The following qualifying work was implemented during the submission period:

- the strict fixture schema and hand-authored perturbation format;
- deterministic perturbation construction and validation;
- the target-adapter interface, custom JSON HTTP adapter, and sample targets;
- the deterministic transition-verdict engine and CI exit contract;
- GPT-5.6 Structured Outputs for normalized claims, citation mapping, transition analysis, and
  failure explanation;
- versioned JSON output, structured logs, and the responsive HTML transition report;
- self-authored demonstration fixtures, automated tests, packaging, installation instructions,
  CI, judge instructions, and submission materials.

No private corpus, portfolio analysis, audit material, or unrelated workspace code is part of
the submission.

## Provenance evidence

The core implementation was produced in one timestamped Codex task during Build Week.
This is the canonical submission repository. The Codex `/feedback`
session ID for the build task and this changelog are the primary evidence of when the core
functionality was built; repository history begins with the canonical submission commit and is not
represented as predating that work.
