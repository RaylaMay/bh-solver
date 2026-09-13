"""Reference steady-state unit-operation implementations."""

from __future__ import annotations

from dataclasses import dataclass

from bh_sim.core import (
    AuditEvidence,
    CompositionComponent,
    Diagnostic,
    EnergyPort,
    EnergyPortValue,
    FlashRequest,
    FlashVariable,
    MaterialPort,
    MaterialPortValue,
    MaterialReference,
    MaterialState,
    Port,
    PortDirection,
    Quantity,
    Residual,
    StableId,
    StateSpecification,
    UnitDefinition,
    UnitEvaluation,
    UnitEvaluationRequest,
    ValidityStatus,
)

from .catalog import EvaluationServices, ModelCatalog, ModelDescriptor

INLET = StableId("port:inlet")
OUTLET = StableId("port:outlet")
INLET_A = StableId("port:inlet-a")
INLET_B = StableId("port:inlet-b")
OUTLET_A = StableId("port:outlet-a")
OUTLET_B = StableId("port:outlet-b")
HOT_IN = StableId("port:hot-in")
HOT_OUT = StableId("port:hot-out")
COLD_IN = StableId("port:cold-in")
COLD_OUT = StableId("port:cold-out")
DUTY = StableId("port:duty")


def _parameter(definition: UnitDefinition, name: str) -> Quantity:
    values = dict(definition.parameters)
    try:
        return values[name]
    except KeyError as error:
        raise ValueError(f"{definition.name} requires parameter {name!r}") from error


def _metadata(definition: UnitDefinition, name: str) -> str:
    values = dict(definition.metadata)
    try:
        return values[name]
    except KeyError as error:
        raise ValueError(f"{definition.name} requires metadata {name!r}") from error


def _material_input(request: UnitEvaluationRequest, port_id: StableId) -> MaterialState:
    for value in request.input_port_values:
        if isinstance(value, MaterialPortValue) and value.port_id == port_id:
            return value.state
    raise ValueError(f"missing material input {port_id}")


def _worst_validity(*values: ValidityStatus) -> ValidityStatus:
    order = {
        ValidityStatus.UNKNOWN: 0,
        ValidityStatus.VALID: 1,
        ValidityStatus.EXTRAPOLATED: 2,
        ValidityStatus.INVALID: 3,
    }
    return max(values, key=order.__getitem__)


@dataclass(frozen=True)
class ReferenceUnit:
    definition: UnitDefinition
    services: EvaluationServices
    _ports: tuple[Port, ...]

    @property
    def model_id(self) -> str:
        return self.definition.model_id

    @property
    def ports(self) -> tuple[Port, ...]:
        return self._ports

    def _flash_tp(
        self,
        material_reference: MaterialReference,
        composition: tuple[CompositionComponent, ...],
        temperature: Quantity,
        pressure: Quantity,
    ):
        package = self.services.properties.get(material_reference.property_package_id)
        return package.flash(
            FlashRequest(
                property_package_id=material_reference.property_package_id,
                composition=composition,
                specifications=(
                    StateSpecification(FlashVariable.TEMPERATURE, temperature),
                    StateSpecification(FlashVariable.PRESSURE, pressure),
                ),
            )
        )

    def _flash_hp(
        self,
        state: MaterialState,
        specific_enthalpy: Quantity,
        pressure: Quantity,
    ):
        package = self.services.properties.get(state.thermo.property_package_id)
        return package.flash(
            FlashRequest(
                property_package_id=state.thermo.property_package_id,
                composition=state.composition,
                specifications=(
                    StateSpecification(FlashVariable.SPECIFIC_ENTHALPY, specific_enthalpy),
                    StateSpecification(FlashVariable.PRESSURE, pressure),
                ),
            )
        )


