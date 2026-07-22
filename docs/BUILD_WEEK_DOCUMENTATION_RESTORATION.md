# Build Week documentation restoration record

Recorded at `2026-07-21T19:55:42-07:00` (`2026-07-22T02:55:42Z`).

- Pre-change public HEAD: `3b07d6e9a50f0a426f2b5b8b907a0f9dfba78328` on `main`.
- Submission deadline used for this audit: `2026-07-21T17:00:00-07:00`.
- This documentation restoration occurred after that deadline. It is not new Build Week
  implementation.

## Historical verification

The last preserved pre-deadline snapshot in the earlier lineage that contains all four restored
items is
`4033af568803e4f35750d6d36e7dc2fb5b0e92a8`, authored by Sanjit Mehat at
`2026-07-21T14:20:25-07:00`. The preserved remote-tracking reflog records that snapshot being
pushed to `origin/main` at `2026-07-21T14:20:53-07:00`, before the deadline.

| Restored path or block | Exact historical source | Verification |
| --- | --- | --- |
| `README.md` — Build Week provenance and Codex collaboration block | `4033af568803e4f35750d6d36e7dc2fb5b0e92a8:README.md`, lines 379–409 | Restored verbatim. The following historical paragraph was not restored because it linked to files absent from the clean public package. |
| `IMPLEMENTATION_PLAN.md` | `4033af568803e4f35750d6d36e7dc2fb5b0e92a8:IMPLEMENTATION_PLAN.md`, blob `402d9a16cf20bf10d8c260c4082113f4ff0cbed0` | Byte-for-byte restoration. This blob was finalized in pre-deadline commit `1cdac1aa393153510896b94bea1ac0d4bc1bc882` at `2026-07-17T22:00:14-07:00`. |
| `docs/PREEXISTING_CONCEPTS.md` | `4033af568803e4f35750d6d36e7dc2fb5b0e92a8:docs/PREEXISTING_CONCEPTS.md`, blob `6fcb548de35f066f23b217dfef99537ac1c11372` | Byte-for-byte restoration. This blob was finalized in pre-deadline commit `1cdac1aa393153510896b94bea1ac0d4bc1bc882` at `2026-07-17T22:00:14-07:00`. |
| `docs/BUILD_WEEK_CHANGELOG.md` | `4033af568803e4f35750d6d36e7dc2fb5b0e92a8:docs/BUILD_WEEK_CHANGELOG.md`, blob `da4dc61cb614fa144ff834b1d033a9ddfab76b31` | Byte-for-byte restoration. This blob was finalized in pre-deadline commit `1cdac1aa393153510896b94bea1ac0d4bc1bc882` at `2026-07-17T22:00:14-07:00`. |

The current public history begins at a separate clean-root publication commit and omitted these
items. No deletion or move commit exists in that lineage, and no equivalent replacement for the
Codex collaboration disclosure or the three provenance documents was present at the pre-change
HEAD.

## Documentation-only changes

Restored material:

- the authenticated README provenance and Codex collaboration block;
- `IMPLEMENTATION_PLAN.md`;
- `docs/PREEXISTING_CONCEPTS.md`;
- `docs/BUILD_WEEK_CHANGELOG.md`.

New records:

- `BUILD_WEEK_EVALUATION_GRANT.md`;
- this restoration record.

`README.md` and `COMMERCIAL-LICENSING.md` also received links to the evaluation grant. The grant
was added solely to make judge access explicit under the current public-license structure. It is
limited to OpenAI, Devpost, the Hackathon administrator, and designated Build Week judges; covers
only access, copying, installation, execution, testing, evaluation, and use reasonably necessary
for judging and verification; and expires at 5:00 p.m. Pacific on August 5, 2026.

Executable code, evaluator logic, tests, fixtures, reports, schemas, pilot data, and research
results were not changed. `LICENSE` was not changed. Prohibited historical license wording was not
restored. No existing Git history was rewritten, and no remote or Devpost submission was changed.

## Pilot terminology review

Historical pilot wording was ambiguous: a count check established 30 distinct fixture IDs, not
statistical independence. The current public pilot package explicitly describes purposively
constructed synthetic clusters and marks the historical independence claim partly contradicted.
The historical five-of-90 support-removal result is preserved as native and frozen evaluator
flags; a separately labeled later correction classifies the same five as evaluator false
positives and reports zero corrected failures. No unresolved contradiction remains in the current
public package, so no pilot artifact or result was edited.
