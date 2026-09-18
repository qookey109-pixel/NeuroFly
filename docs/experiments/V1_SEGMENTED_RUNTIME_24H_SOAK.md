# V1 — Segmented Runtime 24-Hour Soak Evidence

## Purpose

NeuroFly's zero-cost long-running mode is intentionally segmented across
bounded GitHub-hosted runners.

It is not one operating-system process that remains alive for 24 hours.

The relevant v1 release question is whether the real MaleCNS production runtime
can remain continuously covered by successful checkpointed runner lifecycles
for at least 24 wall-clock hours.

## Frozen production evidence

The upgraded evidence snapshot covers:

- first run number: 159
- first run ID: 35067765930
- first created: 2026-09-16T07:17:21Z
- last run number: 461
- last run ID: 35319851297
- last updated: 2026-09-18T07:43:05Z

Observed:

- 303 consecutive NeuroFly Curriculum Training runs
- 303 / 303 completed successfully
- no missing run number
- wall-clock span: 174344 seconds
- wall-clock span: 48.428889 hours
- maximum positive handoff idle gap: 0 seconds
- maximum raw handoff gap: -2 seconds

A negative raw handoff gap means the next workflow was already dispatched and
started before the previous workflow finished its final cleanup. It is overlap,
not an error.

## Acceptance rule

For this frozen evidence, PASS requires:

- at least 24 wall-clock hours;
- exact consecutive run numbers;
- every recorded run completed with conclusion success;
- no positive gap between adjacent runner lifecycles;
- no requirement that a single Python or operating-system process survive for
  the whole interval.

The observed 48.43-hour window passes every rule.

## Why a successful curriculum run is meaningful

The production NeuroFly Curriculum Training workflow treats both real MaleCNS
training and checkpoint persistence as required operations.

A successful run requires the real MaleCNS training step to complete. The
training code rejects any decision that lacks verifiable neural activity.

After successful training, the coordinated brain and curriculum state is saved
with actions/cache/save. That state-cache step is not configured as
continue-on-error.

Therefore the frozen chain is not simply 303 green scheduler pings: it is a
sequence of successful real-MaleCNS training executions with persisted state
handoff.

Viewer-state publishing and continuation dispatch have separate resilience
behavior, so they do not change the authority of the safely persisted brain.

## Relationship to forced-crash evidence

The segmented soak and the forced-crash proof answer different questions.

The 48.43-hour soak demonstrates sustained bounded-run operation with
continuous runner-lifecycle coverage and repeated checkpoint handoff.

The separate forced-crash proof demonstrates that unsaved process failure does
not modify the last persisted checkpoint and that a distinct real MaleCNS
process can recover from it.

Together they support the v1 long-running platform requirement more strongly
than either result alone.

## Claim boundary

This evidence supports:

segmented_runtime_24h_soak_validated = true

and:

bounded_runner_checkpoint_chain_validated = true

It does not support:

- continuous_single_process_uptime_validated
- zero_data_loss_claimed
- storage_corruption_immunity_claimed
- every_unsaved_decision_preserved_claimed

The full per-run metadata is frozen in:

data/v1_segmented_runtime_soak_20260918.json

CI recomputes run-number continuity, success status, wall-clock span and
handoff-gap bounds from the individual records rather than trusting only the
stored summary.
