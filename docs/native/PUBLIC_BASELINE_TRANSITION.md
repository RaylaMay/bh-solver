# Public baseline transition — 2026-09-13

Status: **CURRENT PUBLIC BASELINE VERIFIED; HISTORICAL EVIDENCE QUALIFIED**.
Author: Rayla May. Rayla May instructed the project to establish the renamed
project's verification baseline before DW3, preserving her branding, ownership
and licence work.

The current public baseline is `677d7492fc9daaf2df3b050b1a1425df5856e5a3`,
matching the local `origin/main` reference after Rayla May's identity scrub.
The remote history now uses Rayla May's author and committer metadata.

The [baseline manifest](evidence/public-baseline-2026-09-13/baseline.json) hashes
the 184 files in that Git tree. It records the public `bh_sim` package, `.bh`
runtime naming, BH application identity and the adopted root licence as they
exist now. Private files absent from the public Git tree are not copied into the
baseline or CI inputs. Rayla May's reported pre-publication changes are context;
the manifest independently establishes only the committed bytes available now.

## Historical evidence qualification

The DW0, DW1, DW2 and DW2 macOS records under `docs/native/evidence` are historical
records. Public sanitization changed text in records, paths, patches, manifests,
the startup trace and witness ledger, as well as implementation/documentation.
Their surviving pre-transition hashes do not authenticate those rewritten bytes.
Treat these as **sanitized historical records, not original raw captures**.
Existing image files are preserved as found; this work does not certify their
pre-publication provenance or claim a new native walkthrough from them.

The [historical checker output](evidence/public-baseline-2026-09-13/historical-check.txt)
records expected mismatches. Rewriting its old hashes to make it pass would obscure
the transition, so historical files remain unchanged. Pre-sanitization originals
cannot be reconstructed from the current public root commit. The new manifest
authenticates their current public bytes without backdating that claim.

## Current verification and limitations

[Exact commands and outcomes](evidence/public-baseline-2026-09-13/verification.txt):
100 Python tests and 5 browser tests passed; Ruff and Pyright passed; web lint,
production build, Python source distribution and wheel build passed. The Python
suite retains one upstream Starlette deprecation warning. The initial wheel build
needed approved access to uv's existing cache; the retry passed.

This baseline does not infer a post-rename native Launch Services walkthrough,
scientific model approval, complete accessibility, performance or release
acceptance from software tests. DW3 has its own measurements and evidence.
Local paths in new text logs are replaced by `<checkout>` and explicitly marked
as sanitized; they are not described as raw output.

## Scope, consequences and rollback

No implementation, canonical schema, numerical model, dependency lock, licence
or Rayla May material changed to establish this baseline. Subsequent DW3 changes are
reviewed against this commit. Git provides the durable before-state; rollback
must preserve newer edits by Rayla May and all `.bh` drafts. Do not use a broad clean or
reset. A new public-tree checker validates this baseline against Git objects,
while checking current document links separately, so later legitimate work does
not invalidate historical evidence merely by changing the working tree.

References: ADR-002, ADR-005, ADR-010, UIX-DOC-001, CORE-002 and Rayla May's
explicit public-transition and DW3 instructions. No licence decision by Rayla May is
reopened. New software/model/release gates require their own evidence.
