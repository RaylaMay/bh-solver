# Reference solid-radiator model card — `v1alpha`

Status: **BLOCKED_EVIDENCE / TEST FIXTURE ONLY**

This is a first-slice software-integration model, not an approved spacecraft
radiator design correlation.

## Specification

For inlet and target outlet enthalpies, signed fluid duty is:

```text
Q_fluid = m_dot * (h_out - h_in)
Q_rejected = abs(Q_fluid)
```

The target must not exceed the inlet temperature. Required two-sided planform area
uses an arithmetic mean fluid temperature:

```text
T_mean = (T_in + T_out) / 2
q'' = 2 * emissivity * sigma * (T_mean^4 - T_sink^4)
A = Q_rejected / q''
```

Constants and assumptions:

- `sigma = 5.670374419e-8 W/(m²·K⁴)`.
- `T_sink = 3 K`.
- Two unobstructed radiating sides.
- Uniform radiator surface represented by the arithmetic mean fluid temperature.
- No structure, conduction drop, view obstruction, degradation, environment,
  pressure drop, pumping, phase change, or damage.

## Verification fixture

For 1 kg/s of the reference liquid cooling from 800 K to 500 K at emissivity 0.9:

- rejected duty: 300,000 W;
- mean-temperature flux: 18,219.5509171 W/m²;
- required planform area: 16.4658284589 m².

Independent reconstruction differed from the implementation by less than
`5.6e-13` relative.

## Model-form limitation

The arithmetic-mean-temperature fourth power is not equal to integrating `T^4`
along a radiator with a temperature gradient. For a linear 800–500 K profile, the
integrated comparison gives approximately 14.8733 m², 10.71% below this fixture.
That discrepancy is a declared model-form approximation, not numerical error.

## Promotion blockers

- Primary evidence for geometry, surface properties, environment, view factors,
  axial temperature distribution, structural mass, degradation, and damage.
- A reviewed distributed-temperature or segmented model and limiting cases.
- Independent thermal and radiative closure, uncertainty, and material limits.
