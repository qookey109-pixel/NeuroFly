# V1 FeCO Hook FlyBase Ontology Bridge Audit

Status: **EVIDENCE CROSSCHECK ONLY — POLARITY GATE REMAINS LOCKED**

This audit checks an official ontology route that is independent of the previously
exhausted BANC metadata / matching-table path.

## Official MANC → FBbt mapping

FlyBase's public Drosophila Anatomy Ontology repository contains:

`src/patterns/robot_template_projects/EM_synonyms/manc_cell_type_fbbt_mapping.tsv`

The current checked rows are:

| MANC type | FBbt mapping | Name | Specificity |
| --- | --- | --- | --- |
| `SNpp39` | `FBbt:00049558` | femoral chordotonal hook neuron | `parent_term` |
| `SNpp41` | `FBbt:00049558` | femoral chordotonal hook neuron | `parent_term` |

This is an explicit official bridge from the MANC systematic type names into
FlyBase anatomy ontology, but it does **not** reach directional polarity.

## Directional ontology classes do exist

The same ontology repository separately defines:

- `FBbt:00052632` — femoral chordotonal hook **extension** neuron
- `FBbt:00052633` — femoral chordotonal hook **flexion** neuron

It also defines segment-specific directional classes, including:

- extension: `FBbt:00052634`, `FBbt:00052635`, `FBbt:00052636`
- flexion: `FBbt:00052637`, `FBbt:00052638`, `FBbt:00052639`

Therefore this is not a case where the ontology lacks directional concepts.
The unresolved point is specifically that the official MANC mapping still places
`SNpp39` and `SNpp41` only at the generic hook parent.

## Mapping history check

The mapping file history was checked at updates spanning:

- 2024-08-21
- 2025-02-12
- 2025-05-29
- 2025-12-11
- 2026-07-14

At every checked revision, both SNpp rows remained:

`FBbt:00049558 — femoral chordotonal hook neuron — parent_term`

No checked revision promoted either systematic type to the extension or flexion
ontology child class.

## Interpretation

This is strong **current official negative evidence** for a direct type-to-polarity
annotation.

It strengthens the boundary established by PR #113 and PR #114:

- the functional hook flexion/extension channels are real and directly supported;
- the circuit-consistency candidate remains strong;
- however, the official MANC → FBbt bridge does not currently resolve which
  systematic type is extension versus flexion.

The existing candidate remains unchanged:

- `SNpp39 -> hook extension candidate`
- `SNpp41 -> hook flexion candidate`

No polarity promotion is made.

## Governance

The following remain locked:

- `direct_type_to_polarity_source_found = false`
- `snpp39_snpp41_polarity_resolved = false`
- `exact_polarity_verified = false`
- `current_calibration_authorized = false`
- `runtime_stimulation_authorized = false`
- `privileged_state_bypass_authorized = false`

## Next unlock condition

A future source must explicitly bind `SNpp39` / `SNpp41` to
`FBbt:00052632` / `FBbt:00052633`, or provide an equivalent reproducible
extension/flexion mapping.

Machine-readable state:

`data/feco_hook_flybase_ontology_bridge_audit_v01.json`
