"""Native PFD persistence, reference descriptors and existing quantity conversion.

No new scientific model or coefficient is introduced. Native snapshots use a
separate directory and strict versioned JSON; browser revisions remain untouched.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from bh_sim.boundary import contracts as c
from bh_sim.boundary.json_codec import boundary_from_json, boundary_json


def reference_catalogue() -> c.PfdCatalogueDto:
    """Mirror the existing reference adapter's in-N/out-N port and parameter mapping."""
    definitions = (
        (
            "source",
            "Source",
            0,
            1,
            (
                ("massFlow", "Mass flow", "kg/s"),
                ("temperature", "Temperature", "K"),
                ("pressure", "Pressure", "Pa"),
            ),
        ),
        ("sink", "Sink", 1, 0, ()),
        ("heater", "Heater", 1, 1, (("duty", "Heat duty", "W"),)),
        (
            "radiator",
            "Radiator",
            1,
            1,
            (
                ("targetTemperature", "Outlet temperature", "K"),
                ("emissivity", "Emissivity", "1"),
            ),
        ),
        ("mixer", "Mixer", 2, 1, ()),
        ("splitter", "Splitter", 1, 2, (("splitFraction", "Split fraction", "1"),)),
        (
            "heat_exchanger",
            "Heat exchanger",
            2,
            2,
            (("effectiveness", "Effectiveness", "1"),),
        ),
    )
    return c.PfdCatalogueDto(
        tuple(
            c.PfdModelDto(
                identifier,
                title,
                tuple(c.PfdPortDto(f"in-{i}", "input") for i in range(inputs))
                + tuple(c.PfdPortDto(f"out-{i}", "output") for i in range(outputs)),
                tuple(c.PfdParameterDto(*p) for p in parameters),
            )
            for identifier, title, inputs, outputs, parameters in definitions
        )
    )


class ExistingQuantityAdapter:
    """Use the established double-precision/Pint unit boundary, loaded only on demand."""

    def convert(self, quantity: c.QuantityDto, target_unit: str) -> c.QuantityDto:
        from bh_sim.core.quantity import Quantity

        try:
            converted = Quantity(quantity.value, quantity.unit).to(target_unit)
            return c.QuantityDto(converted.value, target_unit)
        except Exception as error:
            # Pint exposes multiple exception classes. Convert these to a stable
            # input rejection without exposing internals or silently substituting units.
            raise ValueError("Unrecognized or incompatible quantity unit") from error


class NativePfdRepository:
    """Append-only UTF-8 snapshots with idempotency and exclusive atomic publication.

    SHA-256 filenames prevent draft-name normalization collisions. A concurrent
    writer collision fails explicitly; no saved revision is overwritten or retried.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()

    def _paths(self, draft_id: str) -> list[Path]:
        digest = hashlib.sha256(draft_id.encode()).hexdigest()
        return sorted(self.root.glob(f"{digest}.r*.json"))

    @staticmethod
    def _read(path: Path) -> c.PfdDocumentDto:
        if path.stat().st_size > 20_000_000:
            raise ValueError("Native document exceeds 20 MB safety bound")
        document = boundary_from_json(path.read_text(encoding="utf-8"))
        if not isinstance(document, c.PfdDocumentDto):
            raise ValueError("Expected native PFD document")
        return document

    def latest(self, draft_id: str) -> c.PfdDocumentDto:
        paths = self._paths(draft_id)
        if not paths:
            raise KeyError(draft_id)
        document = self._read(paths[-1])
        if document.draft.draft_id != draft_id:
            raise ValueError("Stored draft identity mismatch")
        return document

    def summaries(self) -> tuple[c.DraftSummaryDto, ...]:
        latest: dict[str, c.DraftSummaryDto] = {}
        for path in sorted(self.root.glob("*.r*.json")):
            draft = self._read(path).draft
            previous = latest.get(draft.draft_id)
            if previous is None or draft.revision > previous.revision:
                latest[draft.draft_id] = c.DraftSummaryDto(
                    draft.draft_id, draft.revision, draft.updated_at
                )
        return tuple(latest[k] for k in sorted(latest))

    def save(self, document: c.PfdDocumentDto) -> c.PfdDocumentDto:
        """Publish complete bytes once; errors leave every previous revision intact."""
        with self.lock:
            try:
                previous = self.latest(document.draft.draft_id)
            except KeyError:
                previous = None
            if (
                previous is not None
                and replace(
                    document,
                    draft=replace(
                        document.draft,
                        revision=previous.draft.revision,
                        updated_at=previous.draft.updated_at,
                    ),
                )
                == previous
            ):
                return previous
            revision = previous.draft.revision + 1 if previous else max(1, document.draft.revision)
            saved = replace(
                document,
                draft=replace(
                    document.draft, revision=revision, updated_at=datetime.now(UTC).isoformat()
                ),
            )
            payload = boundary_json(saved) + "\n"
            if len(payload.encode()) > 20_000_000:
                raise ValueError("Native document exceeds 20 MB safety bound")
            digest = hashlib.sha256(saved.draft.draft_id.encode()).hexdigest()
            destination = self.root / f"{digest}.r{revision:09d}.json"
            descriptor, temporary = tempfile.mkstemp(prefix=".pending-", dir=self.root)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.link(temporary, destination)
                if os.name != "nt":
                    directory = os.open(self.root, os.O_RDONLY)
                    try:
                        os.fsync(directory)
                    finally:
                        os.close(directory)
            finally:
                Path(temporary).unlink(missing_ok=True)
            return saved
