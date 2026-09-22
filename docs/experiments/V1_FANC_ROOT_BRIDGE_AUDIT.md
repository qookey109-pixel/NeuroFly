# V1 FANC Legacy CATMAID -> Current Root Bridge Audit

Status: **READ-ONLY EVIDENCE PROBE — NO POLARITY UNLOCK**

## Why this layer exists

PR #120 recovered the author/source identities behind the five Phelps/GridTape
R21D12 EM-LM top hits:

- project59 `515392 -> FANC CATMAID 25849`
- project59 `515366 -> FANC CATMAID 25842`
- project59 `515458 -> FANC CATMAID 25856`
- project59 `511045 -> FANC CATMAID 24831`
- project59 `515617 -> FANC CATMAID 25909`

All five are independently present in the pinned Phelps/GridTape FANC-space
annotation file as left-T1 hook chordotonal sensory neurons.

The unresolved infrastructure edge is now:

`legacy FANC CATMAID skeleton -> current FANC segmentation/root identity`.

This audit does **not** redo NBLAST and does not revisit the old BANC polarity
crosswalk.

## Public mapping contract

The probe mirrors the public `fancr` mapping contract.

Pinned source:

- repository: `flyconnectome/fancr`
- commit: `7b3d429729627d83dad9387f54294272640e87f9`

The published `fancr::fanc_xyz2id()` route is:

1. FANC3 / CATMAID coordinates
2. FANC3 -> FANC4 transform
3. FANC4 point -> supervoxel
4. supervoxel -> current ChunkedGraph root

The probe uses the same public Itanna transform/supervoxel services. Anonymous
root lookup is attempted against the public FANC ChunkedGraph API only after a
published `fancr` canary passes.

## Canary rules

Two independent published `fancr` examples are pinned:

- FANC4 raw `(34495, 82783, 1954)` -> supervoxel
  `73186243730767724`
- that supervoxel -> root `648518346499897667`

The inverse FANC3->FANC4 transform is also checked against the published
coordinate example near:

- FANC3 nm: `(194569.2, 470101.3, 117630)`
- FANC4 raw: `(45224, 109317, 2614)`

A target mapping is not trusted if the relevant canary fails.

## Numeric-ID collision guard

The 2025 neck-connective cross-dataset supplements contain many MANC/FANC IDs,
but numeric equality is not identity across those namespaces.

The probe exact-token checks the FANC sensory-ascending supplement and must not
treat a MANC body such as `25856` as the legacy FANC CATMAID skeleton
`25856`.

This explicitly freezes the earlier collision finding:

**same number != same neuron**.

## Target cells

Author top-five R21D12 hook hits:

| Rank | Legacy FANC CATMAID skeleton | Author NBLAST |
| ---: | ---: | ---: |
| 1 | 25849 | 0.508957 |
| 2 | 25842 | 0.494256 |
| 3 | 25856 | 0.473981 |
| 4 | 24831 | 0.468952 |
| 5 | 25909 | 0.464603 |

Each pinned author SWC is sampled across its arbor, transformed into FANC4, and
queried for supervoxels. If anonymous ChunkedGraph access is available, node
support is aggregated by current root ID.

VFB search is recorded as an independent curated-xref audit, but coincident
numeric identifiers from MaleCNS/MANC are never accepted as a FANC match.

## Interpretation boundary

A reproducible legacy-CATMAID -> current-FANC root mapping is an
**infrastructure crosswalk**, not a biological identity proof.

Even if all five current roots are recovered:

- the rank-1 R21D12 morphology hit is not automatically a curated one-cell
  identity;
- a FANC root is not automatically MANC `97015 / SNpp41`;
- exact flexion/extension polarity remains locked.

The already frozen downstream target remains:

`MaleCNS 911942 -> MANC 97015 -> SNpp41`.

## Governance

Always remain false unless a later independent evidence layer explicitly
satisfies the frozen gate:

- `curated_r21d12_to_specific_fanc_em_identity_found`
- `curated_fanc_to_manc_snpp_bridge_found`
- `exact_polarity_verified`
- `current_calibration_authorized`
- `runtime_stimulation_authorized`
- `privileged_state_bypass_authorized`
