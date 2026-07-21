# Deterministic judge examples

These files were generated from the current public source in deterministic analysis mode.
Regenerate them from the repository root after installing the pinned dependencies:

```bash
replayguard test fixtures/clean_policy.yaml \
  --analysis-mode deterministic \
  --output reports/examples/clean
clean_exit=$?

set +e
replayguard test fixtures/demo_brittle.yaml \
  --analysis-mode deterministic \
  --output reports/examples/brittle
brittle_exit=$?
set -e

test "$clean_exit" -eq 0
test "$brittle_exit" -eq 1
```

The clean fixture must exit `0`. The intentionally brittle fixture must exit `1`; this is the
expected product finding, not a crash. Each directory contains a parseable `result.json` and a
self-contained `index.html` with no external script, stylesheet, image, CDN, or network
dependency.

No API key or model call is required. These are judge examples, not live-model validation.
