# V0.11 Proprioception — Offline Curated Identity Receipt Intake

Status: **REVIEW_REQUIRED / receipt not provided**

Base: Draft PR #76, exact head `e6a2b99f27c6ba93286cc007c97ab5c4c60e539d`.

## Goal

Prepare a reproducible offline intake path for a future authorized NeuronBridge expert-curated identity result without storing login credentials, JWTs, Authorization headers, or any other secret in NeuroFly.

This stage does not obtain a curated result. It freezes how a later result must be captured, hashed, normalized, and reviewed.

## Current state

`receipt_state = NOT_PROVIDED`

The upstream provenance gate remains:

`AUTHENTICATED_CURATED_SOURCE_REQUIRED`

No exact authorized curated result or independently verified immutable annotation-archive receipt has been supplied to this stage.

## Accepted capture methods

A future receipt may originate only from:

1. `authorized-neuronbridge-session`
2. `verified-immutable-annotation-archive`

The validator does not perform login, does not call the protected endpoint, and does not bypass authorization. It accepts only an offline receipt created after lawful/authorized access or from a separately verified immutable archive object.

## Secret-free receipt rule

A valid receipt must explicitly record:

- `authorization_header_stored = false`
- `credentials_or_tokens_stored = false`

The receipt stores scientific provenance, not credentials.

The whole raw response and every accepted normalized record must have SHA-256 receipts. A source/table version and capture time must also be present.

## Exact functional anchors

The intake preserves the direct physiology anchors already frozen upstream.

### Hook flexion

Accepted exact driver anchors:

- `GMR21D12-GAL4`
- `VT038873-p65ADZ + R32H08-GAL4.DBD`

### Hook extension

Accepted exact driver anchor:

- `VT018774-p65ADZ + VT040547-GAL4.DBD`

A single enhancer component is insufficient. For example, `VT018774-p65ADZ` alone cannot stand in for the exact extension split intersection.

An immutable equivalent line identifier may be used only if a separate reviewed equivalence receipt SHA-256 accompanies it.

## Curated record requirements

Every accepted record must include:

- functional direction (`hook_flexion` or `hook_extension`)
- reviewed driver reference
- queried identifier
- dataset
- region
- curated confidence annotation
- annotator/source
- target cell type
- raw-item SHA-256

The current gate requires:

- confidence exactly `Confident`
- region exactly VNC
- target type only `SNpp39` or `SNpp41`
- both direction classes represented
- all records within one direction agree on target type
- flexion and extension form a pure two-type bijection

## Handling disagreement with the existing inference

The validator deliberately does **not** force the existing circuit-supported hypothesis.

If a structurally valid future curated receipt supports:

- extension → `SNpp39`
- flexion → `SNpp41`

it reports:

`VALID_RECEIPT_REVIEW_REQUIRED`

If a structurally valid receipt instead supports the opposite bijection, it is not discarded merely because it conflicts with the current inference. It reports:

`VALID_RECEIPT_CONFLICT_REVIEW_REQUIRED`

This preserves falsifiability. A conflict requires biological/evidence review rather than silently rewriting or rejecting evidence.

## Synthetic tests are not evidence

Unit tests use clearly synthetic records only to exercise schema, hash, bijection, confidence, region, secret-exclusion, and conflict behavior. Synthetic fixtures must never be interpreted as a real NeuronBridge result.

## No automatic polarity resolution

Even a structurally valid future receipt produced by this validator does not itself set:

- `direct_crosswalk_found = true`
- `polarity_resolved = true`
- `promotion_ready = true`

A later, separate frozen evidence-review stage must inspect the real immutable receipt and explicitly decide whether it satisfies the biological direct-crosswalk gate.

## Hard locks

This stage keeps:

- `direct_crosswalk_found=false`
- `polarity_resolved=false`
- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`
- `runtime_gating_authorized=false`
- `neural_payload_eligible=false`
- `promotion_ready=false`

No runtime wiring, receptor encoding, public-state expansion, stimulation, current injection, learning behavior, authorization bypass, or automatic merge is introduced.
