"""Extension admission and provenance policy without loading or installing plugin code.

Execution adapters remain replaceable. This application layer validates declared
capabilities and permissions, requires explicit enablement for elevated tiers, and
converts adapter failure into an attributable immutable record.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from bh_sim.boundary import contracts as c


class ExtensionRunnerPort(Protocol):
    """Execute a previously installed extension through its selected stable adapter."""

    def execute(
        self, manifest: c.PluginManifest, input_hashes: tuple[str, ...]
    ) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class ExtensionPolicy:
    """Host policy selected by the user; manifests cannot grant their own authority."""

    api_version: str
    allowed_permissions: frozenset[str] = frozenset({"case-read", "artifact-read"})
    trusted_in_process_enabled: bool = False
    developer_mode_enabled: bool = False


class ExtensionService:
    """Admit and supervise extension calls while preserving unverified status."""

    def __init__(self, policy: ExtensionPolicy, runner: ExtensionRunnerPort) -> None:
        self.policy = policy
        self.runner = runner

    def execute(
        self, manifest: c.PluginManifest, input_hashes: tuple[str, ...]
    ) -> c.PluginExecutionRecord:
        """Return a record for rejection, crash, or output; never mutate a case."""

        rejection = self._rejection(manifest)
        if rejection:
            return self._record(manifest, input_hashes, "REJECTED", diagnostic=rejection)
        try:
            outputs = self.runner.execute(manifest, input_hashes)
            if any(len(value) != 64 for value in outputs):
                raise ValueError("extension returned a malformed output hash")
            for value in outputs:
                int(value, 16)
        except Exception as error:  # Adapter boundaries convert crashes to typed failure.
            return self._record(
                manifest,
                input_hashes,
                "FAILED",
                diagnostic=f"{type(error).__name__}: extension execution failed",
            )
        return self._record(manifest, input_hashes, "COMPLETED", outputs)

    def _rejection(self, manifest: c.PluginManifest) -> str:
        if manifest.api_version != self.policy.api_version:
            return "Plugin API version mismatch"
        denied = set(manifest.permissions) - self.policy.allowed_permissions
        if denied:
            return "Plugin permission rejected: " + ", ".join(sorted(denied))
        if (
            manifest.execution_mode == "trusted-in-process"
            and not self.policy.trusted_in_process_enabled
        ):
            return "Trusted in-process extensions require explicit enablement"
        if (
            manifest.execution_mode == "developer-unsupported"
            and not self.policy.developer_mode_enabled
        ):
            return "Unsupported developer mode requires explicit enablement"
        return ""

    @staticmethod
    def _record(
        manifest: c.PluginManifest,
        inputs: tuple[str, ...],
        disposition: Literal["COMPLETED", "REJECTED", "FAILED"],
        outputs: tuple[str, ...] = (),
        *,
        diagnostic: str = "",
    ) -> c.PluginExecutionRecord:
        return c.PluginExecutionRecord(
            manifest.plugin_id,
            manifest.version,
            manifest.execution_mode,
            inputs,
            tuple(manifest.permissions),
            disposition,
            outputs,
            diagnostic=diagnostic,
        )
