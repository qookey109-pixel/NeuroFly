# V1 DAN Trace-State Recentering Intervention

## Purpose

KC-DAN Eligibility Diagnostic Run 35413358900 established a concrete state
mismatch candidate:

- the restored source checkpoint carried an aversive `rate_dan` trace of
  about 165.718 Hz;
- the calibrated baseline was about 126.722 Hz;
- applying that baseline without transforming the persisted trace left an
  immediate +38.996 Hz centered-state offset;
- the calibrated arm showed a large positive early aversive plastic drive.

The same diagnostic also showed that positive aversive drive persisted late in
the run, so this mismatch cannot be assumed to explain the entire effect.

This intervention isolates only the checkpoint trace-state contribution.

## Exact state transform

The pinned Stonkfly centered rule evolves `rate_dan` as the exponential trace
of the DAN signal passed into the rule.

If a constant baseline `b` is subtracted from the input signal, the
mathematically corresponding trace state is shifted by the same constant:

`rate_dan_centered = rate_dan_raw - b`

This is an exact coordinate transform for the same first-order trace dynamics.
It is not a new biological parameter.

## Arms

Four fresh matched replicates compare:

- `learning_none_calibrated_unrecentered`
- `learning_none_calibrated_recentered`
- `learning_none_zero_baseline`
- `frozen_none_calibrated_recentered`

All arms use normal sensory input and no external reinforcement.

The calibrated arms reuse the frozen 17-cell baseline from DAN Baseline
Intervention Run 35348834258. No baseline is re-estimated.

## Primary descriptive endpoints

- memory-changed training decisions;
- final mean-efficacy delta;
- first-five-step mean-efficacy delta;
- frozen held-out mean reward.

## Interpretation

If recentering sharply reduces the early and final drift relative to the
unrecentered calibrated arm, the checkpoint trace mismatch becomes a stronger
causal candidate.

If early drift is reduced but substantial later drift persists, the result
supports separating two mechanisms:

1. an initialization / checkpoint-coordinate mismatch; and
2. continuing KC-DAN temporal covariance under the centered rule.

This exploratory run does not automatically validate either causal claim.

## Governance

No production checkpoint mutation.
No eta tuning.
No decoder-threshold tuning.
No reward-strength tuning.
No baseline retuning.

The following remain false:

- `learning_validated`
- `dan_trace_state_mismatch_causal`
- `trace_recentering_remediation_validated`
- `kc_dan_temporal_drive_causal`
- `causal_learning_claim_authorized`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
