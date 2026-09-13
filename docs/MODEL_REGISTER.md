# Model Register

This is the human index for prototype models. None are catalogue-approved; status
follows the [scientific model lifecycle](MODEL_LIFECYCLE.md).

| Model ID / version | Status | Current fidelity | Current check | Important exclusions |
|---|---|---|---|---|
| [`properties.reference_liquid`](model_cards/REFERENCE_LIQUID_V1ALPHA.md) / `v1alpha` | BLOCKED_EVIDENCE | Pure constant-cp illustrative liquid | Independent hand reconstruction and inverse-flash test | Real-fluid identity, pressure effects, mixtures, phase change |
| [`unit.reference_radiator`](model_cards/REFERENCE_RADIATOR_V1ALPHA.md) / `v1alpha` | BLOCKED_EVIDENCE | Target-temperature duty plus mean-temperature two-sided radiation | Independent hand reconstruction to 5.6e-13 relative | Axial T^4 integration, structure, view factors, environment, damage |
| `thermo.polynomial_liquid` / `0-prototype` | IMPLEMENTED_UNVERIFIED | Single-phase cp(T), constant density | Analytic polynomial integral and inversion tests | Pressure effects, mixtures, phase change |
| `unit.heater_cooler` / `0-prototype` | IMPLEMENTED_UNVERIFIED | Steady enthalpy balance | Exact energy balance | Heat loss, pressure drop, dynamics |
| `unit.counterflow_hx` / `0-prototype` | IMPLEMENTED_UNVERIFIED | Effectiveness with nonlinear enthalpy | Independent hot/cold closure | UA/LMTD, pressure drop, fouling, phase change |
| `unit.solid_radiator` / `0-prototype` | IMPLEMENTED_UNVERIFIED | Segmented radiative sizing | Enthalpy and Stefan–Boltzmann closure | Structure, environment, view obstruction, damage |
| `unit.droplet_radiator` / `0-prototype` | IMPLEMENTED_UNVERIFIED | Monodisperse optically thin flight | Segment enthalpy closure | Spray CFD, shielding, charging, collector mechanics |
| `study.thermal_buffer` / `0-prototype` | IMPLEMENTED_UNVERIFIED | Lumped sensible/latent capacity | Analytic energy balance | Transfer rates, gradients, phase kinetics; null maximum duration means no net accumulation |

Each entry must be updated when model behaviour, evidence, validation, or intended
use changes. Before promotion it must gain an evidence-pack ID, model-card hash,
independent V&V record, declared profiles, and exact code/data version hashes.

Property implementations migrate to the `ThermoProvider` contract described in
[CONTRACTS.md](CONTRACTS.md).
Model-register entries must identify the exact property backend and dataset used
for each reference or validation case.
