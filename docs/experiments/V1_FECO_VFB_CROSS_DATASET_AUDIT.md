# V1 FeCO VFB cross-dataset identity audit

## Scope

Continue from the Dallmann FANC v840 audit and test whether a public independent ontology/cross-dataset source closes the cell-level bridge between the frozen MaleCNS SNpp41 target and a specific FANC hook-flexion neuron.

## Public identity evidence

Virtual Fly Brain independently exposes both MaleCNS and BANC neurons under a shared ontology/classification layer.

For the frozen MaleCNS target:

- MaleCNS body `911942`
- type / mancType: `SNpp41`
- classification: femoral chordotonal hook neuron

VFB also exposes BANC roots explicitly annotated `SNpp41`, including:

- `BANC_626:720575941508169089`: middle-leg hook chordotonal organ neuron; Primary Cell Type `SNpp41`
- `BANC_626:720575941612455676`: front-leg hook chordotonal organ neuron; Primary Cell Type `SNpp41`

This independently strengthens the cross-dataset **type-level** identity: MaleCNS `911942` and multiple BANC cells are classified as SNpp41 / FeCO hook neurons.

## Boundary

The VFB records inspected here do not provide a FANC `feco_axons_v0` root identifier, nor do they assert that MaleCNS `911942` is the same individual cell as a particular FANC v840 `hook_flx` root.

Therefore:

`MaleCNS 911942 -> SNpp41 -> hook class`

is independently supported, but:

`MaleCNS 911942 -> specific FANC pt_root_id -> hook_flx`

remains unresolved.

Type-level ontology agreement is not substituted for the PR #134 acceptance rule requiring a reproducible cell-level mapping.

## Gate state

- MaleCNS 911942 = SNpp41: independently corroborated
- BANC SNpp41 roots: independently corroborated
- FANC v840 hook_flx annotation namespace: confirmed by prior audit
- specific SNpp41 -> FANC hook_flx root bridge: unresolved
- bridge_is_type_exclusive: false
- bridge_is_curated_identity: false
- computed_morphology_is_sufficient_for_exact_polarity: false
- exact_polarity_verified: false
- Current Calibration: locked
- Runtime stimulation: locked

## Next route

Search for an explicit FANC v840 `feco_axons_v0` export or cross-dataset match product that contains the actual `hook_flx` `pt_root_id` rows. Do not reopen retired candidate 20201 or morphology-only matching.
