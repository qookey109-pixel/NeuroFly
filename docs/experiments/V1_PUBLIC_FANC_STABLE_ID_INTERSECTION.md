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

## Observed result

GitHub Actions run `36088719107` completed successfully and produced artifact
`public-fanc-stable-id-intersection` (artifact id `10844986476`).

Public FANC `segment_properties`:

- stable FANC IDs: **21,952**
- exact public `hook_flx` stable IDs: **0**
- broader FeCO/sensory-tagged stable IDs: **3,795**
- `cell_id=20201`: label `unknown`, tags `central neuron`, `right`

Public BANC↔FANC compiled NBLAST:

- discovered feather: `nblast/banc_fanc_1116_nblast.feather`
- frozen BANC SNpp41 target rows: **1**
- only `match_id`: `20201`
- score: `0.1`
- validation: `false`
- exact hook-flexion annotation intersection: **0**
- broader FeCO/sensory annotation intersection: **0**

This closes the public stable-ID annotation shortcut for the current SNpp41
candidate set. The only public BANC/FANC candidate is independently annotated
as a right central neuron rather than a sensory/FeCO candidate.

The result strengthens retirement of `20201` as a usable identity bridge, but
does not identify which stable FANC IDs correspond to the 13 frozen
`hook_flx` roots.

## Acceptance boundary

A positive intersection would be useful independent annotation context for a
BANC morphology candidate, but it would not itself be a curated cross-dataset
identity. In particular, `validation=false` remains unvalidated and cannot
open exact polarity, Current Calibration, or Runtime stimulation.

The observed negative intersection is not proof that SNpp41 is not hook-flexion.
It states only that the public compiled BANC/FANC candidate set carries no
independent FANC hook/FeCO/sensory annotation.

## Next route

The remaining public-only route is to inspect whether the pipeline's
root-named FANC source geometry and stable-cell-ID mesh output preserve an exact
same-neuron fingerprint that can recover the namespace mapping by provenance.
This must be treated as namespace recovery only, not morphology-based
scientific promotion.

If that route cannot recover an exact provenance mapping, authenticated
`cell_ids_v2` remains the authoritative required source.

## Locks

- bridge_is_curated_identity: false
- exact_polarity_verified: false
- Current Calibration: locked
- Runtime stimulation: locked
