# V1 authenticated FANC stable-ID workflow

## Status

The public-only root-to-stable-ID routes are exhausted. The authoritative next
operation is a read-only authenticated query of FANC `cell_ids_v2` for the 13
frozen v840 T1L `hook_flx` roots.

## Credential contract

FANC's public authentication helper stores a CAVE token at:

`~/.cloudvolume/secrets/cave-secret.json`

and saves the same token under both the global `token` key and the
`fanc_production_mar2021` key.

NeuroFly therefore uses one repository Actions secret:

`FANC_CAVE_TOKEN`

The token value must never be committed, pasted into a workflow input, printed,
or uploaded as an artifact.

## Workflow

`.github/workflows/research-authenticated-fanc-hook-stable-ids.yml`

is deliberately **workflow_dispatch only**. It does not run on push, PR, or
schedule.

At execution it:

1. requires `FANC_CAVE_TOKEN`;
2. materializes a mode-0600 CAVE secret file inside the ephemeral runner;
3. runs `scripts/research/export_fanc_hook_flx_stable_ids.py`;
4. queries only:
   - datastack `fanc_production_mar2021`
   - materialization `840`
   - table `cell_ids_v2`
   - the 13 frozen roots;
5. emits only the root/stable-ID CSV plus a non-secret receipt;
6. deletes the credential file before artifact upload.

## Required success condition

The extractor must recover exactly 13/13 mappings with no duplicate root rows.
A partial mapping exits non-zero and is not promoted.

## Scientific boundary

A successful stable-ID export closes only the FANC namespace subproblem. The
13 stable IDs must then be joined against accepted BANC/FANC cross-dataset
evidence for BANC SNpp41 root `720575941508169089`.

No workflow in this stage may set:

- `bridge_is_curated_identity=true`
- `exact_polarity_verified=true`
- Current Calibration unlocked
- Runtime stimulation unlocked

without the downstream accepted individual-cell bridge.
