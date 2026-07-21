# Judge testing instructions

ReplayGuard is a Python 3.11+ developer tool. The supported MVP platforms are macOS and Linux.
The canonical submission repository is `/Users/bsm/replayguard-build-week`; after publication its
repository name remains `replayguard-build-week`.

## 30-second path — no build, install, server, or account

1. Download
   [`reports/examples/brittle/index.html`](reports/examples/brittle/index.html).
2. Open it directly in a desktop browser.
3. Read the transition matrix, then expand **Distractor added** and
   **Decisive support removed**.

The file is a self-contained test build: CSS, data, and interactions are embedded; it makes no
network requests and requires no API key. It shows the full judge-facing product experience and
the exact CI exit status. The adjacent `result.json` is the machine-readable artifact.

The committed `reports/examples/` artifacts use deterministic mode. Sanitized live reports under
`reports/final-clean/` and `reports/final-brittle/` add clearly labeled GPT-5.6 semantic checks
without publishing raw API response IDs. Those retained live reports preserve the evaluator version
used when they were generated; current support-removal confidence semantics are exercised offline
by the sanitized retained-output regression corpus.

## Two-minute runnable path — offline

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

replayguard test fixtures/demo_brittle.yaml \
  --analysis-mode deterministic \
  --output reports/judge-brittle
```

Expected exits are `0` for the clean target and `1` for the intentionally brittle target. The
second nonzero exit is the product detecting a regression, not a crash.

## Required-feature path — real GPT-5.6

Set an OpenAI API key in the shell, then require the model rather than allowing fallback:

```bash
export OPENAI_API_KEY="your-key"
replayguard test fixtures/demo_brittle.yaml \
  --analysis-mode model \
  --output reports/judge-model
```

The report should show model-assisted semantic checks and a non-empty model response ID in
`reports/judge-model/result.json`. ReplayGuard sends one structured assessment request with
`store=False`. The key is never serialized.

## Expected resource use

- Five local target executions per fixture: baseline plus four replays.
- One GPT-5.6 Responses API request per fixture in model mode.
- The offline path requires no database, web server, container, account, or paid service; model
  mode makes the single OpenAI API request described above.

## Troubleshooting

- Exit `2` with `OPENAI_API_KEY is not set`: export a key or use deterministic mode.
- Exit `2` with target execution errors: verify the target URL and ReplayGuard custom JSON
  response contract.
- Custom JSON HTTP target timeout: set `REPLAYGUARD_HTTP_TIMEOUT_SECONDS` from `>0` through `300`.
- Windows: use the platform's virtual-environment activation command; Windows has not yet been
  acceptance-tested for this MVP.
