# V1 public FANC stable-ID intersection audit

## Question

Can the public FANC Neuroglancer metadata narrow or resolve the stable FANC
cell IDs relevant to the frozen BANC SNpp41 query without authenticated CAVE
access?

## Inputs

Public-only:

- FANC v1.116 Neuroglancer `segment_properties`, whose IDs are stable FANC
  `cell_id` values and whose label/tags come from the pipeline's local
  `fanc_meta.csv`.
- public `nblast/` FANC feather products.
- frozen BANC SNpp41 root `720575941508169089`.

## Probe

The audit:

1. enumerates stable FANC IDs whose public label/tag is exactly `hook_flx`;
2. separately records a broader FeCO/sensory candidate set using hook,
   chordotonal, sensory, proprioceptive, mechanosensory, or FeCO annotation
   terms;
3. discovers public FANC NBLAST feather files;
4. extracts candidate rows for the frozen BANC SNpp41 root;
5. intersects the NBLAST `match_id` values with the independently published
   stable-ID annotation sets.

## Acceptance boundary

A positive intersection is useful independent annotation context for a BANC
morphology candidate, but it is not a curated cross-dataset identity. In
particular, `validation=false` remains unvalidated and cannot open exact
polarity, Current Calibration, or Runtime stimulation.

A negative intersection is also not proof that SNpp41 is not hook-flexion; it
only states that the public compiled candidate set does not carry the required
independent FANC annotation.

## Locks

All scientific/runtime promotion locks remain closed.