class SourceUnit(ReferenceUnit):
    def evaluate(self, request: UnitEvaluationRequest) -> UnitEvaluation:
        material_id = StableId(_metadata(self.definition, "material_id"))
        material = self.services.materials[material_id]
        if not isinstance(material, MaterialReference):
            raise TypeError("material registry contains an invalid entry")
        composition = (CompositionComponent(material.material_id, 1.0),)
        thermo = self._flash_tp(
            material,
            composition,
            _parameter(self.definition, "temperature"),
            _parameter(self.definition, "pressure"),
        )
        state = MaterialState(
            material_reference_id=material.material_id,
            composition=composition,
            mass_flow=_parameter(self.definition, "mass_flow").to("kg/s"),
            thermo=thermo,
        )
        return UnitEvaluation(
            unit_id=request.unit_id,
            output_port_values=(MaterialPortValue(OUTLET, state),),
            residuals=(),
            diagnostics=tuple(
                Diagnostic("thermo", message, "warning") for message in thermo.messages
            ),
            events=(),
            validity=thermo.validity,
            audit_evidence=(
                AuditEvidence(
                    "source-state",
                    "state = flash(T, P, z)",
                    inputs=(
                        ("temperature", thermo.temperature),
                        ("pressure", thermo.pressure),
                        ("mass_flow", state.mass_flow),
                    ),
                    outputs=(("specific_enthalpy", thermo.specific_enthalpy),),
                    evidence_reference="MODEL-CARD-REFERENCE-LIQUID-V1ALPHA",
                ),
            ),
            metrics=(
                ("temperature", thermo.temperature),
                ("pressure", thermo.pressure),
                ("mass_flow", state.mass_flow),
            ),
        )


class SinkUnit(ReferenceUnit):
    def evaluate(self, request: UnitEvaluationRequest) -> UnitEvaluation:
        state = _material_input(request, INLET)
        return UnitEvaluation(
            unit_id=request.unit_id,
            output_port_values=(),
            residuals=(),
            diagnostics=(),
            events=(),
            validity=state.thermo.validity,
            audit_evidence=(AuditEvidence("sink-boundary", "outflow recorded at boundary"),),
            metrics=(
                ("temperature", state.thermo.temperature),
                ("pressure", state.thermo.pressure),
                ("mass_flow", state.mass_flow),
            ),
        )


class HeaterUnit(ReferenceUnit):
    def evaluate(self, request: UnitEvaluationRequest) -> UnitEvaluation:
        inlet = _material_input(request, INLET)
        duty = _parameter(self.definition, "duty").to("W")
        flow_kg_s = inlet.mass_flow.to("kg/s").value
        if flow_kg_s <= 0.0:
            raise ValueError("heater inlet mass flow must be positive")
        outlet_enthalpy = Quantity(
            inlet.thermo.specific_enthalpy.to("J/kg").value + duty.value / flow_kg_s,
            "J/kg",
        )
        thermo = self._flash_hp(inlet, outlet_enthalpy, inlet.thermo.pressure)
        outlet = MaterialState(
            inlet.material_reference_id,
            inlet.composition,
            inlet.mass_flow,
            thermo,
        )
        return UnitEvaluation(
            unit_id=request.unit_id,
            output_port_values=(
                MaterialPortValue(OUTLET, outlet),
                EnergyPortValue(DUTY, duty),
            ),
            residuals=(Residual("energy", 0.0, max(abs(duty.value), 1.0), "W"),),
            diagnostics=tuple(
                Diagnostic("thermo", message, "warning") for message in thermo.messages
            ),
            events=(),
            validity=_worst_validity(inlet.thermo.validity, thermo.validity),
            audit_evidence=(
                AuditEvidence(
                    "heater-energy-balance",
                    "Q_dot = m_dot * (h_out - h_in)",
                    inputs=(
                        ("mass_flow", inlet.mass_flow),
                        ("specific_enthalpy_in", inlet.thermo.specific_enthalpy),
                        ("specific_enthalpy_out", thermo.specific_enthalpy),
                    ),
                    outputs=(("duty", duty), ("outlet_temperature", thermo.temperature)),
                ),
            ),
            metrics=(("duty", duty), ("outlet_temperature", thermo.temperature)),
        )


