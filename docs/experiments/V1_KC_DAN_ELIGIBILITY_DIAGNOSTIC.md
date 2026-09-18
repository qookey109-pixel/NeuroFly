# V1 KC–DAN Covariance / Eligibility Diagnostic

## Purpose

The DAN Baseline Intervention did not eliminate unreinforced plastic drift.

Instead:

- zero-baseline learning drifted slightly negative;
- calibrated-baseline learning drifted strongly positive;
- both learning arms changed memory on every decision;
- frozen memory stayed unchanged.

This diagnostic traces the exact centered-rule terms that feed the pinned Stonkfly
plasticity update.

It does not tune learning and does not change production runtime behavior.

## Pinned equation

At each 10 ms rate bin, the pinned rule computes midpoint KC and DAN traces and
then applies:

`eta * (KC_now * DAN_trace - DAN_now * KC_trace)`

to each plastic edge, followed by the two-state `u/w` memory filter.

The first term is recorded as:

`kc_x_dan_trace_term`

The second term is recorded as:

`dan_x_kc_trace_term`

Their signed difference is recorded as:

`net_antihebbian_term`

The tracer then calls the original pinned `advance()` implementation and
records the actual `delta_u` and `delta_w`.

## Why this matters

A zero long-run mean DAN residual does not imply zero plastic drive.

Temporal structure can remain because current KC rates are multiplied by DAN
history while current DAN rates are multiplied by KC history.

This diagnostic tests whether those cross-time terms explain the persistent
memory movement seen when external reinforcement is absent.

## Arms

Three fresh matched replicates run:

- `learning_none_zero_baseline`
- `learning_none_calibrated_baseline`
- `frozen_none_zero_baseline`

Every arm receives normal NeuroFly sensory input and no external reinforcement.

The calibrated arm reuses the exact 17-cell task-conditioned baseline vector
frozen from DAN Baseline Intervention Run 35348834258.

## Observations

Every 10 ms bin records:

- KC instantaneous rate;
- DAN residual rate after baseline subtraction;
- KC pre/midpoint trace;
- DAN pre/midpoint trace;
- `KC_now × DAN_trace`;
- `DAN_now × KC_trace`;
- signed net drive;
- actual `delta_u`;
- actual `delta_w`.

The report separates reward-compartment and aversive-compartment plastic edges.

It also freezes the initial checkpointed `rate_dan` state before the first
decision. This is important because changing the DAN baseline after restoring a
checkpoint does not automatically recenter the already persisted DAN trace.

## Interpretation boundary

This run may identify a mathematical driver or a state mismatch candidate, but
it does not make either causal claim automatically.

All remain false:

- `learning_validated`
- `kc_dan_temporal_drive_causal`
- `dan_trace_state_mismatch_causal`
- `causal_learning_claim_authorized`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`

A later intervention would be required before changing production learning.
