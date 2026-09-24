# V1 FANC official CAVE global-route audit

## Why this audit exists

PR #126 correctly established that anonymous requests to the historical
`https://cave.fanc-fly.com` route return a Google OAuth interstitial.

However, the pinned CAVEclient source documents a different official route:

1. default global server: `https://global.daf-apis.com`;
2. query InfoService for `fanc_production_mar2021`;
3. read the datastack's `local_server`;
4. construct MaterializationEngine requests on that local server.

This audit follows that exact routing logic without credentials.

## Frozen questions

### Direction table

Dallmann et al. 2025 explicitly use:

- datastack `fanc_production_mar2021`
- materialization `840`
- table `feco_axons_v0`
- cell types `hook_flx / hook_ext`

The audit exact-queries the five PR #124 roots and requires every returned
target row to be `hook_flx`.

### Cell-ID namespace

BANC's public FANC v1.116 NBLAST product reports `match_id=20201`,
`validation=false`, and the BANC pipeline defines this match ID as FANC
`cell_id`.

The same pipeline defines:

`cell_ids_v2 |> distinct(cell_id = id, pt_root_id, ...)`

Therefore the audit exact-queries materialization 1116 for `id=20201` and
reverse-queries the five frozen hook-flexion roots.

## Governance

A successful `20201 -> hook_flx root` result would resolve the FANC namespace
mapping only. Because the BANC->FANC morphology match remains
`validation=false`, it does not by itself establish a curated FANC->MANC
identity or open polarity, calibration, runtime stimulation, or privileged-state
locks.


## Public segment-properties fallback

The BANC pipeline explicitly states that the FANC compiled metadata feather is
not publicly released, but it publishes a Neuroglancer `segment_properties`
JSON generated from the local `fanc_meta.csv`.

Pinned public object:

`imported_meshes/fanc_1116_meshes_elastix_tpsreg_240721/segment_properties/info`

Its IDs are FANC `cell_id` values, labels are `cell_type`, and tags are
derived from the same local FANC metadata. The audit therefore also performs an
exact lookup of `cell_id=20201` in this public object and records its label and
decoded tags. This can add public annotation context but does not by itself
resolve the corresponding FANC root ID.


## Observed result (2026-09-24)

The official anonymous CAVE route is also authentication-blocked:

- `https://global.daf-apis.com/info/api/v2/datastack/full/fanc_production_mar2021`
  returns an HTTP-200 Google Accounts interstitial rather than JSON;
- no `local_server` can therefore be discovered anonymously;
- direct materialization requests against the global server return HTTP 404,
  which is routing evidence only and not a scientific negative result.

The public FANC Neuroglancer segment-properties object is readable without
credentials and is generated from the pipeline's local `fanc_meta.csv`.

For exact `cell_id=20201`:

- found: `true`
- label: `unknown`
- decoded tags: `central neuron`, `right`

This public metadata does **not** support a sensory / chordotonal / hook
identity for cell 20201. Combined with the BANC NBLAST row
(`score=0.1`, `validation=false`, `match_cell_type=null`), cell 20201
must remain an unvalidated morphology candidate and is not accepted as the
FANC identity bridge to SNpp41.

The result also closes the hypothesis that PR #126 failed only because it used
the historical `cave.fanc-fly.com` hostname: the official global InfoService
route is anonymous-auth-blocked as well.