class MixerUnit(ReferenceUnit):
    def evaluate(self, request: UnitEvaluationRequest) -> UnitEvaluation:
        first = _material_input(request, INLET_A)
        second = _material_input(request, INLET_B)
        if first.material_reference_id != second.material_reference_id:
            raise ValueError("reference mixer requires matching materials")
        if first.composition != second.composition:
            raise ValueError("reference mixer requires matching compositions")
        first_flow = first.mass_flow.to("kg/s").value
        second_flow = second.mass_flow.to("kg/s").value
        total_flow = first_flow + second_flow
        mixed_h = (
            first_flow * first.thermo.specific_enthalpy.to("J/kg").value
            + second_flow * second.thermo.specific_enthalpy.to("J/kg").value
        ) / total_flow
        pressure = Quantity(
            min(first.thermo.pressure.to("Pa").value, second.thermo.pressure.to("Pa").value),
            "Pa",
        )
        thermo = self._flash_hp(first, Quantity(mixed_h, "J/kg"), pressure)
        outlet = MaterialState(
            first.material_reference_id,
            first.composition,
            Quantity(total_flow, "kg/s"),
            thermo,
        )
        return UnitEvaluation(
            request.unit_id,
            (MaterialPortValue(OUTLET, outlet),),
            (Residual("mass", 0.0, max(total_flow, 1.0), "kg/s"), Residual("energy", 0.0)),
            (),
            (),
            _worst_validity(first.thermo.validity, second.thermo.validity, thermo.validity),
            (AuditEvidence("mixer-balances", "m_out=sum(m_in); h_out=sum(m*h)/sum(m)"),),
            (("outlet_mass_flow", outlet.mass_flow), ("outlet_temperature", thermo.temperature)),
        )


class SplitterUnit(ReferenceUnit):
    def evaluate(self, request: UnitEvaluationRequest) -> UnitEvaluation:
        inlet = _material_input(request, INLET)
        fraction = _parameter(self.definition, "split_fraction").to("1").value
        if not 0.0 <= fraction <= 1.0:
            raise ValueError("split fraction must be between zero and one")
        total = inlet.mass_flow.to("kg/s").value
        first = MaterialState(
            inlet.material_reference_id,
            inlet.composition,
            Quantity(total * fraction, "kg/s"),
            inlet.thermo,
        )
        second = MaterialState(
            inlet.material_reference_id,
            inlet.composition,
            Quantity(total * (1.0 - fraction), "kg/s"),
            inlet.thermo,
        )
        return UnitEvaluation(
            request.unit_id,
            (MaterialPortValue(OUTLET_A, first), MaterialPortValue(OUTLET_B, second)),
            (Residual("mass", 0.0, max(total, 1.0), "kg/s"),),
            (),
            (),
            inlet.thermo.validity,
            (AuditEvidence("splitter-mass-balance", "m_a=f*m_in; m_b=(1-f)*m_in"),),
            (("outlet_a_mass_flow", first.mass_flow), ("outlet_b_mass_flow", second.mass_flow)),
        )


