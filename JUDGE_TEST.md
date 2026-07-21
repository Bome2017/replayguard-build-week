# Judge testing instructions

ReplayGuard is a Python 3.11+ developer tool. The supported MVP platforms are macOS and Linux.
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
test "$model_exit" -eq 1
```

This judge-generated model-mode result records the returned response ID and model metadata in
`reports/judge-model/result.json`. ReplayGuard sends one structured assessment request with
`store=False`; it never serializes the API key. The repository does not commit model-mode output
or a returned response ID.

## Exact resource use

- Every fixture executes the local sample target exactly five times: baseline plus four replays.
- Deterministic mode makes zero model or provider API requests.
- Model mode makes exactly one GPT-5.6 Responses API request per fixture after the five target
  executions.
- Every run writes two files in the selected output directory: `index.html` and `result.json`.
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
