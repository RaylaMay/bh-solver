"""Compatibility wrappers for the former HTTP/domain conversion module.

Scientific conversion now belongs to the engineering adapter. Endpoints use
neutral DTOs and services; these wrappers retain existing Python consumers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .schemas import DiagnosticDto, PfdDraftDto

if TYPE_CHECKING:
    from bh_sim.adapters.reference import AdaptedDraft
    from bh_sim.core import Diagnostic, StableId
    from bh_sim.engine.properties import PolynomialLiquidPackage


def reference_property_package() -> PolynomialLiquidPackage:
    """Compatibility factory for the unchanged reference property fixture."""
    from bh_sim.adapters.reference import reference_property_package as factory

    return factory()


def draft_to_contract(draft: PfdDraftDto) -> AdaptedDraft:
    """Retain the original canonical artifact conversion for Python consumers."""
    from bh_sim.adapters.browser_format import from_browser
    from bh_sim.adapters.reference import draft_to_contract as convert

    return convert(from_browser(draft))


def diagnostic_to_dto(
    diagnostic: Diagnostic,
    node_ids: dict[StableId, str],
    edge_ids: dict[StableId, str],
) -> DiagnosticDto:
    """Retain diagnostic projection into the existing HTTP schema."""
    from bh_sim.adapters.reference import diagnostic_to_dto as convert

    item = convert(diagnostic, node_ids, edge_ids)
    return DiagnosticDto(
        code=item.code, message=item.message, severity=item.severity, subject_id=item.subject_id
    )
