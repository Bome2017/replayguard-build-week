# Judge testing instructions

ReplayGuard is a Python 3.11+ developer tool. The commands below use a POSIX shell and are exercised
by the public Linux CI workflow; Windows activation differs and is not acceptance-tested.
The public repository is
[Bome2017/replayguard-build-week](https://github.com/Bome2017/replayguard-build-week).

## 30-second no-install path

1. Download and open the committed
   [intentionally brittle HTML report](reports/examples/brittle/index.html).
2. Expand **Distractor added** and **Decisive support removed** to inspect the failed rules.
3. Optionally compare the [clean HTML report](reports/examples/clean/index.html).
4. Inspect the adjacent machine-readable
   [brittle result](reports/examples/brittle/result.json) and
   [clean result](reports/examples/clean/result.json).

Both HTML files are self-contained: their styles and report data are embedded, they make no
network requests, and they need no server, API key, account, or model call. The committed files
were generated from the current public source in deterministic mode. They are judge examples,
not live-model validation.

## Validation evidence

The exploratory live-model pilot is documented in the
[pilot validation summary](PILOT_VALIDATION.md) and the
[pilot package README](validation/pilot/README.md). Judges can inspect:

- the [native released-evaluator summary](validation/pilot/native_released_evaluator_summary.json);
- the [corrected study analysis](validation/pilot/corrected_study_analysis_summary.json);
- the [exact ten-case equivalent disagreement audit](validation/pilot/equivalent_disagreement_audit.csv);
- the [evaluated-version binding](validation/pilot/evaluated_version.json); and
- the [sanitized run manifest](validation/pilot/run_manifest.csv).

Validate every committed headline count offline from the repository root:

```bash
python scripts/validate_pilot_package.py
```

The deterministic product examples above require no API key. The pilot involved 900 live model
calls, but its committed validation package is sanitized and entirely offline; judges do not need
to rerun those calls. Native released-evaluator results, the preregistered study gate applied
offline to the original records, and the later product-evaluator correction are separate layers.
No full model rerun occurred after the later product correction.

## Two-minute deterministic runnable path

```bash
git clone https://github.com/Bome2017/replayguard-build-week.git
cd replayguard-build-week
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install -e . --no-deps

replayguard test fixtures/clean_policy.yaml \
  --analysis-mode deterministic \
  --output reports/judge-clean
clean_exit=$?

set +e
replayguard test fixtures/demo_brittle.yaml \
  --analysis-mode deterministic \
  --output reports/judge-brittle
brittle_exit=$?
set -e

test "$clean_exit" -eq 0
test "$brittle_exit" -eq 1
```

The clean target must exit `0`. The intentionally brittle target must exit `1`; that exit is the
product reporting brittleness, not a crash. Exit `2` means the fixture, target execution, or a
required analysis step failed.

## Optional model-backed path

Use the judge's own `OPENAI_API_KEY` and require the model rather than allowing fallback:

```bash
export OPENAI_API_KEY="your-key"
set +e
replayguard test fixtures/demo_brittle.yaml \
  --analysis-mode model \
  --output reports/judge-model
model_exit=$?
set -e
case "$model_exit" in
  1) echo "Expected brittle finding from a completed model assessment" ;;
  2) echo "Fail-closed model/fixture error; inspect stderr" >&2 ;;
  *) echo "Unexpected model-mode exit: $model_exit" >&2; exit 1 ;;
esac
```

When the semantic assessment succeeds and accepts the fixture contracts, the brittle fixture exits
`1`; its completed result records the returned response ID and model metadata in
`reports/judge-model/result.json`. Exit `2` is fail-closed for a required-model, fixture, target, or
invalid-test error and can occur before report creation. ReplayGuard sends one batched structured
assessment with `store=False` and repeats that application-level structured-output attempt once
only if the first output is unparsed or schema-invalid. The SDK may separately retry eligible
transport failures under its configured policy. ReplayGuard does not serialize the API key itself.
The repository does not commit model-mode output or a returned response ID.

## Exact resource use

- Every fixture using the local sample target executes that target exactly five times: baseline
  plus four replays. A custom HTTP target instead receives five target requests.
- Deterministic analysis makes zero OpenAI model-assessment requests. With the local sample target,
  it makes no network request.
- After five successful target executions, model analysis makes one batched application-level
  assessment attempt and repeats the same structured-output attempt at most once if the first is
  unparsed or schema-invalid. The SDK controls any lower-level retry of eligible transport
  failures.
- Every completed run writes two files in the selected output directory: `index.html` and
  `result.json`. Some exit-`2` errors occur before report creation.
- After cloning and installing the pinned dependencies, deterministic mode requires no database,
  web server, API key, account, container, or paid service.

## Troubleshooting

- `replayguard: command not found`: activate `.venv` and rerun both installation commands.
- Exit `2` with `OPENAI_API_KEY is not set`: use deterministic mode or export the judge's own key.
- Exit `2` with target execution errors: verify the target URL and ReplayGuard custom JSON
  response contract; the committed sample fixtures do not need an external target.
- Custom JSON HTTP target timeout: set `REPLAYGUARD_HTTP_TIMEOUT_SECONDS` to a value greater than
  `0` and no more than `300`.
- Windows uses a different virtual-environment activation command and is not acceptance-tested
  for this MVP.
