# V0.11 SNpp41 Peer-Only Morphology Protocol

Status: predeclared peer-only morphology comparison protocol. Body `905407` is **not evaluated** in this stage.

## Goal

Freeze the morphology feature set, normalization, distance metric, and peer-derived acceptance envelope **before** examining body `905407` against the cohort.

The upstream 21-peer SWC cohort is already frozen by PR #56. This stage may use those 21 peer assets only.

## Frozen upstream authority

Peer SWC cohort receipt SHA256:

`aeba54052eb7a53c1c1e9b7f6bf1a7fb1010baa3023db9b693af9f3e3e6e70d2`

Body `905407` is excluded from protocol construction.

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

The metric is fixed before target evaluation.

## Peer envelope

Each peer is compared to the other 20 peers. Its leave-one-out nearest-neighbor distance is recorded.

The future target acceptance rule is predeclared as:

`target_nearest_peer_distance <= max(peer_leave_one_out_nearest_neighbor_distance)`

This means a future target passes this **coarse descriptor gate** only if it is no farther from its nearest frozen peer than the most isolated peer is from its own nearest peer.

No percentile, threshold, feature weight, or metric may be changed after seeing body `905407` without opening a new protocol version and rerunning peer-only derivation from scratch.

## Discovery-first receipt

`EXPECTED_PROTOCOL_RECEIPT_SHA256` starts unset. The first external run must derive the peer-only normalization, leave-one-out distances, and threshold and return `DISCOVERY_REQUIRED` if all structural gates pass.

A later evidence commit may freeze only that exact protocol receipt SHA.

## Hard locks

Regardless of result:

- target morphology is not read in this stage;
- `target_morphology_compared=false`;
- `promotion_ready=false`;
- `current_calibration_authorized=false`;
- `stimulation_enabled=false`;
- `runtime_transduction_enabled=false`.

Passing this protocol gate authorizes only a later **read-only target morphology comparison** using the frozen method. It does not authorize proprioceptive current and does not establish `SNpp39/SNpp41 -> extension/flexion` tuning identity.
