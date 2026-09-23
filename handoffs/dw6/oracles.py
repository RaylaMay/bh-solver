"""Reviewer-owned assertions over observable values, independent of product code."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def canonical(value: Any) -> bytes:
    """The documented finite, sorted-key UTF-8 JSON representation."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def unchanged(before: Any, after: Any) -> None:
    assert canonical(before) == canonical(after), "Protected source/result selection changed"


def budget_within(ledger: dict, limits: dict) -> None:
    """Outstanding reservations count against the token ceiling."""
    for name in ("iterations", "runs", "tool_calls"):
        assert type(ledger[name]) is int and 0 <= ledger[name] <= limits[name], name
    for name in ("tokens_used", "tokens_reserved"):
        assert type(ledger[name]) is int and ledger[name] >= 0, name
    assert ledger["tokens_used"] + ledger["tokens_reserved"] <= limits["tokens"]
    assert math.isfinite(ledger["elapsed_seconds"]) and ledger["elapsed_seconds"] >= 0


def approved(proposal: dict, actor: str = "human:reviewer") -> None:
    assert proposal["status"] == "APPROVED", "Exact proposal needs explicit approval"
    assert proposal["approved_by"] == actor, "Approval must retain the human actor"


def audit_valid(export: dict) -> None:
    """Check the chain and payload hashes without using the candidate's codec."""
    assert export["schema_version"] == "bh-ai-audit-v1"
    assert export["records"], "An empty audit cannot reconstruct a submitted session"
    previous = ""
    for sequence, record in enumerate(export["records"], 1):
        assert record["sequence"] == sequence, "Audit sequence gap"
        assert record["session_id"] == export["session_id"]
        assert record["schema_version"] == "bh-ai-audit-v1"
        assert record["previous_hash"] == previous, "Audit chain is broken"
        assert canonical(json.loads(record["body_json"])).decode() == record["body_json"]
        value = {k: v for k, v in record.items() if k != "record_hash"}
        assert record["record_hash"] == digest(value), "Audit record hash mismatch"
        previous = record["record_hash"]
    for artifact in export["artifacts"]:
        actual = hashlib.sha256(artifact["content_utf8"].encode("utf-8")).hexdigest()
        assert actual == artifact["sha256"], "Artifact bytes do not match their digest"


def contains_no_secret(value: Any, secret: str) -> None:
    assert secret not in json.dumps(value), "Credential leaked into an observable record"
