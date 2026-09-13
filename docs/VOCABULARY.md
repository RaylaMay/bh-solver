# Simulator Vocabulary

These terms are normative in documentation, code, schemas, and UI text.

The working product name is **BH solver**. This is a product label, not a change
to schema/package/model IDs or a claim of operational qualification.

| Process-engineering term | Software meaning |
|---|---|
| Case | An immutable `CaseDefinition` containing one flowsheet, registries, specifications, and settings. |
| Draft | A mutable editing session represented on save as an immutable `DraftRevision`. |
| Revision | One immutable snapshot with a parent and ordered change history. |
| Flowsheet | Directed equipment-and-stream topology plus specifications; it contains no UI coordinates. |
| PFD document | Presentation metadata—positions, labels, routes, and viewport—linked to flowsheet IDs. |
| Equipment / unit operation | Independent model with declared typed ports, parameters, equations, limits, and evaluation contract. |
| Stream | A connection that carries a material or energy state between compatible ports. It is not equipment. |
| Material stream | Flow, composition, and thermodynamic state referenced by material and property-package IDs. |
| Energy stream | Signed heat or shaft-power transfer, positive into the receiving unit. |
| Signal stream | Future control or instrumentation value; excluded from `v1alpha` execution. |
| Port | Named, typed connection point owned by one unit instance. |
| Utility | A boundary source or sink represented explicitly by a unit or energy connection. |
| Parameter | Fixed model configuration that is not chosen by the flowsheet solver. |
| Variable | Scalar quantity that the solver may change within declared bounds and scale. |
| Specification | Equation fixing a variable or relationship; includes a target, manipulated variable, and tolerance. |
| Degree of freedom (DOF) | Number of free scalar variables minus independent scalar equations after graph compilation. |
| Residual | Scaled equation error; a converged numerical solution requires all required residual norms within tolerance. |
| Recycle | Directed dependency cycle requiring an initialization and convergence policy. |
| Tear stream | Selected recycle boundary whose state is iterated by the coordinator, never by unit models. |
| Property package | Versioned `ThermoProvider` implementation and its data sources. |
| Flash | Property request using composition and exactly two independent thermodynamic state variables. |
| Model card | Approved specification of equations, assumptions, validity, provenance, verification, and intended use for one model version. |
| Evidence pack | Traceable sources, extracted data/equations, interpretations, licence notes, and uncertainty supporting a model card. |
| Run | One calculation attempt against an immutable case or revision and explicit configuration. |
| Run manifest | Reproducibility record: case hash, code version, package/data versions, solver settings, platform, and timestamps. |
| Run result | Immutable successful or failed calculation record; failure is data, not an exception hidden from the user. |
| Study | Pinch, exergy, sweep, uncertainty, HAZOP, or dynamic analysis consuming immutable case/result inputs. |
| Closure | Independently reported mass, component, and energy imbalance. |
| Numerical convergence | Solver residual criterion only; it does not imply physical or correlation validity. |
| Physical validity | State satisfies universal/model-declared physical constraints. |
| Correlation validity | Inputs lie within the evidence-backed domain of every applied correlation. |
| Extrapolated | Calculation completed outside at least one correlation domain but within a declared safe mathematical extrapolation policy. |
| Approved catalogue | Models that completed evidence, implementation, independent verification, and architecture-steward review. |
| Narrative profile | Explicit mode allowing labelled placeholders and speculative assumptions; it cannot promote a model. |

“Valid” without a qualifier is prohibited in result messages. The UI and reports
must state whether they mean schema, convergence, closure, physical, or correlation
validity.

## DW0 proposed additions

These terms accompany ADR-010, which Rayla May adopted with annotations on
2026-09-11.
Implementation status is recorded separately; terminology does not create a
persisted contract or certify a capability.

| Term | Proposed meaning |
|---|---|
| UIX | Replaceable interaction/presentation adapter; contains no engineering calculations or solver objects. |
| Application command | Versioned, attributable request for one use case, with explicit target identity and typed outcome. |
| Worker | Supervised process executing compile/evaluate work through a negotiated protocol; not an engineering authority separate from the kernel. |
| Engineering content hash | Versioned identity of calculation-affecting inputs; its projection must be specified before implementation and must not redefine existing artifact hashes. |
| Telemetry | Bounded presentation samples/events; never a replacement for complete calculation artifacts. |
| Run lifecycle state | Queued/accepted/running/terminal execution state, separate from convergence, closure and validity. |
| Transcript-first | Record/transcribe/edit workflow whose text is sent to an AI participant only by explicit user action. |
| Parity baseline | Observed browser behaviour plus separately recorded requirement gaps; defects are not desired native behaviour. |
