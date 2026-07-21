# ReplayGuard

**Metamorphic regression testing for evidence-grounded AI systems.**

ReplayGuard detects when an evidence-grounded AI system changes its answer even though the
evidence has not materially changed—or refuses to change after the supporting evidence
disappears.

Unlike pointwise evaluators that score one answer in isolation, ReplayGuard tests behavior across
controlled metamorphic evidence transitions.

It does not require a perfect gold answer for every replay. It tests whether the relationship
between outputs is correct under four controlled evidence transformations:

| Replay | Evidence intervention | Required behavior |
| --- | --- | --- |
| Equivalent evidence | Replace decisive support with a declared semantic equivalent | Stay stable and cite equivalent support |
| Distractor added | Add plausible, non-dispositive evidence | Stay stable and ignore the distractor |
| Decisive support removed | Remove all declared support for the claim | Weaken, change, or abstain |
| No usable evidence | Send an empty evidence packet | Abstain and declare insufficiency |

The top-level verdict is deterministic. GPT-5.6 performs a structured semantic assessment
inside those guardrails and every check is labeled `deterministic` or `model_assisted`.

## One-minute demo

Requires Python 3.11 or newer.

```bash
cd replayguard-build-week
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install -e . --no-deps

export OPENAI_API_KEY="your-key"
replayguard test fixtures/demo_brittle.yaml \
  --analysis-mode model \
  --output reports/demo
```

The intentionally brittle target returns exit code `1`, writes
`reports/demo/result.json`, and generates `reports/demo/index.html`. The expected result is one
passing invariance contract and three visible brittleness failures. Open the HTML report and
expand any failed row to see the answers, changed evidence, unsupported claims, orphaned
citations, and exact failed rule.

To prove the green path:

```bash
replayguard test fixtures/clean_policy.yaml \
  --analysis-mode model \
  --output reports/clean
echo $?  # 0
```

For an offline smoke test, use `--analysis-mode deterministic`. `auto` uses GPT-5.6 when
`OPENAI_API_KEY` is present and records a warning when it falls back. `model` fails closed with
exit code `2` when the required model assessment cannot run.

Generated reports are local runtime outputs and are excluded from source control. Each
`index.html` is self-contained and can be opened directly without a server, CDN, or external
assets.

## What a run does

```text
strict YAML fixture
      |
      v
deterministic perturbation builder + malformed-variant checks
      |
      v
target adapter (explicit evidence packet -> structured response)
      |
      +--> one GPT-5.6 structured semantic batch
      |    (equivalence, claim/citation support, concise explanation)
      v
deterministic transition engine
      |
      +--> result.json (stable schema)
      +--> index.html (transition matrix + expandable rule trace)
      +--> process exit code (0 pass, 1 brittle, 2 invalid/error)
```

The core package is intentionally small:

- `models.py` — strict Pydantic fixture, adapter, result, and model-output contracts.
- `perturbations.py` — deterministic construction and validation of all four replays.
- `adapters.py` — sample demo targets and a custom JSON HTTP adapter boundary.
- `analysis.py` — one batched GPT-5.6 Responses API structured-output call.
- `verdicts.py` — deterministic invariance and sensitivity gates.
- `report.py` and `templates/` — machine-readable JSON and a single-file HTML report.
- `cli.py` — CI-oriented command, summary, report path, and exit code.

## Why GPT-5.6 is material

ReplayGuard sends the baseline output and all four replay packets to GPT-5.6 in one structured
Responses API request. The model must return exactly one typed assessment per replay. It checks:

- whether equivalent and distractor transformations preserve their semantic contract;
- whether paraphrased answers and material claims remain semantically aligned;
- whether citations resolve to evidence in the packet;
- which claims persist without support; and
- a concise explanation for the report.

A high-confidence finding that an equivalent/distractor perturbation is malformed invalidates
the test instead of blaming the target. Semantic claim analysis is labeled model-assisted and
kept advisory for differences in human-readable claim prose. The code—not GPT-5.6—enforces the
final allowed verdict transitions, citation IDs, support removal, abstention, result category, and
exit status. Confidence delta remains visible as a diagnostic when a replay changes verdict class.

For reproducibility, `result.json` records the requested and returned model, reasoning effort,
response ID, token usage, prompt version, prompt SHA-256, fixture SHA-256, package version, and
analysis mode. Requests use `store=False`; secrets and the API key are never written to output.

