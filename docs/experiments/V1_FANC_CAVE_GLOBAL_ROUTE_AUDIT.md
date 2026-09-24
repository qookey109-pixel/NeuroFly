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
