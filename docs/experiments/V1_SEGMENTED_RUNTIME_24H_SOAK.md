# V1 — Segmented Runtime 24-Hour Soak Evidence

## Purpose

NeuroFly's zero-cost long-running mode is intentionally segmented across
bounded GitHub-hosted runners.

It is not a single operating-system process that remains alive for 24 hours.

The release question for this mode is therefore:

Can the real MaleCNS runtime continue through a checkpointed bounded-run chain
for at least 24 wall-clock hours without a failed curriculum run or a broken
run-number sequence?

## Frozen evidence window

This evidence snapshot covers:

- first run number: 225
- first run ID: 35131079927
- first created: 2026-09-16T17:54:34Z
- last run number: 458
- last run ID: 35317484236
- last updated: 2026-09-18T07:11:19Z

Observed:

- 234 consecutive NeuroFly Curriculum Training runs
- all 234 completed successfully
- no missing run number
- wall-clock span: 134205 seconds
- wall-clock span: 37.28 hours
- maximum positive handoff idle gap from GitHub run metadata: 0 seconds

The raw handoff gap can be negative because the next workflow is dispatched and
queued before the previous workflow finishes its final cleanup. Negative values
therefore represent overlap in GitHub run lifecycle metadata, not time travel
or a continuity defect.

## Acceptance rule

The frozen release rule is:

- at least 24 wall-clock hours;
- consecutive run numbers;
- every completed run successful;
- no positive handoff idle gap above 1200 seconds;
- a single uninterrupted operating-system process is not required.

The observed window passes every rule.

## Why workflow success matters

The NeuroFly Curriculum Training workflow does not treat training or checkpoint
persistence as optional.

A successful workflow requires:

1. real MaleCNS curriculum training to complete;
2. the isolated brain and curriculum state to be saved through
   actions/cache/save.

Publishing the viewer state and continuation dispatch have separate resilience
behavior, but failure to train or persist the state is not silently converted
into a successful run.

The workflow also uses one concurrency group so curriculum runners do not race
each other as independent training authorities.

## Relationship to forced-crash evidence

The segmented soak and the forced-crash proof answer different questions.

The 37.28-hour soak demonstrates sustained bounded-run operation and repeated
handoff.

The separate forced-crash evidence demonstrates that an unsaved crashing
process does not modify the last coordinated checkpoint and that a distinct
real MaleCNS process can recover from it.

Together they provide stronger long-running evidence than either result alone.

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

Those stronger statements remain false.

## Source of truth

The full run metadata used for this evidence is frozen in:

data/v1_segmented_runtime_soak_20260918.json

CI recomputes continuity, success status, wall-clock span and handoff-gap bounds
from the individual run records rather than trusting only the stored summary.
