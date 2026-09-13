"""Explicit composition root binding concrete DW1 local adapters.

Only wiring selects the existing fixture catalogue/property backend. No scientific
configuration, dependency or licence selection is introduced by this extraction.
"""

from __future__ import annotations

import json
import platform
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

from bh_sim.adapters.demonstrations import PrototypeDemonstrationAdapter
from bh_sim.adapters.engineering import InProcessEngineeringAdapter
from bh_sim.adapters.reference import reference_property_package
from bh_sim.adapters.storage import (
    ArtifactRepositoryAdapter,
    DraftRepository,
    DraftRepositoryAdapter,
)
from bh_sim.application.commands import CommandRegistry
from bh_sim.application.services import ApplicationServices, DemonstrationService
from bh_sim.core.json_codec import canonical_json
from bh_sim.engine import AcyclicRunEngine, PropertyRegistry, reference_model_catalog
from bh_sim.engine.properties import PolynomialLiquidPackage
from bh_sim.persistence import PersistenceStore


def create_services(data_root: str | Path | None = None) -> ApplicationServices:
    """Bind legacy local storage and the selected in-process fixture engine."""

    root = Path(data_root or ".bh/runtime")
    catalog = reference_model_catalog()
    properties = PropertyRegistry((reference_property_package(),))
    engine = AcyclicRunEngine(catalog, properties)

    def context_metadata(selected_engine: AcyclicRunEngine) -> str:
        # Inventory concrete state here, not in application policy. An unsupported
        # backend requires a context adapter rather than an optimistic version label.
        packages = []
        for identifier, package in sorted(selected_engine.properties._packages.items()):
            if not isinstance(package, PolynomialLiquidPackage):
                raise RuntimeError("execution-context inventory unavailable for this backend")
            packages.append(
                {
                    "package_id": str(identifier),
                    "implementation": type(package).__qualname__,
                    "version": package.version,
                    "liquids": [asdict(liquid) for _, liquid in sorted(package._liquids.items())],
                }
            )
        return json.dumps(
            {
                "catalogue": [
                    json.loads(canonical_json(selected_engine.catalog.descriptor(model)))
                    for model in selected_engine.catalog.model_ids
                ],
                "factories": [
                    (name, factory.__module__, factory.__qualname__)
                    for name, factory in sorted(selected_engine.catalog._factories.items())
                ],
                "properties": packages,
                "execution": "AcyclicRunEngine/v1alpha; no configured residual solver",
                "runtime": {
                    "implementation": platform.python_implementation(),
                    "version": platform.python_version(),
                },
                "packages": {
                    name: version(name) for name in ("numpy", "scipy", "pint", "networkx")
                },
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    return ApplicationServices(
        DraftRepositoryAdapter(DraftRepository(root / "drafts")),
        InProcessEngineeringAdapter(engine, context_metadata),
        ArtifactRepositoryAdapter(PersistenceStore(root / "contracts")),
        PrototypeDemonstrationAdapter(),
    )


def create_registry(data_root: str | Path | None = None) -> CommandRegistry:
    """Create one application command session with process-local receipts."""

    return CommandRegistry(create_services(data_root))


def create_demonstration_registry() -> CommandRegistry:
    """Wire CLI commands without creating a persistence directory."""

    return CommandRegistry(DemonstrationService(PrototypeDemonstrationAdapter()))