The implementation follows OpenAI's current guidance to use the Responses API for GPT-5.6 and
the SDK's Pydantic structured-output parser:
[GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/latest-model) and
[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

## Fixture format

Fixtures are strict YAML. Unknown keys, duplicate evidence IDs, missing decisive support,
incomplete equivalence maps, support-labeled distractors, or incomplete output contracts fail
closed before the target is scored.

```yaml
schema_version: "1.0"
id: approval_limit
title: Approval-limit contract
question: Can a team lead approve a $500 purchase without director review?
claim: A team lead may approve an equipment purchase of up to $500 without director review.

evidence:
  baseline:
    - id: threshold
      role: support
      decisive: true
      supports_claim: true
      text: Team leads may approve equipment costing $500 or less.
    - id: submission-process
      role: context
      text: Approved purchases are entered in the asset register.
  equivalent:
    - id: threshold-restated
      role: support
      decisive: true
      supports_claim: true
      equivalent_to: threshold
      text: Director review is unnecessary for team-lead equipment approvals at or below $500.
  distractor:
    - id: color-note
      role: distractor
      text: Dark-gray equipment is preferred when available.

perturbations:
  equivalent: true
  distractor: true
  support_removed: true
  support_removed_retain_ids: [submission-process]
  no_evidence: true

target:
  adapter: sample
  behavior: compliant

output_contract:
  required_fields: [verdict, answer, material_claims, citations, confidence, evidence_sufficiency]
  allowed_verdicts: [supported, refuted, insufficient_evidence, mixed]

assertions:
  expected_baseline_verdict: supported
  minimum_confidence_drop: 0.20
  require_resolved_citations: true
  require_no_claims_without_evidence: true
```

In schema `1.0`, `confidence` means confidence in the current response and verdict. Values are not
directly comparable across different verdict classes. `minimum_confidence_drop` is retained as a
diagnostic report reference for support-removal transitions; it does not override a correct change
from `supported` to `insufficient_evidence`. A gating confidence rule would require an unambiguous
same-proposition confidence contract.

See [`fixtures/README.md`](fixtures/README.md) and the four self-authored fixtures. The fixture
text is fictional and covered by this project's PolyForm Noncommercial License 1.0.0; no third-party benchmark is
required.

## Custom JSON HTTP target contract

Use the built-in sample adapter for deterministic demos, or point the CLI at an endpoint that
implements ReplayGuard's custom JSON request/response contract:

```bash
replayguard test fixtures/clean_policy.yaml \
  --target http://localhost:8000/answer \
  --output reports/http-target
```

ReplayGuard sends `POST application/json` with:

```json
{
  "question": "...",
  "claim_under_test": "...",
  "evidence": [{"id": "doc-1", "text": "..."}],
  "output_schema": {},
  "metadata": {"test_id": "approval_limit", "replay": "baseline"}
}
```

The target must return JSON matching:

```json
{
  "verdict": "supported",
  "answer": "A paraphrased human-readable answer is allowed.",
  "material_claims": ["Human-readable claims may also be paraphrased."],
  "citations": ["doc-1"],
  "confidence": 0.93,
  "evidence_sufficiency": "sufficient"
}
```

`claim_under_test` is the fixture's canonical claim, and `verdict` is the target's structured
disposition toward it. ReplayGuard does not require the human-readable `answer` or
`material_claims` to repeat that claim exactly. Baseline validity requires the expected verdict,
resolving citations, and at least one citation to declared support. Equivalent and distractor
invariance use the unchanged verdict and citation contracts; claim-prose comparison is advisory.

For support removal, deterministic gates require the decisive support to be absent, a permitted
weakened disposition with insufficient or partial evidence sufficiency, no persisted canonical
affirmative claim, and citations confined to the current packet. A response that remains
`supported` without surviving support, cites removed evidence, or explicitly retains the canonical
claim is brittle regardless of confidence. Confidence delta is reported but non-gating when the
verdict class changes.

This behavior uses schema version 1.0 and does not add fields to the request/response shape above.

Allowed verdicts are `supported`, `refuted`, `insufficient_evidence`, and `mixed`. Citation values
are evidence document IDs. Set `target.api_key_env` in the fixture to the *name* of an environment
variable when the endpoint requires a bearer token. The token value is never serialized. The
adapter interface is typed so local-callable and shell adapters can be added without changing the
verdict engine.

## Configuration

Copy `.env.example` values into your shell or preferred secret manager; ReplayGuard does not
load `.env` files automatically or commit credentials.

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | unset | Required by `--analysis-mode model` |
| `REPLAYGUARD_MODEL` | `gpt-5.6` | Semantic-assessment model |
| `REPLAYGUARD_REASONING_EFFORT` | `low` | Explicit reasoning effort |
| `REPLAYGUARD_HTTP_TIMEOUT_SECONDS` | fixture value / `30` | HTTP target timeout, maximum 300 |
| `REPLAYGUARD_LOG_LEVEL` | `WARNING` | Package log threshold |
| `REPLAYGUARD_LOG_FORMAT` | `json` | `json` or text logs |

Add `--verbose` to emit one JSON log event per run/case to stderr while preserving the
human-readable terminal result on stdout.

## CI behavior

Exit codes are part of the contract:

- `0` — the valid baseline and all four replay contracts passed;
- `1` — at least one valid replay was brittle;
- `2` — invalid fixture/comparison, target execution failure, or required model failure.

Minimal shell gate:

```bash
replayguard test fixtures/clean_policy.yaml \
  --analysis-mode model \
  --output reports/ci
```

Archive both `reports/ci/result.json` and `reports/ci/index.html` as CI artifacts.
The included [GitHub Actions workflow](.github/workflows/ci.yml) runs the pinned install, tests,
lint, the green contract, and the expected brittle exit on every push and pull request.

## Development and verification

```bash
python -m pytest
ruff format --check src tests
ruff check src tests
```

The test suite covers perturbation construction, clean/brittle exit behavior, paraphrased target
responses across baseline and replay calls, missing verdicts, unrelated claims with unresolved
citations, unsupported support-removal explanations, strict model-call arguments and metadata,
HTTP validation, reports, and CLI output.

### Supported platforms

- Python 3.11 or newer on macOS and Linux.
- The clean acceptance run in this repository was executed on macOS with Python 3.13.
- Windows is not yet acceptance-tested. The package code is OS-neutral, but the documented shell
  commands use POSIX activation syntax.

## Current scope

**Implemented MVP**

- All four controlled replay types, deterministic final verdicts, and fail-closed fixtures.
- Invariance and sensitivity checks across verdicts, claims, citations, surviving support, and
  evidence sufficiency, with confidence delta retained as a diagnostic.
- Meaningful GPT-5.6 structured semantic analysis with recorded reproducibility metadata.
- Custom JSON HTTP target adapter plus compliant and deliberately brittle local sample behaviors.
- Human-readable CLI, stable JSON, polished responsive HTML, structured logs, and CI exit codes.
- Four fictional, self-authored fixtures and automated tests.

**Experimental**

- GPT-5.6 semantic equivalence and malformed-perturbation judgments. They are typed and bounded,
  but semantic adjudication remains model-dependent and should be reviewed for high-stakes use.

**Future extensions (not implemented)**

- Local Python-callable and shell-command adapters.
- Model-generated perturbations with independent factual-preservation validation.
- Multi-claim evidence graphs, batch fixture execution, and hosted report aggregation.

## Known limitations and failure modes

- Fixture authors currently supply equivalent evidence and distractors; GPT-5.6 validates rather
  than generates them.
- The HTTP contract treats `verdict` as the disposition toward `claim_under_test`. Human-readable
  answers and material claims may be paraphrased; prose comparison is advisory.
- Generic `confidence` describes the current response/verdict. Cross-verdict confidence deltas are
  diagnostic, not evidence that the original claim persisted.
- Support is declared at document level, not mapped to evidence spans.
- The HTTP adapter expects ReplayGuard's custom JSON request/response boundary; it does not wrap
  OpenAI-compatible or other vendor-specific chat endpoints automatically.
- A fixture with a bad baseline is `invalid_test`; downstream replays are not treated as valid
  brittleness findings.
- `auto` is convenient locally but CI should use `model` when GPT participation is mandatory and
  `deterministic` when a fully offline gate is intentional.
- Model availability, rate limits, invalid credentials, target timeouts, malformed target JSON,
  and unknown citation IDs fail closed or produce explicit warnings according to analysis mode.

## License

ReplayGuard is source-available under the
[PolyForm Noncommercial License 1.0.0](LICENSE) for uses permitted by that license.

Commercial use requires a separate written commercial license. See
[COMMERCIAL-LICENSING.md](COMMERCIAL-LICENSING.md).
