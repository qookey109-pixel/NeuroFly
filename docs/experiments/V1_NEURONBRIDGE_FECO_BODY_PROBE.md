# V1 NeuronBridge FeCO Body-Level Probe

Status: **READ-ONLY EVIDENCE PROBE — NO POLARITY UNLOCK**

## Goal

Probe the last unresolved bridge using Janelia's public NeuronBridge data model:

```
polarity-verified hook driver
        ↓
NeuronBridge LM/EM morphology match
        ↓
dataset-qualified MaleCNS body ID
        ↓
SNpp39 or SNpp41
```

This route does not use BANC metadata or the exhausted BANC matching-table path.

## Body IDs

The probe starts only from MaleCNS bodies for which VFB exposes the same body ID
in both `male-cns:v0.9` and `male-cns:v1.0`.

SNpp39:

- 810041
- 813911
- 814881
- 913886

SNpp41:

- 819524
- 819559
- 911942

This avoids carrying identity through a bare systematic-type string.

## Directional driver tokens

Hook extension:

- `VT018774`
- `VT040547`
- `VT018774-p65ADZ`
- `VT040547-GAL4.DBD`

Hook flexion:

- `VT038873`
- `R32H08`
- `GMR21D12`
- `VT038873-p65ADZ`
- `R32H08-GAL4.DBD`
- `GMR21D12-GAL4`

These come from the functional polarity evidence frozen earlier in the FeCO
research chain.

## Reproducible data path

The probe follows the public Janelia NeuronBridge Python-client pattern:

1. `current.txt`
2. `<version>/config.json`
3. `<version>/metadata/by_body/<body_id>.json`
4. each MaleCNS body's `CDSResults`
5. scan the preserved match records for the polarity-verified driver identities

It also tries direct `metadata/by_line/<line>.json` lookups. A 404 is treated
only as absence of that exact lookup key, never as biological absence.

## Decision rule

The runner is deliberately unable to unlock polarity automatically.

Even an exact driver token in a body-level match is stored only as evidence with
rank/score/provenance fields. A separate scientific review must confirm:

- dataset identity;
- the exact driver identity;
- match rank/score and algorithm provenance;
- consistency across multiple bodies of the same systematic type;
- directional consistency between flexion and extension channels.

Until that review:

- `direct_type_to_polarity_source_found = false`
- `snpp39_snpp41_polarity_resolved = false`
- `exact_polarity_verified = false`
- Current Calibration remains locked
- runtime stimulation remains locked

## Output

GitHub Actions uploads:

`artifacts/neuronbridge_feco_body_probe.json`

as the artifact:

`neuronbridge-feco-body-probe`

The receipt includes the resolved NeuronBridge data version, MaleCNS stores,
direct line lookup statuses, every body metadata lookup, CDS result counts and
any exact directional-driver token hits.
