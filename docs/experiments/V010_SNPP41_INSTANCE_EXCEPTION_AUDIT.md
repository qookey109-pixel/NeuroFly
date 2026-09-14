# V0.10 SNpp41 Instance Exception Audit

Status: discovery gate; no promotion, current calibration, or stimulation.

## Why this exists

The FeCO hook-pair evidence gate established a reproducible mixed-subclass condition in pinned MaleCNS v1.0:

- 21 `SNpp41` rows are `mechanosensory_proprioceptive / chordotonal organ`;
- 1 `SNpp41` row is `mechanosensory_proprioceptive / leg`.

Type-level sources call `SNpp41` a FeCO hook, but NeuroFly does not discard a row-level annotation conflict just to obtain a clean exact-type population.

The next question is therefore not current amplitude. It is:

> Which exact MaleCNS body/instance carries the `SNpp41|leg` annotation exception?

## Discovery-fail design

Stonkfly's pinned `annotations(ids)` function returns annotations indexed by `bodyId`. The audit preserves that index and records:

- `body_id`
- `instance`
- `type`
- `class`
- `subclass`
- `superclass`
- `soma_side`

The first prepared workflow deliberately has no frozen exception identity in source. If the structural evidence still matches 22 total SNpp41 rows, 21 chordotonal-organ rows, and exactly one `leg` row, it reports `DISCOVERY_REQUIRED` and exits non-zero **after publishing the discovered identity**.

This intentional red run prevents NeuroFly from silently accepting "whatever the one exception happens to be".

## Freeze stage

After observing the identity from the pinned prepared dataset, a follow-up commit must freeze that exact body/instance receipt. Only then may the audit return success, and the status must remain `REVIEW_REQUIRED`.

A frozen green receipt still requires:

- `promotion_ready=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`
- `current_calibration_authorized=false`

Changing the body ID, instance, class, subclass, superclass, or side must fail closed.

## Interpretation boundary

This audit can determine reproducible annotation identity. It cannot by itself determine whether the exception is:

- curator annotation drift;
- segmentation/reconstruction ambiguity;
- a legitimate mixed systematic type;
- a cross-dataset naming mismatch;
- or another biological/annotation issue.

That interpretation requires comparison with current MaleCNS type resources, VFB/MANC records, morphology/connectivity and, where possible, curator evidence.

No proprioceptive current should be enabled from this audit alone.
