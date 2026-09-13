# DW0 disposition by Rayla May and DW1 authorization

Date: **2026-09-11**. Status: **RAYLA MAY APPROVED WITH THE ANNOTATIONS BELOW**.
Authority: Rayla May's decision in the continuing BH project
conversation. This records that decision; it is not a scientific approval or a
claim that unimplemented requirements have passed verification.

## Approval scope

Rayla May approved the DW0 proposal with platform and licensing annotations and
instructed continuation into DW1, with questions and suggestions flagged before
building. This accepts ADR-010's architecture direction, neutral boundary and
versioning plan, staged migration, documentation impacts and parity/rollback
checklist. Existing browser/CLI behaviour remains the compatibility baseline.
All software acceptance rows remain at their evidence-supported status.

This explicit authorization permits DW1's Qt-free boundary/service extraction.
The uncompleted historical M0 review records are not silently marked VERIFIED,
and do not ask Rayla May to approve this same DW1 work again. Exact
toolkit payload, new wire contracts, rendering, worker, packaging and scientific
promotion still follow their applicable implementation/review gates.

## Working product name

**BH solver** is the current non-commercial product name. It does not rename the
Python package, executable commands, schema identifiers, model IDs, artifact
hashes or stored cases. BH solver has not been verified for operational use.

## P-01 — Accepted platform direction

| Concern | Rayla May's decision |
|---|---|
| Primary development and first release | macOS/arm64; this is the currently available development/test hardware |
| End-state design | Expect deployment to both macOS/arm64 and Windows/x86_64 |
| BH solver Linux | Planned eventual target; distribution and CPU architecture still to be selected |
| Minimum OS/runtime/hardware versions | Determine as a deployable build develops; no minimums selected now |
| Verification scope | macOS evidence alone does not establish Windows/Linux support |

Implementation implication: keep platform-specific launch, paths, devices and UI
behaviour behind adapters. Avoid architecture decisions that require macOS APIs
in neutral contracts or kernel policy. Required release minimums and supported
configurations must be recorded before their release gate; their deferral does
not prevent DW1.

## L-01 — Accepted route and licence ownership

Rayla May selected the **LGPLv3 route for Qt/PySide**, without commercial Qt terms
or dependencies requiring a commercial licence purchase at this stage. The
existing permissive scientific dependencies remain permitted. A library allowing
commercial use is not the same as a library requiring commercial licensing.

Rayla May then clarified the application-code intention explicitly:
**non-commercial, source-available BH-owned code, with Qt/PySide under LGPLv3.**
The repository now records that policy in its root license. More proprietary packages may
remain separately closed, subject to their actual ownership and licence terms.

The BH project license is separate from Qt's licence and from industrial-use
warnings. No non-commercial limitation is imposed on Qt or third-party code.
LGPL notices, source/replacement/relinking
rights and applicable installation information must be preserved in the actual
distribution. Proprietary adapter separation does not by itself establish licence
compatibility.

The root `LICENSE` and package metadata now identify Rayla May as the project owner and apply
the BH Non-Commercial Source-Available License to BH-owned project material.
Prior distribution and rights ownership must still be checked for any material
whose provenance is not Rayla May's. Local DW1 implementation does not alter
third-party licenses.

Exact Qt versions, module/plugin inventory, source/notices, packager and compliance
evidence remain adoption/release work. Choosing LGPLv3 is not evidence that an
unbuilt installer meets its obligations. The default kernel remains Qt-free.

## Before-build questions and suggestions recorded

The application-versus-library licence ambiguity was raised and Rayla May selected
the source-available option above. Before implementation, the agent recommended:

1. Freeze browser HTTP, canonical artifact and legacy CLI compatibility fixtures.
2. Extract neutral commands and application services without adding Qt.
3. Use exact-hash validation on new commands while preserving the legacy HTTP
   compatibility use case; do not silently tighten its existing API semantics.
4. Keep working product names separate from persisted and package identities.

No further decision by Rayla May is required for that focused DW1 extraction. The adopted
license defines commercial-use restrictions; renderer targets, AI/speech policies
and packaging remain at their later gates.

## Change record

Objective and instruction from Rayla May: record the approved DW0 annotations and prepare DW1.
References: ADR-010, P-01/L-01, action-plan DW0/DW1 and Appendix A.
Scope: product terminology, platform/licence posture and approval status; no
scientific model, artifact schema or licence-file change from this record.
Selected design: preserve dated DW0 evidence and accepted ADR-001–009 bodies; add
this attributable disposition and update current status pointers.
Alternative: treating all approval as pending would contradict Rayla May's
decision; silently interpreting LGPL as non-commercial would misstate its terms.
Risks/limitations: unavailable cross-platform hardware and later toolkit payload
review. No current industrial qualification.
Verification and complete changed-file/rollback inventory are recorded with the
[DW1 work unit](DW1_CHANGE_RECORD.md). This document contains no implied signature
for scientific or release approval.
