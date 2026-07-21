# Self-authored demo fixtures

These fixtures are self-authored for ReplayGuard. They contain fictional policies, products, and
organizations. No external dataset or third-party text is included.

Each fixture hand-authors the baseline packet, equivalent replacement, distractor, and the exact
non-supporting baseline document IDs retained after decisive support is removed. The no-evidence
packet is always constructed deterministically as empty. GPT-5.6 does not generate the demo
interventions.

Fixture schema v1.0 treats the target's `verdict` as its disposition toward the supplied
`claim_under_test`. Answer text and `material_claims` remain human-readable and may be paraphrased.
Generic `confidence` describes the current response/verdict, so confidence deltas across different
verdict classes are diagnostic. Support-removal gates use disposition, evidence sufficiency,
surviving support, material-claim persistence, and packet-local citations.

- `clean_policy.yaml` — all four contracts pass.
- `distractor_flip.yaml` — the target reverses after an irrelevant note is added.
- `unsupported_persistence.yaml` — the target preserves an affirmative claim after support disappears.
- `demo_brittle.yaml` — the three-failure path used in the three-minute demo.

The fixtures are distributed under the repository's PolyForm Noncommercial License 1.0.0.
