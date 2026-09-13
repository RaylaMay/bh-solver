# Reference liquid model card — `v1alpha`

Status: **BLOCKED_EVIDENCE / TEST FIXTURE ONLY**

This model exists to verify contracts, graph execution, unit conversion, energy
accounting, persistence, and UI behaviour. It does not represent water, tin, or any
other BH working fluid and cannot be promoted into an evidence-backed
catalogue without a new evidence pack and review.

## Specification

- Material ID: `material:reference-coolant`
- Property package ID: `properties:reference-liquid-v1alpha`
- Density: 1000 kg/m³, constant.
- Heat capacity: 1000 J/(kg·K), constant.
- Reference temperature: 298.15 K.
- Specific enthalpy: `h(T) = cp * (T - 298.15 K)`.
- Implemented flashes: `(T,P)` and `(h,P)` for a pure liquid only.
- Pressure has no property effect in this fixture.

The mathematical hard domain is 100–2500 K. The nominal regression-test interval
is 250–1200 K. `VALID` means only that a test-fixture evaluation is within this
declared interval; it does not mean the coefficients are scientifically validated.
Values from the evidence interval to the hard boundary are marked `EXTRAPOLATED`.

## Verification fixture

At 300 K, `h = 1,850 J/kg`. Adding 500 kW to 1 kg/s gives
`h_out = 501,850 J/kg` and `T_out = 800 K`. Cooling that stream to 500 K rejects
300 kW. The independent reconstruction is recorded in the implementation handoff.

## Promotion blockers

- Identify the actual fluid and composition.
- Add primary property sources and data-licence records.
- Fit and independently verify density, enthalpy, phase, vapour-pressure, viscosity,
  and thermal-conductivity behaviour over the intended range.
- Define pressure effects, phase boundaries, extrapolation policy, and uncertainty.
