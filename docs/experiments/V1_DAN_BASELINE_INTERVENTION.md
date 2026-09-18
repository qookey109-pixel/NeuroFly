# V1 Task-Conditioned DAN Baseline Intervention

## Purpose

The completed learning-mechanism diagnostic showed that the current
learning-enabled MaleCNS memory changes on every decision even when NeuroFly
delivers no external reward or aversive pulse.

This stage tests one narrow mechanism:

> Does subtracting the endogenous task-conditioned DAN firing rate reduce the
> unreinforced plastic drift seen with the current zero DAN baseline?

This is an exploratory intervention. It does not establish a biological
resting firing rate and it does not validate learning.

## Frozen origin evidence

Diagnostic Run 35343487907 remains immutable historical evidence.

Its compact freeze is stored at:

`data/learning_mechanism_diagnostic_run1_freeze_v01.json`

The observed facts motivating this intervention are:

- `learning_none` changed memory on 60/60 decisions in every diagnostic
  replicate;
- all those decisions had no external reinforcement;
- endogenous DAN activity remained present;
- mean efficacy moved downward;
- frozen memory stayed unchanged;
- save -> fresh restore preserved memory exactly.

## Calibration meaning

The intervention first estimates a **task-conditioned endogenous DAN
baseline**.

It is deliberately not called a physiological resting baseline.

The estimator uses three fresh calibration seeds. For each seed:

- the production checkpoint is opened read-only;
- learning is disabled;
- external reinforcement is disabled;
- normal NeuroFly sensory input remains enabled;
- the world advances decision-synchronously;
- each PAM11/PPL101 cell's spike count is converted to Hz over each 50 ms
  decision;
- the per-cell mean across all calibration decisions becomes the intervention
  baseline vector.

This vector is an engineered model calibration for this task/runtime only.

## Three paired arms

Four fresh matched replicates run three arms from the same source checkpoint:

### learning_none_zero_baseline

Current behavior:

- learning enabled;
- external reinforcement suppressed;
- DAN baseline = zero.

### learning_none_calibrated_baseline

Intervention behavior:

- learning enabled;
- external reinforcement suppressed;
- task-conditioned DAN baseline subtraction enabled.

### frozen_none_zero_baseline

Reference behavior:

- learning disabled;
- external reinforcement suppressed;
- DAN baseline = zero.

All arms use 60 training decisions and two fresh held-out seeds with 20 frozen
evaluation decisions per seed.

## Primary descriptive endpoints

The intervention reports, without an automatic scientific verdict:

1. memory-changed decisions;
2. final mean-efficacy change from the identical starting checkpoint;
3. frozen held-out mean total reward.

Supportive telemetry includes HOLD fraction and DNpe017 gate-zero fraction.

## Checkpoint provenance

For the corrected arm, the source checkpoint is first restored under its
original zero-baseline configuration. The task-conditioned baseline is applied
only after that restore.

When the corrected checkpoint is later evaluated, a fresh brain receives the
same baseline vector before restoring the corrected checkpoint. This preserves
Stonkfly's configuration-signature provenance check rather than bypassing it.

## Claim boundary

Regardless of the exploratory result:

- `learning_validated = false`
- `task_conditioned_dan_baseline_causal = false`
- `biological_dan_resting_rate_established = false`
- `causal_learning_claim_authorized = false`
- `replacement_confirmatory_authorized = false`
- `behavioral_promotion_authorized = false`

If the corrected arm reduces drift, that is evidence supporting a later,
separately preregistered causal replication. It is not itself permission to
change production learning or open a confirmatory study.
