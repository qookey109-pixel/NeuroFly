# V0.11 SNpp39 / SNpp41 Hook Direction Evidence

Status: **REVIEW_REQUIRED**. This evidence stage records a strong circuit-consistent directional hypothesis while explicitly refusing to promote it to a direct type-to-physiology crosswalk.

## Upstream morphology result

The body `905407` morphology-envelope audit in PR #58 passed the peer-only, predeclared SNpp41 morphology gate. Its nearest frozen peer was body `817154` at distance `0.452550685717`, below the frozen threshold `1.833618426632`.

That result supports coarse SNpp41 morphology consistency only. It does **not** establish flexion/extension physiology.

## What direct physiology establishes

Published FeCO work separates hook neurons into populations tuned to tibia flexion versus tibia extension. Direct experimental driver context includes:

- hook flexion: `VT038873-p65ADZ + R32H08-GAL4.DBD`
- hook extension: `VT018774-p65ADZ + VT040547-GAL4.DBD`

The current evidence pass has not found an author-provided exact mapping from those functional driver populations to the systematic MaleCNS type names `SNpp39` and `SNpp41`.

## What the MaleCNS circuit predicts

The systematic Male VNC annotation paper identifies both `SNpp39` and `SNpp41` as FeCO hook types and reconstructs opposing tibia premotor effects:

- `SNpp41` is predicted to inhibit tibia flexor/accessory-flexor output while activating tibia extensor output.
- `SNpp39` is predicted to inhibit tibia extensor output and disinhibit flexor/accessory-flexor output.

Independent FeCO sensorimotor connectome work reports the corresponding directional reflex organisation:

- flexion-tuned hook feedback promotes extensor and suppresses flexor output;
- extension-tuned hook feedback promotes flexor and suppresses extensor output.

Taken together, these two independent circuit statements support the **strong inference**:

- `SNpp41 ≈ flexion-tuned hook`
- `SNpp39 ≈ extension-tuned hook`

However, this remains a cross-paper circuit inference. It is **not** treated as a direct author-provided type-to-physiology crosswalk.

## Frozen evidence policy

The machine-readable evidence matrix therefore keeps:

- `SNpp41.direct_directional_tuning = null`
- `SNpp39.direct_directional_tuning = null`
- `SNpp41.circuit_consistent_hypothesis = flexion`
- `SNpp39.circuit_consistent_hypothesis = extension`
- `direct_crosswalk_found = false`

The audit fails closed if a direct directional label is inserted while the direct-crosswalk gate remains unresolved, if the inferred polarity is silently changed, or if any current/stimulation/runtime lock is opened.

## Verification receipt

Workflow `34917475235` passed the dedicated hook-direction evidence gate on branch head `f7c45ace386f5dc808580272f41264a81e267eb4`.

- dedicated evidence workflow: **PASS**
- general NeuroFly CI `34917475125`: **PASS**
- artifact ID: `10377036587`
- artifact ZIP SHA256: `ac361fdce62ca084efd31cbbd004c2f50f7c6f48a0bcfc26b73d366c300035e1`
- result status: `REVIEW_REQUIRED`
- `direct_crosswalk_found=false`
- `current_calibration_authorized=false`

A green workflow here verifies the evidence boundary and hard locks; it does not promote the inferred polarity to direct physiology.

## Promotion requirement

Before directional identity can authorize a prepared MaleCNS current calibration, NeuroFly requires one of:

1. author source data or an annotation table explicitly mapping `SNpp39/SNpp41` to flexion/extension physiology;
2. an exact, independently validated functional-driver ↔ systematic-type morphology crosswalk with an immutable receipt;
3. equivalent direct experimental/type-level evidence.

Circuit consistency by itself is insufficient.

## Hard locks

- `direct_crosswalk_found=false`
- `promotion_ready=false`
- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`

No proprioceptive current is authorized by this evidence stage.
