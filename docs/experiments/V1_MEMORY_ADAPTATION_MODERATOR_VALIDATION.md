# V1 Adaptation Moderator Validation

Status: **PREREGISTERED EXPLORATORY VALIDATION**

## Background

The previous outcome-blind moderator audit found a large discovery gap in
boundary adaptation engagement:

- suppression histories: `adaptation.paired_mean.std ≈ 1.09–1.13`
- non-suppression histories: `≈ 0.052–0.055`

That result was exploratory and cannot confirm a moderator.

This study uses a **new seed pool** and freezes a discovery-derived
classification before any new terminal intervention outcome is evaluated.

## Moderator bands

Measured after the exact prefix ending at lag -21 and before the intervention:

- **quiescent:** `adaptation.paired_mean.std <= 0.10`
- **engaged:** `adaptation.paired_mean.std >= 0.50`
- **intermediate:** recorded but not assigned to either target stratum

These thresholds are frozen before this cohort's effect labels exist.

## Outcome-blind stratified selection

Candidates are scanned in frozen order.

A candidate must have unique:

- pre-event checkpoint SHA-256
- stable sensory-sequence SHA-256

The study stops only after collecting:

- 4 adaptation-engaged histories
- 4 adaptation-quiescent histories

The adaptation feature is allowed to determine stratum membership because it is
the preregistered predictor. Terminal `intact` versus `clear_vg_delay`
effect endpoints are prohibited until the 8-history stratified manifest is
frozen.

## Shared intervention assay

Every selected history uses the same protocol:

- paired reward/no-pulse synaptic memory
- five reinforcement-free delay decisions
- exact prefix `-60...-21`
- boundary intervention
- exact terminal `-20...0`
- frozen learning
- zero recall reinforcement

Conditions:

1. `intact`
2. `clear_vg_delay`

## Effect labels

- **suppression:** candidate lower than intact on all three primary neural endpoints
- **reversal:** candidate higher than intact on all three
- **mixed:** otherwise

## Validation targets

Primary directional target:

**engaged suppression count > quiescent suppression count**

Secondary directional target:

**engaged mean candidate-minus-intact delta is more negative than quiescent
mean delta on all three primary endpoints**

No p-value or significance threshold is used.

If both targets pass, the correct conclusion is:

**adaptation moderator replication supported**

—not moderator confirmed, not causal, and not a carrier claim.

## Correlated prefix crosscheck

The discovery cohort also showed that non-suppression histories had zero
changed-KC and changed-edge expression at lag -21.

This validation therefore records whether those two lag -21 measures are
jointly nonzero in each adaptation stratum. This is a crosscheck only; it does
not resolve causal independence.

## Governance

All learning, carrier, causality, moderator-confirmation and behavioral
promotion locks remain false.
