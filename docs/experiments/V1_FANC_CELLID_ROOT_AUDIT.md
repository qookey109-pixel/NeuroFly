# V1 FANC cell-ID → root audit

## Question

Does the authoritative FANC `cell_ids_v2` table map the BANC-reported FANC
`cell_id=20201` to one of the five current FANC `hook_flx` roots frozen by
PR #124?

## Why version 1116 matters

The public BANC↔FANC product is named `banc_fanc_1116_nblast.feather`, and the
author pipeline documents its target as FANC v1.116. Therefore the audit queries
materialization **1116** first. It also queries the latest anonymously
discoverable materialization when the server exposes one.

This avoids treating a current segmentation split/merge as evidence that an
older author match did or did not exist.

## Exact targets

FANC cell ID:

- `20201`

PR #124 exact Lee `hook_flx` roots:

- `648518346481857725`
- `648518346509569667`
- `648518346494933426`
- `648518346514448583`
- `648518346494264434`

## Queries

For each materialization version the probe performs:

1. exact `id=20201`;
2. exact `user_id=20201` as a schema-compatibility check;
3. reverse exact `pt_root_id IN {five hook_flx roots}`.

Only an exact `cell_ids_v2` row can establish the namespace mapping.

## Fail-closed interpretation

Anonymous HTTP 401/403 **or an HTTP 200 response that redirects to / embeds a
Google Accounts sign-in interstitial** is recorded as an authorization boundary,
not as a scientific negative result. A 200 HTML login page is never parsed as an
empty successful `cell_ids_v2` query.

Even if `20201` maps exactly to one of the five `hook_flx` roots, the
BANC→FANC NBLAST record remains `validation=false`. Therefore this audit cannot
by itself set `curated_fanc_to_manc_snpp_bridge_found=true`,
`exact_polarity_verified=true`, or open calibration/runtime.

## Observed pre-fix behavior

The first anonymous run returned HTTP 200 for the FANC materialization endpoints,
but the response body was a Google Accounts login page (`accounts.google.com`),
not JSON. Therefore the earlier zero-row result is invalid as scientific evidence.
The corrected probe explicitly classifies this case as an authentication
interstitial and remains fail-closed.


## Public static fallback

Because anonymous CAVE requests currently redirect to a Google Accounts
interstitial, the probe also enumerates the public
`lee-lab_brain-and-nerve-cord-fly-connectome` GCS bucket under FANC-related
prefixes. It records candidate metadata / cell-ID / annotation objects for the
next exact `20201 -> root_id` lookup without requiring a user token.


## Observed result (2026-09-23)

The corrected anonymous audit is fail-closed and reproducible:

- all five CAVE requests were redirected to Google Accounts login HTML;
- `auth_interstitial_response_count = 5`;
- `non_json_success_response_count = 5`;
- `transport_error_count = 0`;
- therefore the earlier apparent zero-row result is **not** scientific negative evidence.

The public GCS fallback was also queried without credentials:

- `compiled_data/fanc_1116/` hierarchy listing succeeded;
- hierarchy `is_truncated = false`;
- direct top-level object count = `0`;
- the only common prefix is
  `compiled_data/fanc_1116/fanc_banc_space_swc/`;
- no metadata / cell-ID / annotation object is exposed at that dataset level.

The broader `compiled_data/fanc` listing is truncated after 1000 objects and is
dominated by SWCs, so it is not used to claim exhaustive absence. The
non-truncated hierarchy listing is the authoritative statement about the
published `fanc_1116` top level.

Result: `cell_id=20201 -> pt_root_id` remains unresolved without authenticated
`cell_ids_v2` access or a separately published static identity table. No
scientific or runtime lock changes.
