# V1 FeCO Hook Driver Polarity Crosscheck

Status: **EVIDENCE CROSSCHECK ONLY — SYSTEMATIC-TYPE POLARITY GATE REMAINS LOCKED**

This crosscheck advances the unresolved NeuroFly FeCO hook polarity problem without
retrying the exhausted BANC Dataverse / `banc_888_meta.feather` / old matching-table
route.

## What is now directly anchored

The functional hook channels themselves are not ambiguous.

Chen et al. (2021), *Functional architecture of neural circuits for leg
proprioception in Drosophila* (DOI: 10.1016/j.cub.2021.09.035), directly
distinguishes hook flexion and hook extension channels. It also reconstructs a
hook-extension FeCO axon that directly synapses onto 13Bb.

Golding et al. (2023), *Biomechanical origins of proprioceptor feature selectivity
and topographic maps in the Drosophila leg* (DOI: 10.1016/j.neuron.2023.07.009),
independently uses the following directional split-GAL4 lines:

- hook flexion: `VT038873-p65ADZ + R32H08-GAL4.DBD`
- hook extension: `VT018774-p65ADZ + VT040547-GAL4.DBD`

Dallmann et al. (2024), *Presynaptic inhibition selectively suppresses leg
proprioception in behaving Drosophila*, additionally uses:

- `GMR21D12-GAL4` as a hook-flexion driver;
- the same `VT038873 + R32H08` hook-flexion split line;
- the same `VT018774 + VT040547` hook-extension split line.

Therefore the **driver/channel polarity is direct evidence**, not an inference.

## What is still missing

The unresolved step is the cross-dataset bridge:

```
polarity-verified driver / Chen EM hook axon
                    ↓
          MaleCNS systematic type
                    ↓
             SNpp39 or SNpp41
```

The current Male CNS Cell Type Explorer (`male-cns:v1.0`) identifies both
systematic types only as:

- `SNpp39`: AKA **FeCO hook**
- `SNpp41`: AKA **FeCO hook**

It does not add a flexion/extension synonym to either type.

The audited VFB driver records expose FlyLight/NeuronBridge cross-references, but
this crosscheck did not recover an explicit, reproducible result that binds one
of the polarity-verified drivers to `SNpp39` or `SNpp41`. The legacy
`https://neuronbridge.janelia.org/search?q=...` route currently returns 404,
so it is not treated as evidence either way.

No manual visual resemblance is accepted as a type mapping.

## Relationship to PR #113

PR #113 established the strong circuit-consistency candidate:

- `SNpp39 -> hook extension candidate`
- `SNpp41 -> hook flexion candidate`

This crosscheck strengthens the **functional polarity anchor**, but does not
supply the missing systematic-type bridge. Therefore the candidate crosswalk is
unchanged and is not promoted.

## Governance

The following must remain locked:

- `snpp39_snpp41_polarity_resolved = false`
- `exact_polarity_verified = false`
- `current_calibration_authorized = false`
- `runtime_stimulation_authorized = false`
- `privileged_state_bypass_authorized = false`

The new positive fact is only:

- `functional_driver_polarity_verified = true`

## Next unlock condition

The gate can move only when an independently auditable source supplies a direct
bridge such as:

1. a published driver-to-MaleCNS systematic-type match;
2. a stable NeuronBridge/VFB match whose result explicitly identifies
   `SNpp39` or `SNpp41`;
3. a stable body/segment identifier for Chen's directional hook EM axon that can
   be reproduced into a modern MaleCNS systematic type.

Until then, NeuroFly keeps the driver-level direction as verified evidence and
the SNpp39/SNpp41 direction as candidate-only.

Machine-readable state:

`data/feco_hook_driver_polarity_crosscheck_v01.json`
