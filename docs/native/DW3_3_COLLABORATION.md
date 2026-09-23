# Following milestone: simultaneous BH editing over LAN/VPN

Status: **PLANNED; NETWORK EDITING DISABLED**. Date: 2026-09-14.
Rayla May selected a separate milestone following DW3.2, with one participant
hosting through BH on a local network or VPN. This record makes no choice for
any separately governed programme.

## Required behaviour

- One explicit host session orders and durably acknowledges versioned edits.
  Solo local work remains fully functional without a server or account service.
- Invitation and authenticated session identities distinguish host, editor and
  viewer. Hosting/joining are explicit UI actions; no automatic discovery upload,
  external hosting, port forwarding or project publication occurs.
- Clients submit typed operations with request, actor, project, document, branch
  and base-content identities. Disjoint changes can proceed; conflicting fields,
  deleted objects and topology changes receive explicit resolution diagnostics.
- Each client displays its own selection, viewport, dock arrangement and temporary
  groups. Follow presenter is optional and reversible. Shared equipment coordinates,
  routes, group definitions and engineering edits remain attributable.
- Undo reverses the initiating actor's changes against the current state. A
  conflicting inverse cannot restore an old whole-document checkpoint over another
  actor's work. DW3.2's conservative local reversal is not shared selective undo.
- Disconnects retain local edits in a named alternative. Reconnection reconciles
  acknowledged request IDs and heads without duplicate edits, silent overwrites,
  calculation replay or automatic branch merging.
- HAZOP review uses an exact named baseline and preserves attributable proposals,
  human dispositions and dissent under the existing scientific/AI authority gates.

## Protocol and failure-review gate

Before enabling network editing, specify and review transport framing, capability
and version negotiation, invitation authentication, encryption, permission revocation,
message/resource bounds, durable acknowledgement semantics, conflict diagnostics,
host loss, reconnect, actor identity and signed/provenance claims. Select the
transport adapter only after dependency/licence review. The UI must expose missing
capabilities and permission rejection without implying that a shared session exists.

Acceptance requires two isolated client processes, simultaneous independent edits,
same-field conflicts, delete/connect races, per-actor undo, dropped replies,
duplicate requests, malformed/version-mismatched messages, viewer write rejection,
revocation, host crashes, reconnect recovery and preservation of all saved cases.
Test network and input limits before making performance or security claims. Never
infer this gate from DW3.2's local two-writer conflict tests.
