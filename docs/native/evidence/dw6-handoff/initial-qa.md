# Initial package authoring checks

These are observed authoring failures before the frozen release, not DW6 product
results. Recorded 2026-09-16 by Codex.

- Ruff's first authoring pass found formatting/style issues in new package code;
  the formatter was applied only to files created for this package.
- The next Ruff check reported four remaining issues: two long lines, an inverted
  suffix comparison and a unused property expression.
- Pyright reported two issues: a possibly unbound polling variable and a possibly
  absent module `__file__` value.
- Initial verifier challenge run: 8 passed, 1 failed. The candidate-config isolation
  challenge correctly exposed a harness bug: macOS temporary paths can use a
  symlinked prefix, but the import-origin assertion resolved only one side.
  Both sides now resolve before comparison. The check itself was retained.

Final commands and outcomes are recorded separately. These observations do not
claim that missing DW6 application paths have executed.

## Subsequent authoring observations

The first complete 96-test run collected successfully (3 passed, 93 failed), but
88 missing draft-profile/scope failures appeared as raw constructor TypeErrors.
The diagnostic guard now reports `DW6_MISSING_CONTRACT_FIELDS`. The next Pyright
pass exposed narrowing of the constructor to a possibly non-callable dataclass;
a callable assertion corrected that check. Final Pyright passes. Both unreleased
authoring snapshots, manifests and red logs are retained; their results are not
the final release digest.

The isolated offline `uv build` attempt failed because its new temporary cache had
no setuptools distribution. The bundled Python had no `build.__main__` entrypoint.
Using its installed setuptools 84.0.0 backend in a temporary source copy succeeded:
source distribution first, then a wheel from the extracted source distribution.
No dependencies were installed, no network was used, and project source was unchanged.

The release adds a second real-process crash point: suspend the test worker before
acknowledgement, admit/persist its run, crash the application, then require recovery
without another run admission. Final inventory is 97 tests, with 3 legacy passes
and 94 explicit missing-capability failures. Earlier 96-test snapshots are
unreleased preparation evidence, not approved test amendments.
