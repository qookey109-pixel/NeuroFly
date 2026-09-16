# V0.11 Proprioception Cross-Dataset Hook Identity

Status: **REVIEW_REQUIRED**. This stage strengthens only the systematic-type identity of `SNpp39` and `SNpp41` as FeCO hook neurons across public connectome annotations. It does not resolve flexion/extension polarity and does not authorize runtime wiring or current.

## Why this stage exists

Earlier NeuroFly evidence already established a strong circuit-consistent hypothesis:

- `SNpp39 ≈ extension-sensitive hook`
- `SNpp41 ≈ flexion-sensitive hook`

That hypothesis remains `PHYSIOLOGY_SUPPORTED_INFERENCE`, because no exact author-provided functional-driver/systematic-type crosswalk has been frozen.

The exact BANC/FANC matching route was already attempted separately. This stage does not repeat raw BANC object acquisition, Dataverse retrieval, `banc_888_meta.feather`, or NBLAST discovery. Instead, it asks a narrower independent question:

> Do current public VFB annotation records consistently preserve `SNpp39` and `SNpp41` as femoral chordotonal hook systematic types across MaleCNS and BANC examples?

## Public annotation snapshot

Observed on 2026-09-16, representative Virtual Fly Brain records show both systematic types classified as `femoral chordotonal hook neuron`.

### BANC v626

For `SNpp39`, the frozen snapshot includes representative front-, middle-, and hind-leg records:

- `720575941578950133` — front leg — VFB `VFB_001059vs`
- `720575941642643557` — middle leg — VFB `VFB_00104ye2`
- `720575941531825611` — hind leg — VFB `VFB_00105pzq`

For `SNpp41`, the frozen snapshot includes representative front-, middle-, and hind-leg records:

- `720575941460957651` — front leg — VFB `VFB_001069bx`
- `720575941593894102` — middle leg — VFB `VFB_00105597`
- `720575941503646514` — hind leg — VFB `VFB_00105x02`

The BANC records expose `Primary Cell Type` as `SNpp39` or `SNpp41`, a leg-specific hook chordotonal-organ subclass, and the VFB classification `femoral chordotonal hook neuron`.

### MaleCNS

Representative MaleCNS records independently preserve the same systematic-type/hook relationship. The frozen snapshot includes:

- `SNpp39`: bodies `833439`, `913886`, and `813911`
- `SNpp41`: bodies `911942` and `819524`

These public records expose MaleCNS type `SNpp39` or `SNpp41`, chordotonal-organ subclass context, and VFB classification `femoral chordotonal hook neuron`.

## What this supports

This snapshot supports the narrower statement:

- `SNpp39` is consistently annotated as a FeCO hook systematic type in representative MaleCNS and BANC records.
- `SNpp41` is consistently annotated as a FeCO hook systematic type in representative MaleCNS and BANC records.
- BANC examples for both systematic types are represented in front, middle, and hind legs.

This is useful because it reduces the risk that the current NeuroFly polarity hypothesis is being attached to a systematic type that is actually claw, club, or another proprioceptive class in one of the current public connectome annotation surfaces.

## What this does not support

The VFB records inspected here do **not** provide an exact field saying:

- `SNpp39 = hook extension` or `hook flexion`;
- `SNpp41 = hook extension` or `hook flexion`.

Therefore the following remain unchanged:

- `SNpp39.direct_directional_tuning = null`
- `SNpp41.direct_directional_tuning = null`
- `direct_crosswalk_found = false`
- `polarity_resolved = false`

The pre-existing circuit-consistent hypotheses remain metadata only:

- `SNpp39.circuit_consistent_hypothesis = extension`
- `SNpp41.circuit_consistent_hypothesis = flexion`
- evidence level: `PHYSIOLOGY_SUPPORTED_INFERENCE`

## Fail-closed audit

The machine-readable evidence gate fails if:

- either systematic type disappears from either BANC or MaleCNS examples;
- a frozen record is no longer classified as a femoral chordotonal hook neuron;
- BANC front/middle/hind representative coverage is lost for either type;
- a direct flexion/extension tuning value is inserted;
- the existing circuit-consistent hypotheses are silently swapped;
- any current, stimulation, runtime-transduction, runtime-gating, neural-payload, or promotion lock opens.

## Hard locks

- `direct_crosswalk_found=false`
- `polarity_resolved=false`
- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`
- `runtime_gating_authorized=false`
- `neural_payload_eligible=false`
- `promotion_ready=false`

This stage is evidence-only. It changes no receptor encoding, neural handoff, website publication, stimulation path, current calibration, systematic-type routing, decoder, reward, or learning behavior.
