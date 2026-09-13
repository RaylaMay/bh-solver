# Pre-DW1 compatibility fixtures

These fixtures were captured from the working implementation on 2026-09-11,
before the DW1 application-service extraction. They are regression evidence,
not an approval of the reference scientific models. Do not regenerate them to
make a refactor pass; investigate any change and record an approved contract
change where needed.

`manifest.json` records the original implementation file hashes and SHA-256
digests for each canonical artifact. Each canonical JSON file contains exactly
the bytes returned by the existing serializer, with no trailing newline.

The three request sets cover:

- `baseline`: the existing `tests/test_api.py::draft_payload` thermal loop.
- `units_extensions`: affine temperature, non-SI input units, the `fraction`
  alias, absent handles, a pre-existing base-case ID, presentation extensions,
  Unicode labels, and a node ID requiring the existing sanitization behavior.
- `splitter`: both outlet handles and fractional mass-flow distribution.

Each HTTP trace covers save/open/validate/run, another explicit Run, transient
result normalization, a presentation revision, missing drafts, mismatched IDs,
an unconnected input and an invalid handle. HTTP status codes, aliases, messages,
metrics, fixture warnings and all response fields are retained. Only generated
`updatedAt`, `completedAt` and `runId` values are replaced with fixed values;
their original formats and distinct run identities are checked before replacement.

Each scenario also has case, revision, compiled and run canonical artifacts.
Only the generated run ID and run creation timestamp are replaced. Stable IDs,
the case hash, compiled identity, quantity representations, diagnostics,
provenance and four independent result states are unchanged.

The three CLI fixtures preserve exact standard-output JSON, and
`public_exports.json` records the package's ordered public symbols and their
original defining modules.
