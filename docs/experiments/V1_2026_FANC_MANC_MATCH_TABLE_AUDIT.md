# V1 2026 author FANC↔MANC match-table audit

## New source

Guo et al. (2026), *iScience* 29(3):114902,
**Segmentally repeated ventral nerve cord circuits drive different leg rubbing
behaviors in Drosophila grooming**.

- DOI: `10.1016/j.isci.2026.114902`
- PII: `S2589004226002774`
- PMCID: `PMC12933626`
- publisher supplement: **Table S2 — Full dataset of matching FANC and MANC
  neuron identification and the post-synaptic downstream**

This source is newer than the earlier NeuroFly FANC/MANC audits and is useful
because it explicitly publishes an author-level cross-connectome match table.

## Question

Does Table S2 contain an exact row connecting any frozen NeuroFly FeCO target?

Exact targets:

- MANC body `97015`
- systematic type `SNpp41`
- BANC-reported FANC candidate cell ID `20201`
- PR #124 FANC `hook_flx` roots:
  - `648518346481857725`
  - `648518346509569667`
  - `648518346494933426`
  - `648518346514448583`
  - `648518346494264434`

## Method

The GitHub Actions probe attempts publisher and PMC supplement mirrors, accepts
only a structurally valid XLSX, parses it with Python's standard ZIP/XML stack,
and exact-matches every cell.

A row is elevated only to **candidate bridge evidence** if the same author row
contains:

- `97015` plus a FANC target; or
- `SNpp41` plus a FANC target.

No substring, fuzzy, morphology, proximity, or same-number inference is allowed.

## Governance

Even a positive same-row hit is frozen for semantic review first. This audit
does not automatically change:

- `curated_fanc_to_manc_snpp_bridge_found`
- `exact_polarity_verified`
- calibration authorization
- runtime stimulation authorization
- privileged-state bypass authorization


## Observed result (2026-09-23)

The publisher supplement was fetched successfully from the Elsevier CDN:

- chosen URL: `https://ars.els-cdn.com/content/image/1-s2.0-S2589004226002774-mmc2.xlsx`
- byte count: `113470`
- structurally valid XLSX: `true`
- parse error: `null`

Workbook coverage:

- sheet: `LegPN Downstream`
- rows scanned: `1001`
- cells scanned: `36036`
- exact target hits: `0`

No exact occurrence was found for any frozen target:

- `97015`
- `SNpp41`
- `20201`
- any of the five PR #124 `hook_flx` roots

Interpretation is deliberately narrow: Table S2 is a valid author FANC↔MANC
matching dataset, but this workbook is scoped to the LegPN/downstream circuit.
The zero-hit result therefore means only that this particular author table does
not cover the NeuroFly FeCO bridge targets. It is **not** evidence that no
FANC↔MANC SNpp41/FeCO identity exists elsewhere.
