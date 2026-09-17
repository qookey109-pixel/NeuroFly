# V0.11 Proprioception — Curated Evidence Review Preparation

Status: REVIEW_REQUIRED  
Date: 2026-09-17

## Purpose

This stage sits directly above Draft PR #77 and prepares a fail-closed machine classification step for a future **already validated** NeuronBridge expert-curated identity receipt.

It does not acquire credentials, perform login, call the protected `/curated_matches` endpoint, resolve SNpp39/SNpp41 polarity, or authorize runtime use.

## Upstream authority

This stage is stacked on:

- PR #77 — `V0.11 proprioception — offline curated identity receipt intake`
- exact upstream head: `e65738731c44f831eb50a8e8ee102b0da8014a2a`
- expected validation schema: `neurofly-proprioception-curated-identity-receipt-validation-v0.1`

Only the two structurally valid upstream states are accepted:

- `VALID_RECEIPT_REVIEW_REQUIRED`
- `VALID_RECEIPT_CONFLICT_REVIEW_REQUIRED`

## Why this stage exists

A receipt passing a structural validator is not yet a biological conclusion.

This layer therefore separates:

1. **receipt structure/provenance validation** — PR #77;
2. **machine classification for science review** — this PR;
3. **human science review and any future polarity promotion** — a later, separate stage.

No stage is allowed to collapse these boundaries.

## Exact validation-report firewall

The review classifier accepts only the exact top-level output contract produced by PR #77. Extra fields fail closed. In particular, raw API responses, credentials, authorization headers, tokens, or other unreviewed payloads are not part of the review-stage input contract.

The classifier also re-checks:

- exact validation schema;
- allowed validation state;
- `receipt_valid=true`;
- both direction classes represented by a pure `SNpp39`/`SNpp41` bijection;
- every upstream validation gate is true;
- every upstream per-record result is passed and all of its gates are true;
- validation state is consistent with the reported hypothesis-agreement boolean;
- all science/runtime locks remain closed.

## Classification states

If a validated receipt agrees with the current working inference:

- `hook_extension -> SNpp39`
- `hook_flexion -> SNpp41`

then this stage emits:

`EVIDENCE_SUPPORTS_CURRENT_HYPOTHESIS_REVIEW_REQUIRED`

If an otherwise valid receipt supports the opposite pure bijection, this stage emits:

`EVIDENCE_CONFLICTS_CURRENT_HYPOTHESIS_REVIEW_REQUIRED`

The conflicting result is preserved for biological review. It is not discarded merely because it disagrees with the current inference.

If the validation report is malformed, tampered, incomplete, inconsistent, or contains an opened science/runtime lock, this stage emits:

`INVALID_VALIDATION_REPORT`

## Synthetic tests are not evidence

Unit tests construct synthetic receipts only to prove the control logic can distinguish agreement, conflict, tampering, and malformed reports.

Synthetic records:

- are not biological observations;
- do not count toward polarity resolution;
- cannot become direct crosswalk evidence;
- cannot authorize calibration, stimulation, runtime mapping, or promotion.

## Current scientific boundary

Unchanged:

- `SNpp39 ≈ extension-sensitive hook` — `PHYSIOLOGY_SUPPORTED_INFERENCE`
- `SNpp41 ≈ flexion-sensitive hook` — `PHYSIOLOGY_SUPPORTED_INFERENCE`
- `direct_crosswalk_found=false`
- `polarity_resolved=false`

A future authentic receipt can be classified here, but even a structurally valid and hypothesis-supporting receipt still requires a later explicit science-review stage before any promotion is considered.

## Hard locks

This stage always emits:

- `human_science_review_required=true`
- `science_review_completed=false`
- `direct_crosswalk_found=false`
- `polarity_resolved=false`
- `current_calibration_authorized=false`
- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`
- `runtime_gating_authorized=false`
- `neural_payload_eligible=false`
- `promotion_ready=false`

No receptor encoding, runtime wiring, public-state publication, neural current, stimulation, systematic-type routing, reward, decoder, training behavior, or merge policy is changed.
