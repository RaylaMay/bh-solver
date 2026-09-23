"""Existing browser draft persistence format plus immutable scientific repository ports.

DW1 retains legacy normalization, revision naming and write semantics. Atomic
browser saves, recovery and admission manifests remain explicit DW4 work.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Literal, ParamSpec, TypeVar, cast

from bh_sim.boundary.contracts import (
    CalculatedRunDto,
    DiagnosticDto,
    EquipmentResultOverlayDto,
    EquipmentResultRowDto,
    OverlaysDto,
    PlotDefinitionDto,
    PreparedRevisionDto,
    ProcessBalanceDto,
    ResultSelectionDto,
    RunAttemptRecord,
    RunViewDto,
    SeriesDataPointDto,
    SeriesDescriptorDto,
    StreamPropertyDto,
    StreamResultOverlayDto,
    StreamResultRowDto,
    WorkbookDto,
)
from bh_sim.core import (
    CaseDefinition,
    EnergyPortValue,
    MaterialPortValue,
    Quantity,
    RunResult,
    UnitEvaluation,
)
from bh_sim.core.json_codec import contract_digest, contract_from_json
from bh_sim.persistence import PersistenceStore

from .drafts import DraftRepository as DraftRepository
from .drafts import DraftRepositoryAdapter as DraftRepositoryAdapter
from .engineering import read_prepared_revision, run_to_view

_Validity = Literal["VALID", "EXTRAPOLATED", "INVALID", "UNKNOWN"]
_P = ParamSpec("_P")
_R = TypeVar("_R")


def _sanitize_index_failure(method: Callable[_P, _R]) -> Callable[_P, _R]:
    """Translate SQLite details into the neutral runtime port-failure category."""

    @wraps(method)
    def wrapped(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        try:
            return method(*args, **kwargs)
        except sqlite3.Error as error:
            raise RuntimeError("artifact index operation failed") from error

    return wrapped


def _clean_id(raw: object) -> str:
    s = str(raw)
    while s.startswith("unit:") or s.startswith("port:"):
        if s.startswith("unit:") or s.startswith("port:"):
            s = s[5:]
    return s


class ArtifactRepositoryAdapter:
    """Scientific JSON reconstruction and immutable persistence behind a port."""

    def __init__(self, store: PersistenceStore) -> None:
        self.store = store

    @_sanitize_index_failure
    def save_inputs(self, prepared: PreparedRevisionDto) -> None:
        revision = read_prepared_revision(prepared)
        self.store.save_case(revision.case)
        self.store.save_revision(revision)

    @_sanitize_index_failure
    def save_run(self, result: CalculatedRunDto) -> None:
        run = contract_from_json(result.canonical_json)
        if not isinstance(run, RunResult):
            raise TypeError("calculated artifact is not RunResult")
        if run_to_view(run) != result.view:
            raise ValueError("run view does not match canonical artifact")
        self.store.save_run(run)

    @_sanitize_index_failure
    def load_run(self, run_id: str) -> RunViewDto:
        return run_to_view(self.store.load_run(run_id))

    @_sanitize_index_failure
    def latest_valid_run(self, case_id: str) -> RunViewDto | None:
        result = self.store.load_latest_valid_run(case_id)
        return run_to_view(result) if result is not None else None

    @_sanitize_index_failure
    def record_attempt(self, attempt: RunAttemptRecord) -> RunAttemptRecord:
        return self.store.record_attempt(attempt)

    @_sanitize_index_failure
    def load_attempt(self, attempt_id: str) -> RunAttemptRecord | None:
        return self.store.get_attempt(attempt_id)

    @_sanitize_index_failure
    def list_attempts(self, case_id: str | None = None) -> tuple[RunAttemptRecord, ...]:
        return self.store.list_attempts(case_id)

    @_sanitize_index_failure
    def reconcile_startup_attempts(self) -> tuple[RunAttemptRecord, ...]:
        return self.store.reconcile_startup_attempts()

    @_sanitize_index_failure
    def promote_staged_run(
        self,
        staged_path: str,
        *,
        expected_run_id: str | None = None,
        expected_case_id: str | None = None,
        expected_revision_id: str | None = None,
        expected_hash: str | None = None,
    ) -> RunViewDto:
        staged_file = Path(staged_path)
        if not staged_file.exists():
            raise FileNotFoundError(f"staged artifact does not exist: {staged_path}")
        raw_bytes = staged_file.read_bytes()
        if expected_hash is not None:
            actual_hash = hashlib.sha256(raw_bytes).hexdigest()
            if actual_hash != expected_hash:
                raise ValueError(
                    f"staged artifact hash mismatch: expected {expected_hash}, got {actual_hash}"
                )
        raw_json = raw_bytes.decode("utf-8")
        run = contract_from_json(raw_json)
        if not isinstance(run, RunResult):
            raise TypeError("staged artifact is not RunResult")
        if expected_run_id is not None and str(run.run_id) != expected_run_id:
            raise ValueError(
                f"staged run_id mismatch: expected {expected_run_id}, got {run.run_id}"
            )
        if expected_case_id is not None and str(run.case_id) != expected_case_id:
            raise ValueError(
                f"staged case_id mismatch: expected {expected_case_id}, got {run.case_id}"
            )
        if expected_revision_id is not None:
            actual_rev = str(run.revision_id) if run.revision_id is not None else None
            if actual_rev != str(expected_revision_id):
                raise ValueError(
                    f"staged revision_id mismatch: expected {expected_revision_id}, "
                    f"got {actual_rev}"
                )
        if run.revision_id:
            rev = self.store.load_revision(run.revision_id)
            if rev is None:
                raise ValueError(f"staged run refers to unknown revision {run.revision_id}")
        view = run_to_view(run)
        self.store.save_run(run)
        return view

    def _resolve_run(self, case_id: str, run_id: str | None) -> RunResult | None:
        if run_id:
            try:
                return self.store.load_run(run_id)
            except KeyError:
                return None
        runs = self.store.list_runs(case_id)
        if not runs and not case_id.startswith("case:"):
            runs = self.store.list_runs(f"case:{case_id}")
        if runs:
            return self.store.load_run(runs[-1][0])
        res = self.store.load_latest_valid_run(case_id)
        if res is None and not case_id.startswith("case:"):
            res = self.store.load_latest_valid_run(f"case:{case_id}")
        return res

    def _resolve_case(self, run: RunResult) -> CaseDefinition | None:
        if run.revision_id:
            rev = self.store.load_revision(run.revision_id)
            if rev is not None:
                return rev.case
        return self.store.load_case(run.case_id)

    def _resolve_selection(self, case_id: str, run: RunResult | None) -> ResultSelectionDto:
        effective_case_id = str(run.case_id) if run is not None else case_id
        runs = self.store.list_runs(effective_case_id)
        if not runs and not effective_case_id.startswith("case:"):
            runs = self.store.list_runs(f"case:{effective_case_id}")
        latest_id = runs[-1][0] if runs else None

        latest_valid = self.store.load_latest_valid_run(effective_case_id)
        if latest_valid is None and not effective_case_id.startswith("case:"):
            latest_valid = self.store.load_latest_valid_run(f"case:{effective_case_id}")
        latest_valid_id = str(latest_valid.run_id) if latest_valid else None

        if run is None:
            return ResultSelectionDto(
                case_id=case_id,
                active_run_id=None,
                latest_run_id=latest_id,
                latest_valid_run_id=latest_valid_id,
                is_stale=False,
            )
        is_stale = bool(latest_id and str(run.run_id) != latest_id)
        return ResultSelectionDto(
            case_id=case_id,
            active_run_id=str(run.run_id),
            latest_run_id=latest_id,
            latest_valid_run_id=latest_valid_id,
            is_stale=is_stale,
            convergence=run.convergence.name,
            closure=run.closure.name,
            physical_validity=cast(_Validity, run.physical_validity.name),
            correlation_validity=cast(_Validity, run.correlation_validity.name),
        )

    def _build_workbook(
        self,
        run: RunResult,
        case: CaseDefinition | None,
        selection: ResultSelectionDto | None,
    ) -> WorkbookDto:
        port_values: dict[tuple[str, str], object] = {}
        unit_evals: dict[str, UnitEvaluation] = {}
        for ev in run.unit_evaluations:
            uid_str = str(ev.unit_id)
            clean_uid = uid_str.removeprefix("unit:")
            unit_evals[uid_str] = ev
            unit_evals[clean_uid] = ev
            for val in ev.output_port_values:
                pid_str = str(val.port_id)
                clean_pid = pid_str.removeprefix("port:")
                port_values[(uid_str, pid_str)] = val
                port_values[(clean_uid, pid_str)] = val
                port_values[(uid_str, clean_pid)] = val
                port_values[(clean_uid, clean_pid)] = val

        stream_rows: list[StreamResultRowDto] = []
        if case is not None and case.connections:
            for conn in case.connections:
                sid = str(conn.connection_id)
                clean_sid = sid.removeprefix("connection:")
                s_unit = str(conn.source_unit_id)
                clean_s_unit = s_unit.removeprefix("unit:")
                s_port = str(conn.source_port_id)
                clean_s_port = s_port.removeprefix("port:")
                t_unit = str(conn.target_unit_id)
                clean_t_unit = t_unit.removeprefix("unit:")
                t_port = str(conn.target_port_id)
                clean_t_port = t_port.removeprefix("port:")
                val = (
                    port_values.get((s_unit, s_port))
                    or port_values.get((clean_s_unit, s_port))
                    or port_values.get((s_unit, clean_s_port))
                    or port_values.get((clean_s_unit, clean_s_port))
                )
                if isinstance(val, MaterialPortValue):
                    fluid = str(val.state.material_reference_id)
                    m_flow = val.state.mass_flow.to("kg/s").value
                    t_k = val.state.thermo.temperature.to("K").value
                    p_pa = val.state.thermo.pressure.to("Pa").value
                    h_j_kg = val.state.thermo.specific_enthalpy.to("J/kg").value
                    v_frac = sum(
                        p.fraction
                        for p in val.state.thermo.phases
                        if "vapor" in p.phase.lower() or "gas" in p.phase.lower()
                    )
                    props = [StreamPropertyDto("enthalpy_flow", m_flow * h_j_kg, "W")]
                    for p in val.state.thermo.phases:
                        if p.density is not None:
                            props.append(
                                StreamPropertyDto(
                                    f"{p.phase}_density",
                                    p.density.to("kg/m^3").value,
                                    "kg/m^3",
                                )
                            )
                        if p.heat_capacity is not None:
                            props.append(
                                StreamPropertyDto(
                                    f"{p.phase}_cp",
                                    p.heat_capacity.to("J/(kg*K)").value,
                                    "J/(kg*K)",
                                )
                            )
                    stream_rows.append(
                        StreamResultRowDto(
                            stream_id=clean_sid,
                            tag=clean_sid,
                            from_unit_id=clean_s_unit,
                            from_port=clean_s_port,
                            to_unit_id=clean_t_unit,
                            to_port=clean_t_port,
                            fluid=fluid,
                            mass_flow_kg_s=m_flow,
                            temperature_k=t_k,
                            pressure_pa=p_pa,
                            enthalpy_j_kg=h_j_kg,
                            vapor_fraction=v_frac,
                            properties=tuple(props),
                        )
                    )
                elif isinstance(val, EnergyPortValue):
                    duty_w = val.duty.to("W").value
                    stream_rows.append(
                        StreamResultRowDto(
                            stream_id=clean_sid,
                            tag=clean_sid,
                            from_unit_id=clean_s_unit,
                            from_port=clean_s_port,
                            to_unit_id=clean_t_unit,
                            to_port=clean_t_port,
                            fluid="Energy",
                            mass_flow_kg_s=None,
                            temperature_k=None,
                            pressure_pa=None,
                            enthalpy_j_kg=None,
                            vapor_fraction=None,
                            properties=(StreamPropertyDto("duty", duty_w, "W"),),
                        )
                    )
                else:
                    stream_rows.append(
                        StreamResultRowDto(
                            stream_id=clean_sid,
                            tag=clean_sid,
                            from_unit_id=clean_s_unit,
                            from_port=clean_s_port,
                            to_unit_id=clean_t_unit,
                            to_port=clean_t_port,
                            fluid=None,
                            mass_flow_kg_s=None,
                            temperature_k=None,
                            pressure_pa=None,
                            enthalpy_j_kg=None,
                            vapor_fraction=None,
                            properties=(),
                        )
                    )
        else:
            for (u_id, p_id), val in port_values.items():
                sid = f"s-{u_id}-{p_id}"
                if isinstance(val, MaterialPortValue):
                    stream_rows.append(
                        StreamResultRowDto(
                            stream_id=sid,
                            tag=sid,
                            from_unit_id=u_id,
                            from_port=p_id,
                            to_unit_id=None,
                            to_port=None,
                            fluid=str(val.state.material_reference_id),
                            mass_flow_kg_s=val.state.mass_flow.to("kg/s").value,
                            temperature_k=val.state.thermo.temperature.to("K").value,
                            pressure_pa=val.state.thermo.pressure.to("Pa").value,
                            enthalpy_j_kg=val.state.thermo.specific_enthalpy.to("J/kg").value,
                            vapor_fraction=None,
                            properties=(),
                        )
                    )

        equipment_rows: list[EquipmentResultRowDto] = []
        if case is not None and case.units:
            for u in case.units:
                uid = str(u.unit_id)
                clean_uid = uid.removeprefix("unit:")
                ev = unit_evals.get(uid) or unit_evals.get(clean_uid)
                duty_w = None
                delta_p_pa = None
                diags = ()
                props: list[StreamPropertyDto] = [
                    StreamPropertyDto(p[0], p[1].value, p[1].unit) for p in u.parameters
                ]
                if ev is not None:
                    conv = run.convergence.name
                    closure = run.closure.name
                    phys = ev.validity.name
                    corr = ev.validity.name
                    diags = tuple(
                        DiagnosticDto(
                            d.code,
                            d.message,
                            cast(Literal["info", "warning", "error"], d.severity),
                            str(d.subject_id) if d.subject_id else None,
                        )
                        for d in ev.diagnostics
                    )
                    for m_name, m_qty in ev.metrics:
                        props.append(StreamPropertyDto(m_name, m_qty.value, m_qty.unit))
                        if m_name in ("duty", "heat_duty") and duty_w is None:
                            duty_w = m_qty.to("W").value
                    for v in ev.output_port_values:
                        if isinstance(v, EnergyPortValue) and duty_w is None:
                            duty_w = v.duty.to("W").value
                else:
                    conv = "NOT_RUN"
                    closure = "NOT_CHECKED"
                    phys = "UNKNOWN"
                    corr = "UNKNOWN"
                equipment_rows.append(
                    EquipmentResultRowDto(
                        unit_id=clean_uid,
                        label=u.name or clean_uid,
                        model_id=u.model_id,
                        duty_w=duty_w,
                        delta_p_pa=delta_p_pa,
                        convergence=conv,
                        closure=closure,
                        physical_validity=phys,
                        correlation_validity=corr,
                        diagnostics=diags,
                        properties=tuple(props),
                    )
                )
        else:
            for uid, ev in unit_evals.items():
                duty_w = None
                for v in ev.output_port_values:
                    if isinstance(v, EnergyPortValue):
                        duty_w = v.duty.to("W").value
                clean_uid = uid.removeprefix("unit:")
                equipment_rows.append(
                    EquipmentResultRowDto(
                        unit_id=clean_uid,
                        label=clean_uid,
                        model_id="",
                        duty_w=duty_w,
                        delta_p_pa=None,
                        convergence=run.convergence.name,
                        closure=run.closure.name,
                        physical_validity=ev.validity.name,
                        correlation_validity=ev.validity.name,
                        diagnostics=(),
                        properties=(),
                    )
                )

        balances: list[ProcessBalanceDto] = []
        for b in run.balances:
            b_type = "MASS" if "mass" in b.name.lower() else "ENERGY"
            inlet_tot = 0.0
            outlet_tot = 0.0
            duty_tot = 0.0
            if case is not None:
                if b_type == "MASS":
                    for u in case.units:
                        if u.model_id == "source":
                            ev = unit_evals.get(str(u.unit_id))
                            if ev:
                                inlet_tot += sum(
                                    v.state.mass_flow.to("kg/s").value
                                    for v in ev.output_port_values
                                    if isinstance(v, MaterialPortValue)
                                )
                        elif u.model_id == "sink":
                            for c in case.connections:
                                if str(c.target_unit_id) == str(u.unit_id):
                                    up = port_values.get(
                                        (str(c.source_unit_id), str(c.source_port_id))
                                    )
                                    if isinstance(up, MaterialPortValue):
                                        outlet_tot += up.state.mass_flow.to("kg/s").value
                else:
                    for u in case.units:
                        if u.model_id == "source":
                            ev = unit_evals.get(str(u.unit_id))
                            if ev:
                                inlet_tot += sum(
                                    v.state.mass_flow.to("kg/s").value
                                    * v.state.thermo.specific_enthalpy.to("J/kg").value
                                    for v in ev.output_port_values
                                    if isinstance(v, MaterialPortValue)
                                )
                        elif u.model_id == "sink":
                            for c in case.connections:
                                if str(c.target_unit_id) == str(u.unit_id):
                                    up = port_values.get(
                                        (str(c.source_unit_id), str(c.source_port_id))
                                    )
                                    if isinstance(up, MaterialPortValue):
                                        outlet_tot += (
                                            up.state.mass_flow.to("kg/s").value
                                            * up.state.thermo.specific_enthalpy.to("J/kg").value
                                        )
                        ev = unit_evals.get(str(u.unit_id))
                        if ev:
                            duty_tot += sum(
                                v.duty.to("W").value
                                for v in ev.output_port_values
                                if isinstance(v, EnergyPortValue)
                            )
            balances.append(
                ProcessBalanceDto(
                    balance_type=b_type,
                    inlet_total=inlet_tot,
                    outlet_total=outlet_tot,
                    generation_or_duty=duty_tot,
                    residual=b.residual.value,
                    tolerance=b.tolerance.value,
                    status=b.status.name,
                    units=b.residual.unit,
                )
            )

        diags = tuple(
            DiagnosticDto(
                d.code,
                d.message,
                cast(Literal["info", "warning", "error"], d.severity),
                str(d.subject_id) if d.subject_id else None,
            )
            for d in run.diagnostics
        )

        return WorkbookDto(
            case_id=str(run.case_id),
            run_id=str(run.run_id),
            flowsheet_id=str(run.compiled_id),
            convergence=run.convergence.name,
            closure=run.closure.name,
            physical_validity=run.physical_validity.name,
            correlation_validity=run.correlation_validity.name,
            streams=tuple(stream_rows),
            equipment=tuple(equipment_rows),
            balances=tuple(balances),
            diagnostics=diags,
            selection=selection,
        )

    def _build_plot(
        self,
        run: RunResult,
        case: CaseDefinition | None,
        plot_kind: str,
        unit_id: str | None,
    ) -> PlotDefinitionDto:
        port_values: dict[tuple[str, str], object] = {}
        unit_evals: dict[str, UnitEvaluation] = {}
        for ev in run.unit_evaluations:
            uid_str = str(ev.unit_id)
            c_uid = _clean_id(uid_str)
            for k in (uid_str, c_uid, f"unit:{c_uid}", f"unit:unit:{c_uid}"):
                unit_evals[k] = ev
            for val in ev.output_port_values:
                pid_str = str(val.port_id)
                c_pid = _clean_id(pid_str)
                for u_key in (uid_str, c_uid, f"unit:{c_uid}", f"unit:unit:{c_uid}"):
                    for p_key in (pid_str, c_pid, f"port:{c_pid}"):
                        port_values[(u_key, p_key)] = val

        if plot_kind == "RESIDUAL_CONVERGENCE":
            series_pts: list[SeriesDataPointDto] = []
            if run.solver_result.iterations:
                for it in run.solver_result.iterations:
                    series_pts.append(
                        SeriesDataPointDto(
                            float(it.iteration),
                            it.residual_norm,
                            f"Iter {it.iteration}",
                        )
                    )
            elif run.solver_result.final_residuals:
                for idx, r in enumerate(run.solver_result.final_residuals):
                    series_pts.append(SeriesDataPointDto(float(idx + 1), abs(r.value), r.name))

            return PlotDefinitionDto(
                plot_id=f"plot-{run.run_id}-residuals",
                title=f"Solver Convergence Trace · Run {run.run_id}",
                x_label="Iteration",
                y_label="Residual Norm ||r||",
                plot_kind="RESIDUAL_CONVERGENCE",
                series=(
                    SeriesDescriptorDto(
                        "residual_norm",
                        "Residual Norm ||r||",
                        "Iteration",
                        "Residual",
                        "solid",
                        "#D19A66",
                        tuple(series_pts),
                    ),
                ),
                run_id=str(run.run_id),
                unit_id=None,
                provenance_hash=contract_digest(run),
                notes=(
                    f"Solver status: {run.solver_result.status.name} · {run.solver_result.message}"
                ),
            )

        # Default: T_Q or thermal profiles
        if unit_id:
            c_unit = _clean_id(unit_id)
            ev = (
                unit_evals.get(unit_id)
                or unit_evals.get(c_unit)
                or unit_evals.get(f"unit:{c_unit}")
                or unit_evals.get(f"unit:unit:{c_unit}")
            )
            unit_def = (
                next(
                    (
                        u
                        for u in case.units
                        if _clean_id(str(u.unit_id)) == c_unit
                        or u.name == unit_id
                        or _clean_id(u.name) == c_unit
                    ),
                    None,
                )
                if case
                else None
            )
            if ev is not None:
                model_id = unit_def.model_id if unit_def else ""
                metrics_dict = dict(ev.metrics)
                duty_w: float | None = None
                duty_val = metrics_dict.get("duty") or metrics_dict.get("heat_duty")
                if isinstance(duty_val, Quantity):
                    duty_w = duty_val.to("W").value
                else:
                    for v in ev.output_port_values:
                        if isinstance(v, EnergyPortValue):
                            duty_w = v.duty.to("W").value
                            break
                if duty_w is None and unit_def is not None:
                    for p_name, p_qty in unit_def.parameters:
                        if p_name in ("duty", "heat_duty") and isinstance(p_qty, Quantity):
                            duty_w = p_qty.to("W").value
                            break

                series: list[SeriesDescriptorDto] = []
                notes = "Steady-state point-state profile between inlet and outlet states."
                if model_id == "heat_exchanger":
                    hot_out_t: float | None = None
                    hot_out_val = metrics_dict.get("hot_outlet_temperature")
                    if isinstance(hot_out_val, Quantity):
                        hot_out_t = hot_out_val.to("K").value
                    else:
                        for v in ev.output_port_values:
                            if isinstance(v, MaterialPortValue) and "hot" in str(v.port_id).lower():
                                hot_out_t = v.state.thermo.temperature.to("K").value
                                break

                    cold_out_t: float | None = None
                    cold_out_val = metrics_dict.get("cold_outlet_temperature")
                    if isinstance(cold_out_val, Quantity):
                        cold_out_t = cold_out_val.to("K").value
                    else:
                        for v in ev.output_port_values:
                            if (
                                isinstance(v, MaterialPortValue)
                                and "cold" in str(v.port_id).lower()
                            ):
                                cold_out_t = v.state.thermo.temperature.to("K").value
                                break

                    hot_in_t: float | None = None
                    cold_in_t: float | None = None
                    if case:
                        for c in case.connections:
                            if _clean_id(str(c.target_unit_id)) == c_unit:
                                s_uid = _clean_id(str(c.source_unit_id))
                                s_pid = _clean_id(str(c.source_port_id))
                                up = (
                                    port_values.get((s_uid, s_pid))
                                    or port_values.get((f"unit:{s_uid}", s_pid))
                                    or port_values.get((f"unit:unit:{s_uid}", s_pid))
                                    or port_values.get(
                                        (str(c.source_unit_id), str(c.source_port_id))
                                    )
                                )
                                if isinstance(up, MaterialPortValue):
                                    t_port = str(c.target_port_id).lower()
                                    if "hot" in t_port or "in-0" in t_port:
                                        hot_in_t = up.state.thermo.temperature.to("K").value
                                    elif "cold" in t_port or "in-1" in t_port:
                                        cold_in_t = up.state.thermo.temperature.to("K").value

                    if (
                        hot_in_t is not None
                        and hot_out_t is not None
                        and cold_in_t is not None
                        and cold_out_t is not None
                        and duty_w is not None
                    ):
                        hot_pts = (
                            SeriesDataPointDto(0.0, hot_in_t, "Hot In"),
                            SeriesDataPointDto(duty_w, hot_out_t, "Hot Out"),
                        )
                        cold_pts = (
                            SeriesDataPointDto(0.0, cold_in_t, "Cold In"),
                            SeriesDataPointDto(duty_w, cold_out_t, "Cold Out"),
                        )
                        series.append(
                            SeriesDescriptorDto(
                                "hot_stream",
                                "Hot Stream (T-Q)",
                                "W",
                                "K",
                                "solid",
                                "#E06C75",
                                hot_pts,
                            )
                        )
                        series.append(
                            SeriesDescriptorDto(
                                "cold_stream",
                                "Cold Stream (T-Q)",
                                "W",
                                "K",
                                "solid",
                                "#61AFEF",
                                cold_pts,
                            )
                        )
                    else:
                        notes = (
                            "Inlet/outlet stream temperatures or heat duty "
                            "unavailable for heat exchanger."
                        )
                    title = f"{unit_def.name if unit_def else c_unit} · T-Q Diagram"
                elif model_id == "radiator":
                    t_out = next(
                        (
                            v.state.thermo.temperature.to("K").value
                            for v in ev.output_port_values
                            if isinstance(v, MaterialPortValue)
                        ),
                        None,
                    )
                    t_in: float | None = None
                    if case:
                        for c in case.connections:
                            if _clean_id(str(c.target_unit_id)) == c_unit:
                                s_uid = _clean_id(str(c.source_unit_id))
                                s_pid = _clean_id(str(c.source_port_id))
                                up = (
                                    port_values.get((s_uid, s_pid))
                                    or port_values.get((f"unit:{s_uid}", s_pid))
                                    or port_values.get((f"unit:unit:{s_uid}", s_pid))
                                    or port_values.get(
                                        (str(c.source_unit_id), str(c.source_port_id))
                                    )
                                )
                                if isinstance(up, MaterialPortValue):
                                    t_in = up.state.thermo.temperature.to("K").value
                                    break
                    if t_in is not None and t_out is not None and duty_w is not None:
                        pts = (
                            SeriesDataPointDto(0.0, t_in, "Inlet"),
                            SeriesDataPointDto(abs(duty_w), t_out, "Outlet"),
                        )
                        series.append(
                            SeriesDescriptorDto(
                                "radiator_cooling",
                                "Radiator Cooling Curve",
                                "W",
                                "K",
                                "solid",
                                "#98C379",
                                pts,
                            )
                        )
                    else:
                        notes = "Inlet/outlet temperatures or duty unavailable for radiator."
                    title = f"{unit_def.name if unit_def else c_unit} · Radiator Cooling"
                else:
                    t_out_val = metrics_dict.get("outlet_temperature") or metrics_dict.get(
                        "temperature"
                    )
                    if isinstance(t_out_val, Quantity):
                        t_out = t_out_val.to("K").value
                    else:
                        t_out = next(
                            (
                                v.state.thermo.temperature.to("K").value
                                for v in ev.output_port_values
                                if isinstance(v, MaterialPortValue)
                            ),
                            None,
                        )
                    t_in = None
                    if case:
                        for c in case.connections:
                            if _clean_id(str(c.target_unit_id)) == c_unit:
                                s_uid = _clean_id(str(c.source_unit_id))
                                s_pid = _clean_id(str(c.source_port_id))
                                up = (
                                    port_values.get((s_uid, s_pid))
                                    or port_values.get((f"unit:{s_uid}", s_pid))
                                    or port_values.get((f"unit:unit:{s_uid}", s_pid))
                                    or port_values.get(
                                        (str(c.source_unit_id), str(c.source_port_id))
                                    )
                                )
                                if isinstance(up, MaterialPortValue):
                                    t_in = up.state.thermo.temperature.to("K").value
                                    break
                    if t_in is not None and t_out is not None and duty_w is not None:
                        pts = (
                            SeriesDataPointDto(0.0, t_in, "Inlet"),
                            SeriesDataPointDto(abs(duty_w), t_out, "Outlet"),
                        )
                        series.append(
                            SeriesDescriptorDto(
                                "thermal_profile",
                                "Thermal Profile",
                                "W",
                                "K",
                                "solid",
                                "#E5C07B",
                                pts,
                            )
                        )
                    else:
                        notes = f"Inlet/outlet temperatures or duty unavailable for {c_unit}."
                    title = f"{unit_def.name if unit_def else c_unit} · Thermal Profile"

                return PlotDefinitionDto(
                    plot_id=f"plot-{run.run_id}-{c_unit}",
                    title=title,
                    x_label="Heat Transferred Q (W)",
                    y_label="Temperature T (K)",
                    plot_kind="T_Q",
                    series=tuple(series),
                    run_id=str(run.run_id),
                    unit_id=c_unit,
                    provenance_hash=contract_digest(run),
                    notes=notes,
                )

        workbook = self._build_workbook(run, case, None)
        pts_all = [
            SeriesDataPointDto(float(i + 1), s.temperature_k, s.tag)
            for i, s in enumerate(workbook.streams)
            if s.temperature_k is not None
        ]
        return PlotDefinitionDto(
            plot_id=f"plot-{run.run_id}-process",
            title=f"Whole-Process Temperatures · Run {run.run_id}",
            x_label="Stream Index",
            y_label="Temperature T (K)",
            plot_kind="T_Q",
            series=(
                SeriesDescriptorDto(
                    "process_t",
                    "Stream Temperatures",
                    "Stream #",
                    "K",
                    "scatter",
                    "#61AFEF",
                    tuple(pts_all),
                ),
            ),
            run_id=str(run.run_id),
            unit_id=None,
            provenance_hash=contract_digest(run),
            notes="Measured stream temperatures across process flowsheet.",
        )

    @_sanitize_index_failure
    def get_workbook(self, case_id: str, run_id: str | None = None) -> WorkbookDto:
        run = self._resolve_run(case_id, run_id)
        if run is None:
            raise KeyError(f"No run found for case {case_id}")
        case = self._resolve_case(run)
        selection = self._resolve_selection(case_id, run)
        return self._build_workbook(run, case, selection)

    @_sanitize_index_failure
    def get_overlays(self, case_id: str, run_id: str | None = None) -> OverlaysDto:
        run = self._resolve_run(case_id, run_id)
        if run is None:
            selection = ResultSelectionDto(
                case_id=case_id,
                active_run_id=None,
                latest_run_id=None,
                latest_valid_run_id=None,
                is_stale=False,
            )
            return OverlaysDto(
                case_id=case_id,
                run_id=None,
                streams=(),
                equipment=(),
                selection=selection,
            )
        case = self._resolve_case(run)
        selection = self._resolve_selection(case_id, run)
        workbook = self._build_workbook(run, case, selection)
        stream_overlays = tuple(
            StreamResultOverlayDto(
                stream_id=row.stream_id,
                tag=row.tag,
                temperature_k=row.temperature_k,
                pressure_pa=row.pressure_pa,
                mass_flow_kg_s=row.mass_flow_kg_s,
                vapor_fraction=row.vapor_fraction,
                is_valid=bool(
                    row.temperature_k is not None
                    and run.physical_validity.name in ("VALID", "EXTRAPOLATED")
                ),
            )
            for row in workbook.streams
        )
        equipment_overlays = tuple(
            EquipmentResultOverlayDto(
                unit_id=row.unit_id,
                convergence=row.convergence,
                closure=row.closure,
                physical_validity=row.physical_validity,
                correlation_validity=row.correlation_validity,
                duty_w=row.duty_w,
                delta_p_pa=row.delta_p_pa,
            )
            for row in workbook.equipment
        )
        return OverlaysDto(
            case_id=case_id,
            run_id=str(run.run_id),
            streams=stream_overlays,
            equipment=equipment_overlays,
            selection=selection,
        )

    @_sanitize_index_failure
    def get_plot_data(
        self,
        case_id: str,
        run_id: str | None = None,
        plot_kind: str = "T_Q",
        unit_id: str | None = None,
    ) -> PlotDefinitionDto:
        run = self._resolve_run(case_id, run_id)
        if run is None:
            raise KeyError(f"No run found for case {case_id}")
        case = self._resolve_case(run)
        return self._build_plot(run, case, plot_kind, unit_id)
