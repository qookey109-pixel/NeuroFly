# V1 FeCO Lee 2024 public hook-flexion root recovery

## Result

A public static export of the FANC FeCO annotation table was recovered from `sagrawal/Lee_2024`:

`synapse_tables/feco_annotation_table.csv`

At source commit `4328b1d5549749f1014c4d73cccc0c5241d98ae4`, the table contains 13 valid T1L rows explicitly annotated `hook_flx`.

The exact rows are frozen in:

`data/research/feco/fanc_v840_t1l_hook_flx_roots.csv`

This closes the previously missing **FANC-side root enumeration**.

## Recovered root set

- 648518346476657526
- 648518346507233352
- 648518346480125925
- 648518346514448583
- 648518346509569667
- 648518346490237960
- 648518346496671612
- 648518346494264434
- 648518346480666625
- 648518346494932914
- 648518346494933426
- 648518346481857725
- 648518346517348645

## Independent reuse check

Global GitHub code search shows these roots are reused in other FANC analysis products, notably `tuthill-lab/Lesser_Azevedo_2023`, supporting that they are real FANC v840 scientific identifiers rather than NeuroFly-generated candidates.

A targeted search of `htem/BANC-project` and `murthylab/banc_connectivity_analysis` did not recover an explicit `SNpp41 -> one of these FANC roots` mapping.

The frozen BANC root `720575941508169089` remains explicitly `SNpp41` in BANC inventory, but no public cell-level bridge to one of the 13 FANC hook-flexion roots was recovered in this pass.

## Updated evidence chain

Confirmed:

`MaleCNS 911942 -> SNpp41`

`BANC 720575941508169089 -> SNpp41`

`FANC v840 -> 13 explicit T1L hook_flx pt_root_id values`

Still unresolved:

`SNpp41 / MaleCNS 911942 -> specific FANC hook_flx pt_root_id`

## Gate state

- FANC hook_flx root enumeration: **resolved**
- SNpp41 -> specific FANC hook_flx root: unresolved
- bridge_is_type_exclusive: false
- bridge_is_curated_identity: false
- exact_polarity_verified: false
- Current Calibration: locked
- Runtime stimulation: locked

## Next route

The remaining search space is now bounded to the 13 recovered FANC roots. Search independent cross-dataset match products for an explicit mapping from MaleCNS/BANC SNpp41 to one of these roots. Do not reopen candidate 20201 or morphology-only acceptance.
