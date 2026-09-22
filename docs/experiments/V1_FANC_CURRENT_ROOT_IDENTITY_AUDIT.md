# V1 FANC Legacy CATMAID -> Current Root Identity Audit

Status: **READ-ONLY ID MIGRATION PROBE — NO POLARITY UNLOCK**

## Why this layer exists

PR #120 recovered the five Phelps/GridTape author top-hit FANC source cells:

- CATMAID project-2 skeleton 25849
- 25842
- 25856
- 24831
- 25909

All five are author-annotated left-T1 hook chordotonal sensory neurons.

Those numbers are **legacy CATMAID skeleton IDs**. They are not current FANC
segmentation root IDs, MANC body IDs, MaleCNS body IDs, or BANC root IDs.

Searching the decimal number alone is therefore unsafe. For example, another
dataset may legitimately contain a neuron numbered 25849; numeric equality
across namespaces is not identity evidence.

## Official FANC migration path

This probe follows the public FANC tooling rather than inventing a matcher:

1. Read the pinned author FANC-space SWC.
2. Convert SWC nanometres to FANC mip-0 v3 voxels.
3. Reproduce FANC's documented v3 -> v4 inverse-descent mapping using the
   public `fanc_v4_to_v3` transform service.
4. Query FANC's public v4 point -> supervoxel service.
5. First try the public read-only chunkedgraph handle-root endpoint pinned by
   the official FANC Neuroglancer configuration
   (`cave.fanc-fly.com / mar2021_prod`).
6. If that endpoint requires authentication, fall back to
   `CAVEclient("fanc_production_mar2021").chunkedgraph.get_roots()` and
   record the authentication boundary rather than guessing.
7. Report the dominant current root and fraction of sampled skeleton points.

A dominant root is **ID migration evidence only**. It is not a curated
cross-dataset biological identity.

## Cross-dataset guard

The 2025 neck-connective FANC/MANC correspondence resource contains curated
matches for descending/ascending/neck classes, but its exact-token sensory
table does not directly map these five legacy hook CATMAID IDs. An apparent
same-number hit such as a MANC body ID equal to one of the legacy skeleton
numbers must not be treated as a match.

The frozen downstream target remains:

`MaleCNS 911942 -> MANC 97015 -> SNpp41`

## Unlock rule

This audit never changes the polarity gate by itself.

After current FANC root IDs are recovered, a later layer may search official
CAVE/VFB/BANC/cross-connectome metadata for an explicit curated bridge from
one of those current roots to MANC 97015 / SNpp41.

Until then:

- `curated_fanc_to_manc_snpp_bridge_found = false`
- `snpp39_snpp41_polarity_resolved = false`
- `exact_polarity_verified = false`
- Current Calibration remains locked
- runtime stimulation remains locked


## VFB xref fallback

Because the current FANC chunkedgraph may require authentication for root
resolution, the same audit also queries Virtual Fly Brain's public xref API for
each pinned legacy CATMAID skeleton accession. Any returned VFB individual is
followed with `get_term_info` and scanned for explicit FANC/MANC/MaleCNS/BANC
or SNpp41/97015 cross-dataset signals.

This is a curated-metadata fallback, not a morphology matcher. Numeric equality
alone remains non-evidence.


## Observed public result

The evidence workflow resolved all five author SWCs through the public FANC
v3->v4 and point->supervoxel services:

- 25849: 48/48 sampled points -> non-zero supervoxels
- 25842: 48/48
- 25856: 48/48
- 24831: 48/48
- 25909: 48/48

Current root resolution is blocked for 5/5 cells by the CAVE authentication
boundary. The direct chunkedgraph route does not provide a usable anonymous
root payload, and the official CAVEclient fallback reports AuthException.

VFB reverse-xref was also audited with explicit database scoping. Unfiltered
numeric accessions collide with legitimate MANC/MaleCNS IDs and are therefore
non-evidence. With `db=catmaid_fanc` and
`db=catmaid_fanc_JRC2018VF`, the five legacy IDs produce **0 FANC xref
hits**.

Therefore the public evidence currently reaches:

`legacy Phelps FANC skeleton -> current FANC supervoxels`

but not:

`legacy Phelps FANC skeleton -> current FANC root -> MANC 97015 / SNpp41`.

This is an external-auth / missing-curated-xref boundary, not evidence against
SNpp41 itself.
