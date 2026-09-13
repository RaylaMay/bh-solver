"""Reference property backend and replaceable property registry."""

from __future__ import annotations

from dataclasses import dataclass

from bh_sim.core import (
    FlashRequest,
    FlashVariable,
    PhaseState,
    PropertyPackage,
    ProvenanceRecord,
    Quantity,
    StableId,
    ThermoState,
    ValidityStatus,
)


@dataclass(frozen=True)
class ReferenceLiquid:
    material_id: StableId
    name: str
    density_kg_m3: float
    cp_a_j_kg_k: float
    cp_b_j_kg_k2: float = 0.0
    cp_c_j_kg_k3: float = 0.0
    reference_temperature_k: float = 298.15
    evidence_minimum_temperature_k: float = 1.0
    evidence_maximum_temperature_k: float = 5000.0
    hard_minimum_temperature_k: float = 1.0
    hard_maximum_temperature_k: float = 5000.0
    evidence_reference: str | None = None

    def cp(self, temperature_k: float) -> float:
        value = (
            self.cp_a_j_kg_k
            + self.cp_b_j_kg_k2 * temperature_k
            + self.cp_c_j_kg_k3 * temperature_k**2
        )
        if value <= 0.0:
            raise ValueError(f"{self.name} heat capacity is non-positive")
        return value

    def enthalpy(self, temperature_k: float) -> float:
        t0 = self.reference_temperature_k
        return (
            self.cp_a_j_kg_k * (temperature_k - t0)
            + 0.5 * self.cp_b_j_kg_k2 * (temperature_k**2 - t0**2)
            + self.cp_c_j_kg_k3 / 3.0 * (temperature_k**3 - t0**3)
        )

    def temperature_from_enthalpy(self, enthalpy_j_kg: float) -> float:
        lower = self.hard_minimum_temperature_k
        upper = self.hard_maximum_temperature_k
        lower_residual = self.enthalpy(lower) - enthalpy_j_kg
        upper_residual = self.enthalpy(upper) - enthalpy_j_kg
        if lower_residual * upper_residual > 0.0:
            raise ValueError(f"enthalpy lies outside the hard domain for {self.name}")
        for _ in range(200):
            midpoint = 0.5 * (lower + upper)
            residual = self.enthalpy(midpoint) - enthalpy_j_kg
            if abs(residual) <= 1.0e-8 or upper - lower <= 1.0e-9:
                return midpoint
            if lower_residual * residual <= 0.0:
                upper = midpoint
            else:
                lower = midpoint
                lower_residual = residual
        raise RuntimeError("property inversion failed to converge")


class PolynomialLiquidPackage(PropertyPackage):
    """Pure, single-phase reference backend with extrapolation classification."""

    def __init__(
        self,
        package_id: StableId,
        liquids: tuple[ReferenceLiquid, ...],
        *,
        version: str = "v1alpha",
    ) -> None:
        self._package_id = package_id
        self.version = version
        self._liquids = {liquid.material_id: liquid for liquid in liquids}
        if not self._liquids:
            raise ValueError("property package requires at least one liquid")

    @property
    def package_id(self) -> StableId:
        return self._package_id

    def flash(self, request: FlashRequest) -> ThermoState:
        if request.property_package_id != self.package_id:
            raise ValueError("flash request targets a different property package")
        if len(request.composition) != 1 or request.composition[0].fraction != 1.0:
            raise ValueError("reference liquid backend currently supports pure fluids only")
        material_id = request.composition[0].material_id
        try:
            liquid = self._liquids[material_id]
        except KeyError as error:
            raise KeyError(f"unknown reference liquid: {material_id}") from error

        specifications = {item.variable: item.value for item in request.specifications}
        if FlashVariable.PRESSURE not in specifications:
            raise ValueError("reference liquid flash requires pressure")
        pressure = specifications[FlashVariable.PRESSURE].to("Pa")
        if FlashVariable.TEMPERATURE in specifications:
            temperature_k = specifications[FlashVariable.TEMPERATURE].to("K").value
            enthalpy_j_kg = liquid.enthalpy(temperature_k)
        elif FlashVariable.SPECIFIC_ENTHALPY in specifications:
            enthalpy_j_kg = specifications[FlashVariable.SPECIFIC_ENTHALPY].to("J/kg").value
            temperature_k = liquid.temperature_from_enthalpy(enthalpy_j_kg)
        else:
            raise ValueError("reference liquid flash supports T-P or H-P requests")

        if (
            not liquid.hard_minimum_temperature_k
            <= temperature_k
            <= liquid.hard_maximum_temperature_k
        ):
            raise ValueError(f"temperature is outside the hard domain for {liquid.name}")
        validity = ValidityStatus.VALID
        messages: tuple[str, ...] = ()
        if not (
            liquid.evidence_minimum_temperature_k
            <= temperature_k
            <= liquid.evidence_maximum_temperature_k
        ):
            validity = ValidityStatus.EXTRAPOLATED
            messages = ("temperature lies outside the evidence-backed correlation range",)

        temperature = Quantity(temperature_k, "K")
        enthalpy = Quantity(enthalpy_j_kg, "J/kg")
        phase = PhaseState(
            phase="liquid",
            fraction=1.0,
            temperature=temperature,
            pressure=pressure,
            density=Quantity(liquid.density_kg_m3, "kg/m^3"),
            specific_enthalpy=enthalpy,
            heat_capacity=Quantity(liquid.cp(temperature_k), "J/(kg*K)"),
        )
        provenance = ProvenanceRecord(
            source="polynomial-liquid-reference",
            model=liquid.name,
            version=self.version,
            evidence_reference=liquid.evidence_reference,
        )
        return ThermoState(
            property_package_id=self.package_id,
            composition=request.composition,
            temperature=temperature,
            pressure=pressure,
            specific_enthalpy=enthalpy,
            phases=(phase,),
            validity=validity,
            provenance=(provenance,),
            messages=messages,
        )


class PropertyRegistry:
    def __init__(self, packages: tuple[PropertyPackage, ...] = ()) -> None:
        self._packages: dict[StableId, PropertyPackage] = {}
        for package in packages:
            self.register(package)

    def register(self, package: PropertyPackage) -> None:
        if package.package_id in self._packages:
            raise ValueError(f"duplicate property package: {package.package_id}")
        self._packages[package.package_id] = package

    def get(self, package_id: StableId) -> PropertyPackage:
        try:
            return self._packages[package_id]
        except KeyError as error:
            raise KeyError(f"property package is unavailable: {package_id}") from error
