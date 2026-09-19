# V1 NeuronBridge FeCO Body Probe — Run #1 Analysis

Status: **STRONG MORPHOLOGY-CONSISTENCY EVIDENCE — EXACT POLARITY STILL LOCKED**

## Execution

The preregistered read-only probe completed successfully:

- GitHub Actions run: `35442954845`
- head: `1a7a2a06f87ec7aae3ab2d1f8b486062da522a0f`
- NeuronBridge data version: `v3_10_0`
- artifact: `neuronbridge-feco-body-probe`
- artifact ID: `10584029271`
- artifact digest:
  `sha256:7ec8366393259cc0a8ef336d33a8eb9c297ab48882d2b15984ee3f64d386696d`

The runner fetched all 7 preregistered MaleCNS bodies and scanned:

- 7 CDS result files
- 16,654 precomputed match records
- 66 exact driver-component token hits

## Main result

### SNpp39

All four bodies prefer an **extension-associated component** by best match rank:

| body | best extension component | rank | score | best flexion component | rank | score |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| 810041 | VT040547 | 115 | 27594.34 | VT038873 | 1100 | 4235.808 |
| 813911 | VT018774 | 873 | 2339.5962 | VT038873 | 1354 | 1072.3925 |
| 814881 | VT018774 | 716 | 6906.961 | VT038873 | 1693 | 1339.9879 |
| 913886 | VT040547 | 69 | 28651.686 | VT038873 | 506 | 11383.21 |

Thus the body-level morphology result is **4/4 consistent** with the existing:

`SNpp39 -> hook extension candidate`

### SNpp41

Two of three bodies prefer a **flexion-associated component** by best match rank:

| body | best flexion component | rank | score | best extension component | rank | score |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| 819524 | VT038873 | 899 | 2951.1582 | VT040547 | 967 | 2591.064 |
| 819559 | VT038873 | 1105 | 2220.9492 | VT040547 | 833 | 3761.0112 |
| 911942 | R32H08 | **9** | **31088.082** | VT040547 | 409 | 10702.281 |

Body `911942` is especially notable:

- R32H08 rank 9
- R32H08 rank 14
- R32H08 rank 16
- VT038873 rank 35
- best extension-associated component only rank 409

This strongly supports the existing:

`SNpp41 -> hook flexion candidate`

but `819559` is a counterexample at the component-morphology level, so the
SNpp41 evidence is not uniform.

## Why this still does not unlock exact polarity

The functional experiments do not define direction using the individual
component lines alone.

The experimentally validated hook-extension split driver is:

`VT018774-p65ADZ x VT040547-GAL4.DBD`

The experimentally validated hook-flexion split driver is:

`VT038873-p65ADZ x R32H08-GAL4.DBD`

Run #1's 66 hits came from:

- 48 `FlyLight Gen1 MCFO`
- 18 `FlyLight Annotator Gen1 MCFO`
- **0 complete Split-GAL4 intersection-library hits**

Direct NeuronBridge line lookup succeeded for the individual names
`VT018774`, `VT040547`, `VT038873`, and `R32H08`, but the exact
hemidriver-qualified names/intersections were not recovered under the tested
lookup keys.

This distinction matters biologically: an intersection can be substantially
more specific than either hemidriver's broad expression pattern. Therefore:

**individual hemidriver morphology match != functional split-GAL4 identity**

## Updated evidence strength

Run #1 materially strengthens the existing candidate because the evidence is
now:

- dataset-qualified;
- body-level;
- reproducible against a frozen NeuronBridge data version;
- directionally patterned across multiple bodies;
- preserved with match rank, normalized score, image ID, slide code and
  artifact digest.

However it remains **morphology-consistency evidence**, not a direct
type-to-polarity annotation.

## Governance

No unlock occurs:

- `direct_type_to_polarity_source_found = false`
- `snpp39_snpp41_polarity_resolved = false`
- `exact_polarity_verified = false`
- `current_calibration_authorized = false`
- `runtime_stimulation_authorized = false`
- `privileged_state_bypass_authorized = false`

## Next narrow target

Do not rerun this component-level probe.

The remaining target is now narrower:

> recover the **complete functional split-GAL4 intersection identity** in
> NeuronBridge/FlyLight (or an equivalent auditable source), then bind that
> complete driver identity to MaleCNS `SNpp39` / `SNpp41` bodies.

Machine-readable analysis:

`data/neuronbridge_feco_body_probe_run1_analysis.json`
