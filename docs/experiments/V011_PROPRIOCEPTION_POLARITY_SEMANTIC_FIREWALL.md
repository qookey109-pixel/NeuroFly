# V0.11 Proprioception — systematic-type polarity semantic firewall

Status: **REVIEW_REQUIRED**

This stage continues from the verified `SNpp39` / `SNpp41` hook-direction evidence boundary. It does not reopen current calibration and does not add MaleCNS proprioceptive stimulation.

## Why this layer exists

NeuroFly already has a virtual-body receptor contract with engineering channels named:

- `hook_extension`
- `hook_flexion`
- `club_motion`
- `club_vibration`

For the two hook channels, **extension/flexion describes the sign of the private virtual femur-tibia joint motion**. It does not mean that a MaleCNS systematic type has been directly identified as that biological tuning class.

The strongest current type-level hypotheses remain:

- `SNpp39 ≈ extension-sensitive hook`
- `SNpp41 ≈ flexion-sensitive hook`

The evidence level is `PHYSIOLOGY_SUPPORTED_INFERENCE`, not a direct author/type crosswalk.

## Semantic firewall

`proprioception_polarity_semantics.py` creates a control-plane-only contract.

The systematic types are represented by opaque identities:

- `hook_direction_channel_A -> SNpp39`
- `hook_direction_channel_B -> SNpp41`

Their candidate functions are retained as metadata, but all of the following stay false:

- `authoritative_polarity`
- `runtime_routable`
- `systematic_type_polarity_resolved`
- `current_calibration_authorized`
- `stimulation_enabled`
- `runtime_transduction_enabled`
- `promotion_ready`
- `neural_payload_eligible`

The engineering receptor channels have `systematic_type_binding = null`.

This means there is **no executable alias** such as:

```text
hook_extension -> SNpp39
hook_flexion   -> SNpp41
```

even though that is the current physiology-supported candidate.

## Neural boundary

The semantic contract is control-plane evidence, not sensation. The Neural Context Firewall now validates any `proprioception` modality against the existing FeCO receptor contract. A semantic-control payload therefore cannot be inserted under `proprioception`, and a new top-level key such as `proprioception_semantics` is rejected as a non-sensory field.

The existing delayed receptor-domain proprioception path is unchanged.

## Promotion rule

A future version may create an executable systematic-type mapping only after the evidence gate is replaced by a frozen direct crosswalk or equivalent direct type-level physiology evidence.

That future change must be separately reviewed and must not silently reinterpret the v0.11 inference as direct evidence.

## Scope

- semantic/control-plane hardening only
- no new receptor mechanics
- no virtual-body dynamics change
- no SNpp39/SNpp41 current
- no current calibration
- no runtime systematic-type routing
- no decoder/reward/learning change
- no automatic merge
