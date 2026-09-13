"""Small JSON command-line interface for calculation demonstrations."""

from __future__ import annotations

import argparse
import json
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from bh_sim.boundary.contracts import (
    CommandRequest,
    DemonstrationParameters,
    DemonstrationReportDto,
)
from bh_sim.composition import create_demonstration_registry

if TYPE_CHECKING:
    from bh_sim.audit import CalculationReport


def _command_report(command: str) -> DemonstrationReportDto:
    outcome = create_demonstration_registry().dispatch(
        CommandRequest(
            "demo.evaluate",
            str(uuid4()),
            "legacy-cli",
            DemonstrationParameters(command),
        )
    )
    if not isinstance(outcome.data, DemonstrationReportDto):
        raise ValueError(f"unknown command {command}")
    return outcome.data


def demonstration_report(command: str) -> CalculationReport:
    """Compatibility Python API; restore report identity after application dispatch."""
    from bh_sim.adapters.demonstrations import restore_legacy_report

    return restore_legacy_report(_command_report(command))


def main() -> None:
    """Preserve existing arguments and JSON output; no storage is created."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("solid-radiator", "droplet-radiator", "surge-buffer"))
    args = parser.parse_args()
    print(json.dumps(_command_report(args.command).to_dict(), indent=2, allow_nan=False))


def __getattr__(name: str) -> Any:
    """Retain the old illustrative_fluid helper for explicit Python consumers."""
    if name != "illustrative_fluid":
        raise AttributeError(name)
    from bh_sim.adapters.demonstrations import illustrative_fluid

    return illustrative_fluid


if __name__ == "__main__":
    main()