class HeatExchangerUnit(ReferenceUnit):
    def evaluate(self, request: UnitEvaluationRequest) -> UnitEvaluation:
        hot = _material_input(request, HOT_IN)
        cold = _material_input(request, COLD_IN)
        effectiveness = _parameter(self.definition, "effectiveness").to("1").value
        if not 0.0 <= effectiveness <= 1.0:
            raise ValueError("effectiveness must be between zero and one")
        if hot.thermo.temperature.to("K").value <= cold.thermo.temperature.to("K").value:
            raise ValueError("hot inlet must be warmer than cold inlet")

        hot_flow = hot.mass_flow.to("kg/s").value
        cold_flow = cold.mass_flow.to("kg/s").value
        hot_package = self.services.properties.get(hot.thermo.property_package_id)
        cold_package = self.services.properties.get(cold.thermo.property_package_id)
        hot_at_cold = hot_package.flash(
            FlashRequest(
                hot.thermo.property_package_id,
                hot.composition,
                (
                    StateSpecification(FlashVariable.TEMPERATURE, cold.thermo.temperature),
                    StateSpecification(FlashVariable.PRESSURE, hot.thermo.pressure),
                ),
            )
        )
        cold_at_hot = cold_package.flash(
            FlashRequest(
                cold.thermo.property_package_id,
                cold.composition,
                (
                    StateSpecification(FlashVariable.TEMPERATURE, hot.thermo.temperature),
                    StateSpecification(FlashVariable.PRESSURE, cold.thermo.pressure),
                ),
            )
        )
        hot_limit = hot_flow * (
            hot.thermo.specific_enthalpy.to("J/kg").value
            - hot_at_cold.specific_enthalpy.to("J/kg").value
        )
        cold_limit = cold_flow * (
            cold_at_hot.specific_enthalpy.to("J/kg").value
            - cold.thermo.specific_enthalpy.to("J/kg").value
        )
        duty_w = effectiveness * min(hot_limit, cold_limit)
        hot_h = hot.thermo.specific_enthalpy.to("J/kg").value - duty_w / hot_flow
        cold_h = cold.thermo.specific_enthalpy.to("J/kg").value + duty_w / cold_flow
        hot_thermo = self._flash_hp(hot, Quantity(hot_h, "J/kg"), hot.thermo.pressure)
        cold_thermo = self._flash_hp(cold, Quantity(cold_h, "J/kg"), cold.thermo.pressure)
        hot_out = MaterialState(
            hot.material_reference_id, hot.composition, hot.mass_flow, hot_thermo
        )
        cold_out = MaterialState(
            cold.material_reference_id, cold.composition, cold.mass_flow, cold_thermo
        )
        duty = Quantity(duty_w, "W")
        validity = _worst_validity(
            hot.thermo.validity,
            cold.thermo.validity,
            hot_thermo.validity,
            cold_thermo.validity,
        )
        return UnitEvaluation(
            request.unit_id,
            (MaterialPortValue(HOT_OUT, hot_out), MaterialPortValue(COLD_OUT, cold_out)),
            (Residual("energy", 0.0, max(duty_w, 1.0), "W"),),
            (),
            (),
            validity,
            (AuditEvidence("heat-exchanger", "Q=epsilon*Q_max; Q_hot=Q_cold"),),
            (
                ("duty", duty),
                ("hot_outlet_temperature", hot_thermo.temperature),
                ("cold_outlet_temperature", cold_thermo.temperature),
            ),
        )


class RadiatorUnit(HeaterUnit):
    def evaluate(self, request: UnitEvaluationRequest) -> UnitEvaluation:
        inlet = _material_input(request, INLET)
        material = self.services.materials[inlet.material_reference_id]
        if not isinstance(material, MaterialReference):
            raise TypeError("material registry contains an invalid entry")
        target = _parameter(self.definition, "outlet_temperature")
        target_state = self._flash_tp(material, inlet.composition, target, inlet.thermo.pressure)
        duty = Quantity(
            inlet.mass_flow.to("kg/s").value
            * (
                target_state.specific_enthalpy.to("J/kg").value
                - inlet.thermo.specific_enthalpy.to("J/kg").value
            ),
            "W",
        )
        radiator_definition = UnitDefinition(
            self.definition.unit_id,
            self.definition.model_id,
            self.definition.name,
            (("duty", duty),),
            self.definition.metadata,
        )
        result = HeaterUnit(radiator_definition, self.services, self.ports).evaluate(request)
        outlet = next(
            value.state
            for value in result.output_port_values
            if isinstance(value, MaterialPortValue)
        )
        rejected_w = abs(
            next(
                value.duty.value
                for value in result.output_port_values
                if isinstance(value, EnergyPortValue)
            )
        )
        if duty.value > 0.0:
            raise ValueError("radiator target temperature must not exceed its inlet temperature")
        emissivity = _parameter(self.definition, "emissivity").to("1").value
        if not 0.0 < emissivity <= 1.0:
            raise ValueError("emissivity must be in (0, 1]")
        mean_temperature = 0.5 * (
            inlet.thermo.temperature.to("K").value + outlet.thermo.temperature.to("K").value
        )
        stefan_boltzmann = 5.670374419e-8
        sink_temperature_k = 3.0
        flux = 2.0 * emissivity * stefan_boltzmann * (mean_temperature**4 - sink_temperature_k**4)
        area = Quantity(rejected_w / flux, "m^2")
        return UnitEvaluation(
            result.unit_id,
            result.output_port_values,
            result.residuals,
            result.diagnostics,
            result.events,
            result.validity,
            result.audit_evidence
            + (
                AuditEvidence(
                    "radiator-area",
                    "A=Q/[2*epsilon*sigma*(T_mean^4-T_sink^4)]",
                    inputs=(
                        ("rejected_duty", Quantity(rejected_w, "W")),
                        ("emissivity", Quantity(emissivity, "1")),
                        (
                            "stefan_boltzmann",
                            Quantity(stefan_boltzmann, "W/(m^2*K^4)"),
                        ),
                        ("mean_temperature", Quantity(mean_temperature, "K")),
                        ("sink_temperature", Quantity(sink_temperature_k, "K")),
                        ("radiative_flux", Quantity(flux, "W/m^2")),
                    ),
                    outputs=(("required_planform_area", area),),
                    assumptions=(
                        "Two radiating sides",
                        "Arithmetic mean fluid temperature represents a uniform surface",
                        "Three-kelvin radiative sink",
                    ),
                    evidence_reference="MODEL-CARD-REFERENCE-RADIATOR-V1ALPHA",
                ),
            ),
            result.metrics + (("required_planform_area", area),),
        )


