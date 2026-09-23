"""DW3.1 extension contracts and policy; no plugin code is loaded by these tests."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from bh_sim.application.extensions import ExtensionPolicy, ExtensionService
from bh_sim.boundary import contracts as c
from bh_sim.boundary.json_codec import boundary_from_json, boundary_json

HASH = "a" * 64


class RecordingRunner:
    def __init__(self, result: tuple[str, ...] = ("b" * 64,), error: Exception | None = None):
        self.result, self.error = result, error
        self.calls = 0

    def execute(self, manifest: c.PluginManifest, input_hashes: tuple[str, ...]) -> tuple[str, ...]:
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


def manifest(**changes: object) -> c.PluginManifest:
    return replace(
        c.PluginManifest(
            "example.domain",
            "Example domain package",
            "1.0.0",
            "bh-extension-v1",
            "python",
            "isolated-stable",
            ("domain-package", "unit-model"),
            ("case-read",),
            ("macos", "windows", "linux"),
            ("arm64", "x86_64"),
            "BH-compatible-source-available",
            "publisher:example",
            HASH,
            "example.worker",
        ),
        **changes,
    )


def test_plugin_contract_round_trip_and_unverified_provenance() -> None:
    plugin = manifest()
    runner = RecordingRunner()
    record = ExtensionService(ExtensionPolicy("bh-extension-v1"), runner).execute(plugin, (HASH,))
    assert record.disposition == "COMPLETED"
    assert record.scientific_status == "UNVERIFIED_EXTENSION"
    assert record.plugin_id == plugin.plugin_id
    assert boundary_from_json(boundary_json(plugin)) == plugin
    assert boundary_from_json(boundary_json(record)) == record
    fixture = Path(__file__).parent / "fixtures" / "dw3_1" / "plugin-manifest.json"
    assert boundary_from_json(fixture.read_text()) == plugin
    assert boundary_json(plugin) == fixture.read_text().strip()


@pytest.mark.parametrize(
    ("plugin", "expected"),
    [
        (manifest(api_version="future"), "version mismatch"),
        (manifest(permissions=("network",)), "permission rejected"),
        (manifest(execution_mode="trusted-in-process"), "explicit enablement"),
        (manifest(execution_mode="developer-unsupported"), "explicit enablement"),
    ],
)
def test_extension_rejection_occurs_before_runner(plugin: c.PluginManifest, expected: str) -> None:
    runner = RecordingRunner()
    record = ExtensionService(ExtensionPolicy("bh-extension-v1"), runner).execute(plugin, (HASH,))
    assert record.disposition == "REJECTED" and expected in record.diagnostic.lower()
    assert runner.calls == 0


def test_extension_crash_and_malformed_output_are_contained() -> None:
    for runner in (
        RecordingRunner(error=RuntimeError("private detail")),
        RecordingRunner(("bad",)),
    ):
        record = ExtensionService(ExtensionPolicy("bh-extension-v1"), runner).execute(
            manifest(), (HASH,)
        )
        assert record.disposition == "FAILED"
        assert record.output_hashes == ()
        assert "private detail" not in record.diagnostic
        assert record.scientific_status == "UNVERIFIED_EXTENSION"


def test_elevated_modes_require_and_honor_explicit_host_enablement() -> None:
    runner = RecordingRunner()
    trusted = ExtensionService(
        ExtensionPolicy("bh-extension-v1", trusted_in_process_enabled=True), runner
    ).execute(manifest(execution_mode="trusted-in-process"), (HASH,))
    developer = ExtensionService(
        ExtensionPolicy("bh-extension-v1", developer_mode_enabled=True), runner
    ).execute(manifest(execution_mode="developer-unsupported"), (HASH,))
    assert trusted.disposition == developer.disposition == "COMPLETED"
    assert trusted.execution_mode == "trusted-in-process"
    assert developer.execution_mode == "developer-unsupported"


def test_plugin_manifest_rejects_invalid_hash_and_duplicate_authority() -> None:
    with pytest.raises(ValueError):
        manifest(artifact_sha256="not-a-hash")
    with pytest.raises(ValueError):
        manifest(capabilities=("unit-model", "unit-model"))


def test_isolated_worker_schema_is_closed_and_versioned() -> None:
    root = Path(__file__).parents[1]
    schema = json.loads((root / "docs/extensions/worker-protocol-v1.schema.json").read_text())
    assert schema["$id"] == "bh-extension-worker-v1"
    request = schema["$defs"]["request"]
    response = schema["$defs"]["response"]
    assert request["additionalProperties"] is False
    assert response["additionalProperties"] is False
    assert response["properties"]["disposition"]["enum"] == [
        "COMPLETED",
        "REJECTED",
        "FAILED",
    ]
