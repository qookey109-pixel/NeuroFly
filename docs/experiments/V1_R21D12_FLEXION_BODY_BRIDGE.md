# V1 R21D12 Hook-Flexion Body-Level Bridge Probe

Status: **READ-ONLY EVIDENCE PROBE — NO AUTOMATIC POLARITY UNLOCK**

## Why this probe exists

PR #117 showed strong body-level morphology consistency for the existing
SNpp39/SNpp41 polarity candidate, but its directional hits were individual
split-GAL4 hemidriver components rather than the complete functional
intersection.

A separate route is now available.

Dallmann et al. use the full `GMR21D12-GAL4` driver to label **hook flexion
neurons**. This gives the driver a directional functional/anatomical identity
without requiring reconstruction of the `VT038873 x R32H08` intersection.

Virtual Fly Brain cross-references the `GMR21D12-GAL4` expression pattern to
FlyLight and NeuronBridge under the accession:

`R21D12`

This explains why the earlier exact lookup for `GMR21D12` returned 404.

## Question

Does the polarity-verified `R21D12` LM line produce a reproducible
NeuronBridge morphology match to current MaleCNS `SNpp39` or `SNpp41`
body IDs?

## Frozen target bodies

SNpp39:

- 810041
- 813911
- 814881
- 913886

SNpp41:

- 819524
- 819559
- 911942

These are the same dataset-qualified target bodies frozen in PR #117.

## Data route

The runner follows Janelia's public NeuronBridge object model:

`current.txt -> config.json -> by_line/R21D12.json -> by_body/<id>.json -> CDSResults`

Only exact `image.publishedName == R21D12` matches count.

## Decision rule

The runner cannot unlock polarity automatically.

A positive hit is frozen with body ID, rank, score and image provenance. The
scientific review must then determine whether the body-level morphology match is
strong and specific enough to count as a direct driver-to-type bridge.

Until that review:

- `direct_type_to_polarity_source_found = false`
- `snpp39_snpp41_polarity_resolved = false`
- `exact_polarity_verified = false`
- Current Calibration remains locked
- runtime stimulation remains locked