def register_reference_models(catalog: ModelCatalog) -> None:
    def material_in(identifier: StableId, name: str) -> MaterialPort:
        return MaterialPort(identifier, name, PortDirection.INPUT)

    def material_out(identifier: StableId, name: str) -> MaterialPort:
        return MaterialPort(identifier, name, PortDirection.OUTPUT)

    energy_out = EnergyPort(DUTY, "Duty", PortDirection.OUTPUT, required=False)

    registrations = (
        (
            ModelDescriptor(
                "source",
                (material_out(OUTLET, "Outlet"),),
                ("mass_flow", "temperature", "pressure"),
                required_metadata=("material_id",),
            ),
            SourceUnit,
        ),
        (ModelDescriptor("sink", (material_in(INLET, "Inlet"),)), SinkUnit),
        (
            ModelDescriptor(
                "heater",
                (material_in(INLET, "Inlet"), material_out(OUTLET, "Outlet"), energy_out),
                ("duty",),
            ),
            HeaterUnit,
        ),
        (
            ModelDescriptor(
                "mixer",
                (
                    material_in(INLET_A, "Inlet A"),
                    material_in(INLET_B, "Inlet B"),
                    material_out(OUTLET, "Outlet"),
                ),
            ),
            MixerUnit,
        ),
        (
            ModelDescriptor(
                "splitter",
                (
                    material_in(INLET, "Inlet"),
                    material_out(OUTLET_A, "Outlet A"),
                    material_out(OUTLET_B, "Outlet B"),
                ),
                ("split_fraction",),
            ),
            SplitterUnit,
        ),
        (
            ModelDescriptor(
                "heat_exchanger",
                (
                    material_in(HOT_IN, "Hot inlet"),
                    material_out(HOT_OUT, "Hot outlet"),
                    material_in(COLD_IN, "Cold inlet"),
                    material_out(COLD_OUT, "Cold outlet"),
                ),
                ("effectiveness",),
            ),
            HeatExchangerUnit,
        ),
        (
            ModelDescriptor(
                "radiator",
                (material_in(INLET, "Inlet"), material_out(OUTLET, "Outlet"), energy_out),
                ("outlet_temperature", "emissivity"),
            ),
            RadiatorUnit,
        ),
    )
    for descriptor, unit_type in registrations:
        catalog.register(
            descriptor,
            lambda definition, services, unit_type=unit_type, descriptor=descriptor: unit_type(
                definition, services, descriptor.ports
            ),
        )
