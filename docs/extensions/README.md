# Extension foundation

Status: **DW3.1 CONTRACT AND POLICY FOUNDATION; RUNTIME LOADERS DEFERRED**.
Date: 2026-09-14. Owner: Rayla May.

BH solver accepts no extension merely because a manifest exists. A user must install
code separately, review its declared permissions and choose an execution tier. BH
does not download code, install dependencies, or bundle a C++ compiler in this work
unit.

`PluginManifest` declares identity, version, stable API version, Python or C++
language, execution mode, capabilities, permissions, supported platform and
architecture, licence, provenance, entry point and exact artifact SHA-256. The
registered capability vocabulary covers unit models, numerical adapters, studies,
import/export handlers, commands, data-driven panels, visual layers and namespaced
domain packages.

The three execution tiers are:

1. `isolated-stable`: default language-neutral worker boundary.
2. `trusted-in-process`: stable API for a user-enabled, performance-sensitive plugin.
3. `developer-unsupported`: user-enabled internal Python imports with explicit
   compatibility and audit limitations.

The [worker schema](worker-protocol-v1.schema.json) fixes the first request/outcome
framing for an isolated adapter. It carries hashes and identifiers rather than case
objects. Framing, size limits, process supervision and platform sandboxing remain a
future runtime implementation gate.

The [C header](../../sdk/cpp/bh_plugin.h) fixes the first supported in-process ABI
surface for precompiled extensions. C++ plugins expose C symbols and exchange the
same UTF-8 protocol messages. This avoids compiler-ABI coupling at the exported
boundary. The header alone does not establish binary compatibility across all
toolchains or platforms; packaged SDK examples, conformance tests and loader
hardening remain future extension work.

`ExtensionService` currently implements admission policy over an injected runner:
API mismatch, undeclared host permissions, and disabled elevated tiers reject
before execution. Adapter exceptions and malformed output hashes become typed
failed records and do not mutate a case. Every completed custom output remains
`UNVERIFIED_EXTENSION`; only the evidence-pack, model-card, implementation,
independent-V&V and catalogue lifecycle can change scientific authority.

The `domain-package` capability reserves namespaced extension identity for future
1-D propulsion work. It adds no rocket equation, reacting-flow implementation,
port type or validity claim. A dedicated scientific programme must govern
compressible/reacting flow, choking, combustion, heat transfer, turbomachinery,
mechanical coupling, events and model validity after the dynamic foundation exists.
