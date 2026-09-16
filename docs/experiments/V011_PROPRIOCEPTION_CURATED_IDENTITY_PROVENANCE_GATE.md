# V0.11 Proprioception — Curated Identity Provenance Gate

Status: **REVIEW_REQUIRED / evidence provenance only**

Base: Draft PR #75, exact head `e308dbe815db8c3d65e3d0f03d26eab4387651af`.

## Goal

Separate two NeuronBridge evidence paths that must not be treated as interchangeable:

1. the public versioned NeuronBridge Open Data API containing image metadata and precomputed morphology-search results;
2. the expert-curated Split-GAL4 / cell-type annotation service used by the current NeuronBridge frontend.

This stage exists to prevent a public morphology score from being promoted into a direct biological identity receipt for `SNpp39` or `SNpp41`.

## Public Open Data API

Official repository: `JaneliaSciComp/neuronbridge-data`

Pinned commit:

`0b6c184ce5af4fc6ae3264f8c89ba88c62ef2caa`

The repository documents the production bucket:

`s3://janelia-neuronbridge-data-prod`

and the production pointer observed in the reviewed snapshot is:

`v3_10_0`

The documented public object families include version/config/schema data, published names, references, EM/LM metadata, CDS results, and PPPM results. These are public morphology/search surfaces. The documented bucket structure does not identify expert-curated identity annotations as part of that Open Data API.

Therefore public precomputed morphology output remains useful for candidate discovery and human inspection, but it is **not identity authority** for the SNpp39/SNpp41 polarity gate.

## Expert-curated identity service

Official backend repository: `JaneliaSciComp/neuronbridge-services`

Pinned commit:

`3847c602fcc5e3ae2bae47b7308ee11263ae6cef`

The reviewed service defines:

- endpoint: `GET /curated_matches`
- source table: `janelia-neuronbridge-custom-annotations`
- DynamoDB partition type: `searchString`
- JWT authorizer: `neuronBridgeJwtAuthorizer`
- identity source: `$request.header.Authorization`

The service therefore exposes expert-curated identity records through a provenance path distinct from the public precomputed morphology bucket.

No authenticated exact hook-driver result was obtained in this stage. The project does not bypass the authorizer.

## Curated annotation archive path

Official preprocessing repository: `JaneliaSciComp/neuronbridge-precompute`

Pinned commit:

`e51e7c1ed6523597a7f6f6f9cbe18a53ac4eb1f3`

The reviewed updater documents the curated annotation input columns:

- `Line Name`
- `Dataset`
- `Region`
- `Term`
- `Term type`
- `Annotation`
- `Annotator`

The same updater writes records to `janelia-neuronbridge-custom-annotations` and archives the input file under:

`s3://janelia-neuronbridge-annotation/input/<filename>`

This is potentially an independent immutable-receipt route if an exact relevant object can later be obtained and hashed. In the present audit, public readability of that archive was **not verified**, and no exact hook-driver archive object was obtained.

The absence of such an object here is not evidence that no curated match exists.

## Frontend separation

Official frontend repository: `JaneliaSciComp/neuronbridge`

Pinned commit:

`18d97306372d27322482208432663f9f2b6b52a8`

The reviewed frontend presents curated matches separately from computed matches and exposes curated confidence, anatomical region, matched cell/body identity, and source. This reinforces the provenance boundary: computed morphology and expert-curated identity are separate evidence classes.

## Current conclusion

`AUTHENTICATED_CURATED_SOURCE_REQUIRED`

The existing directional candidates remain unchanged:

- `SNpp39 ≈ extension-sensitive hook` — `PHYSIOLOGY_SUPPORTED_INFERENCE`
- `SNpp41 ≈ flexion-sensitive hook` — `PHYSIOLOGY_SUPPORTED_INFERENCE`

The following remain unresolved:

- `SNpp39.direct_directional_tuning = null`
- `SNpp41.direct_directional_tuning = null`
- `direct_crosswalk_found = false`
- `polarity_resolved = false`

## What can satisfy the blocker later

A later frozen receipt must come from either:

1. the authenticated expert-curated identity service, or
2. an equivalent immutable annotation archive object with exact provenance.

It must cover both hook direction classes and preserve the predeclared PR #75 requirements: exact driver identity, `Confident` curation, VNC context, source/annotator, target type `SNpp39`/`SNpp41`, pure bijection, no conflicting curated assignment, source version/table identity, and immutable content hash.

## Hard locks

This stage does **not** authorize:

- login/authentication bypass;
- treating public morphology scores as identity truth;
- executable `hook_extension/flexion -> SNpp39/SNpp41` mapping;
- proprioceptive current calibration;
- stimulation;
- runtime transduction;
- runtime predictive-inhibition gating;
- neural-payload eligibility;
- model or evidence promotion;
- automatic merge.

All such locks remain closed.
