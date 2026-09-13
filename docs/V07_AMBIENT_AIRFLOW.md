# V0.7 — Default ambient airflow

Status: **implemented on stacked branch; CI and prepared-runtime validation required before integration**

NeuroFly's mechanosensory pathway is default-on, so the normal curriculum must provide a real environment signal rather than leaving the pathway idle outside isolated smoke tests.

## Policy

The first normal-environment airflow model is:

`neurofly-curriculum-ambient-airflow-v1`

with a fixed normalized world-frame engineering vector:

```json
{"x": 0.0, "y": 1.0}
```

This is intentionally simple. It creates a stable environmental wind reference while NeuroFly's own heading changes the fly-relative antennal response.

The normalized magnitude `1.0` is used because the existing `0.70` crosswind antenna-load proxy then produces `0.7 × calibrated current 10.0 = 7.0` on the targeted JO channels, which lies inside the already demonstrated prepared-MaleCNS response condition. A weaker `0.6` environment vector would yield only `4.2` current on crosswind channels, below a previously observed no-spike calibration condition. This is an engineering compatibility choice, **not** a claim about natural Drosophila wind speed.

The vector is **not** derived from:

- food position;
- enemy position;
- maze route;
- target coordinates;
- rewards;
- the next desired action;
- curriculum success/failure.

Therefore it cannot function as a hidden solution oracle.

## Neural path

The normal curriculum path is now:

```text
fixed ambient world airflow
        ↓
fly heading
        ↓
virtual antennal deflection
        ↓
strict bilateral JO-C / JO-E payload
        ↓
MaleCNSBrain default-on current routing
        ↓
prepared MaleCNS
```

The regular runtime snapshot exposes only:

```json
{
  "antennal_mechanosensation": {
    "model": "neurofly-antennal-mechanosensation-v0.1",
    "available": true,
    "left": {"jo_c": 0.7, "jo_e": 0.0},
    "right": {"jo_c": 0.0, "jo_e": 0.7}
  }
}
```

for the canonical initial RIGHT-facing pose.

The exact world airflow vector is **not** present in the normal runtime snapshot passed to the brain. It is retained only in persistence metadata so experiment state can record which environment policy produced the sensory stream.

## Egocentric behavior

With the same fixed world wind:

- RIGHT-facing canonical pose → left JO-C `0.7`, right JO-E `0.7`;
- UP-facing pose → bilateral JO-E `1.0`.

The environment therefore supplies one stable physical condition while the sensory representation changes with the fly's own body orientation.

## Why start with a fixed field

A fixed field is useful as the first normal environment because it is:

- deterministic;
- cheap;
- checkpoint-reproducible;
- independent of target truth;
- easy to inspect for privilege leaks;
- sufficient to keep the mechanosensory pathway continuously meaningful;
- aligned with the frozen current-routing response range already demonstrated in prepared MaleCNS.

It is not intended to be the final aerodynamic model.

## Deferred biological/environment upgrades

Future versions may add:

- spatially varying wind;
- turbulence and gusts;
- wall occlusion / channeling;
- odor plume advection by wind;
- temporal antennal dynamics;
- vibration / JO-A/JO-B channels.

Those upgrades should be versioned separately and must preserve the rule that the nervous system receives transduced fly-accessible signals rather than solved world truth.

## Scientific boundary

This ambient field is an **environment engineering model**. It does not establish that the chosen vector or magnitude corresponds to a measured natural Drosophila wind condition. The already-calibrated JO-C/JO-E runtime remains an engineered proxy pending future biological and behavioral validation.
