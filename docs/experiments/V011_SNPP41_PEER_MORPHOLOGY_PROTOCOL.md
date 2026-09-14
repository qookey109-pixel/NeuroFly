# V0.11 SNpp41 Peer-Only Morphology Protocol

Status: **frozen verification PASS**. Body `905407` was not evaluated while this protocol was derived or frozen.

## Goal

Freeze the morphology feature set, normalization, distance metric, and peer-derived acceptance envelope **before** examining body `905407` against the cohort.

The upstream 21-peer SWC cohort is frozen by PR #56. This stage used those 21 peer assets only.

## Frozen upstream authority

Peer SWC cohort receipt SHA256:

`aeba54052eb7a53c1c1e9b7f6bf1a7fb1010baa3023db9b693af9f3e3e6e70d2`

Body `905407` was excluded from protocol construction.

## Descriptor policy

The protocol uses a coarse translation-free topology/geometry descriptor derived from each peer skeleton:

1. `log1p(node_count)`
2. `log1p(branch_points)`
3. `log1p(terminal_nodes)`
4. `log1p(cable_length)`
5. branch-point fraction
6. terminal-node fraction
7. `log1p(mean_edge_length)`
8. `log1p(smallest bbox extent)`
9. `log1p(middle bbox extent)`
10. `log1p(largest bbox extent)`

Bounding-box extents are sorted before use, so absolute left/right atlas position and axis ordering do not directly determine similarity.

This is intentionally a **coarse morphology envelope**, not a full neuron-shape registration or synaptic-connectivity similarity metric.

## Peer-only normalization

For every feature, the 21 peers define:

- center = cohort median;
- scale = `1.4826 × MAD`;
- if MAD collapses, use `IQR / 1.349`;
- if both collapse, use a unit fallback.

No target value can change the center or scale.

## Distance metric

For two descriptor vectors `x` and `y`:

`sqrt(mean(((x_i - y_i) / scale_i)^2))`

The metric was fixed before target evaluation.

## Frozen peer envelope

Each peer was compared to the other 20 peers. Its leave-one-out nearest-neighbor distance was recorded.

Observed peer-only LOO nearest-neighbor distances:

- minimum: `0.162105635450`
- median: `0.416349397622`
- maximum: `1.833618426632`

The frozen future-target acceptance rule is:

`target_nearest_peer_distance <= 1.833618426632`

No percentile, threshold, feature weight, or metric may be changed after seeing body `905407` without opening a new protocol version and rerunning peer-only derivation from scratch.

## Discovery and frozen verification

Discovery workflow run `34825842332` derived the peer-only normalization, leave-one-out distances, and threshold and intentionally returned `DISCOVERY_REQUIRED` because no protocol receipt had yet been frozen.

Frozen protocol receipt SHA256:

`9710b3456c599af24d896a6e9b9f0b577c73cdc0eae6a3ac9260c1baf5ed8c48`

Discovery artifact:

- artifact ID `10340541784`
- ZIP SHA256 `1e75d1f4b8f48b8af295401ce62cb08305576940239b2bdc87e3b8d7226ff570`

Frozen verification workflow run `34825998654` reproduced the exact protocol and completed successfully.

Frozen verification artifact:

- artifact ID `10340148075`
- ZIP SHA256 `36c0d0afb208af0a4eba8843050408ed7c293a5769cdcdbd14c7eba2eacf828e`

The associated general NeuroFly CI run `34825998305` also completed successfully.

## Hard locks

Regardless of result:

- target morphology was not read in this stage;
- `target_morphology_compared=false`;
- `promotion_ready=false`;
- `current_calibration_authorized=false`;
- `stimulation_enabled=false`;
- `runtime_transduction_enabled=false`.

Passing this protocol gate authorizes only a later **read-only target morphology comparison** using the frozen method. It does not authorize proprioceptive current and does not establish `SNpp39/SNpp41 -> extension/flexion` tuning identity.
