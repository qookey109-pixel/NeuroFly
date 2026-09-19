# V1 R21D12 Hook-Flexion Bridge — Run #2 Analysis

Status: **STRONG BIDIRECTIONAL FUNCTIONAL-DRIVER MORPHOLOGY EVIDENCE — EXACT POLARITY STILL LOCKED**

## Why R21D12 matters

The earlier component-level NeuronBridge probe in PR #117 could not use
`GMR21D12` because that was not the NeuronBridge lookup key.

Virtual Fly Brain exposes the expression pattern as:

- construct: `P{GMR21D12-GAL4}`
- VFB expression pattern: `VFBexp_FBtp0058328`
- FlyLight / NeuronBridge accession: **`R21D12`**

Dallmann et al. use `GMR21D12-GAL4` to label **hook flexion neurons**.
Therefore this route is stronger than matching an isolated split-GAL4
hemidriver component: the source line itself has a published directional
identity.

## Run provenance

Bidirectional probe run:

- GitHub Actions run: `35446074417`
- head: `ee21ef0475f4c3a12aaf093be84536fb4348bcc8`
- NeuronBridge data version: `v3_10_0`
- artifact ID: `10584904264`
- digest:
  `sha256:0e8c329cfbac91572878bf59ebfe6e8cf73494f57d2f52170392d3c4b62534e2`

The exact `R21D12` lookup succeeded:

- HTTP 200
- 81 line records

## Forward direction: MaleCNS body -> R21D12 LM

Best exact R21D12 hits:

| target | rank | normalized score |
| --- | ---: | ---: |
| `SNpp41:911942` | **2** | **36269.43** |
| `SNpp39:810041` | 32 | 33111.457 |
| `SNpp39:913886` | 143 | 24719.102 |

The strongest frozen target is therefore `SNpp41:911942`.

## Reverse direction: R21D12 LM -> MaleCNS body

The reverse search confirms the same directional pattern:

| target | best reverse rank | normalized score |
| --- | ---: | ---: |
| `SNpp41:911942` | **6** | 28238.342 |
| `SNpp39:810041` | 29 | 33111.457 |
| `SNpp39:913886` | 32 | 17415.73 |

Thus the `SNpp41:911942` enrichment is not an artifact of using only the
EM-body-to-LM search direction.

## Why exact polarity still does not unlock

The evidence is **not type-exclusive**.

The same R21D12 MCFO collection also produces reproducible matches to
`SNpp39:810041` and `SNpp39:913886`.

There is also a segment-composition confound in the frozen target set:

- all three bodies with exact R21D12 hits are **mesothoracic**;
- all four bodies without exact hits are **metathoracic**.

The hit set is:

- `SNpp39:810041` — mesothoracic, right
- `SNpp39:913886` — mesothoracic, right
- `SNpp41:911942` — mesothoracic, left

The no-hit set is:

- `SNpp39:813911` — metathoracic, left
- `SNpp39:814881` — metathoracic, right
- `SNpp41:819524` — metathoracic, right
- `SNpp41:819559` — metathoracic, right

Therefore the presence/absence pattern cannot be interpreted as a clean
SNpp39-vs-SNpp41 enrichment statistic.

Most importantly, NeuronBridge CDS is a **computed morphology match**, not a
curated assertion that an individual R21D12-labelled cell and a MaleCNS body
are the same biological cell class.

## Evidence update

This is the strongest recovered bridge so far:

`published hook-flexion driver -> exact NeuronBridge line -> single-cell LM -> MaleCNS body`

It strongly strengthens:

`SNpp41 -> hook flexion candidate`

but does not convert it to calibrated truth.

The existing:

`SNpp39 -> hook extension candidate`

is unchanged.

## Governance

Still locked:

- `direct_type_to_polarity_source_found = false`
- `snpp39_snpp41_polarity_resolved = false`
- `exact_polarity_verified = false`
- `current_calibration_authorized = false`
- `runtime_stimulation_authorized = false`
- `privileged_state_bypass_authorized = false`

## Next unlock condition

Do not rerun the same R21D12 computed-match layer.

The next evidence must be one of:

1. a curated/manual cell-level R21D12 -> MaleCNS identity;
2. a type-exclusive functional-driver bridge without segment ambiguity;
3. the exact functional split-GAL4 intersection recovered as a searchable
   single-cell morphology source and mapped reproducibly to MaleCNS.

Machine-readable analysis:

`data/r21d12_flexion_bridge_run2_analysis.json`
