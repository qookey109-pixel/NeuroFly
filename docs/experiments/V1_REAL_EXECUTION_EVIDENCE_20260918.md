# NeuroFly V1 — Real Execution Evidence Freeze (2026-09-18)

## Purpose

This file freezes the first real-execution evidence set produced after the
NeuroFly v1 platform integration candidate entered main.

The original GitHub Actions artifacts have short retention. This evidence
snapshot preserves the run identifiers, artifact identifiers, receipt hashes,
source checkpoint hashes, descriptive metrics and claim boundaries needed to
reconstruct what was actually demonstrated.

It does not replace the original workflow logs or raw receipts. It provides a
stable repository-level evidence index anchored by their hashes.

## Shared execution basis

All three workflows executed on:

- GitHub branch: main
- workflow head SHA: 35341d96843d846388ace5520569187c0521ade3
- MaleCNS release: MaleCNS v1.0
- neurons: 166700
- directed edges: 25582938
- shared production brain SHA-256:
  afbe266465e0b14c4a353f2ee7123c4a2cc85835bf3db90b1b8cd9b60e366ddd

The production checkpoint was used only as a read-only source for these
isolated experiments.

## 1. Real MaleCNS in Light Chase

Workflow run:

35315244715

Receipt:

cbcb0543946ec8e18fb8a2574221c51df26335b3f3e5f1adf88fe59d024125ea

Result:

PASS

The real MaleCNS backend executed three verified decisions through the Light
Chase sensory-only environment adapter.

Observed actions:

- TURN_LEFT: 3

Observed task result:

- total reward: -0.03
- lights reached: 0

This proves execution compatibility with the second game. It does not prove
successful light seeking or learning.

## 2. Forced crash recovery

Workflow run:

35315253949

Receipt:

df516cc8802fbd1816ba7d49fcd163bd167c01edd7f3163d29ebd98ff6aa7aea

Result:

PASS

Three crash/recovery cycles completed.

Each crash worker:

- executed verified real MaleCNS neural activity;
- exited with the preregistered non-zero crash code;
- deliberately did not save the newer unsaved state.

For every cycle:

- the persisted brain + maze checkpoint pair was byte-for-byte unchanged by the
  unsaved crash;
- recovery occurred in a distinct process;
- the recovery process executed verified real MaleCNS;
- persisted counters resumed monotonically;
- a new coordinated checkpoint pair was produced.

The original production checkpoint hashes remained unchanged.

This supports recoverability from the latest persisted checkpoint. It does not
claim preservation of work performed after the last save, zero data loss or
24-hour soak stability.

## 3. Real MaleCNS learning control study

Workflow run:

35315263154

Receipt:

d14be40f2dc3f589548e9e36e453090a2db0605124b5b690d8779b1ff1d958bc

Execution status:

HUMAN_REVIEW_REQUIRED

Execution gate:

PASS

The study ran all four preregistered arms from the same initial brain
checkpoint:

- learning_true
- frozen_true
- learning_scrambled
- learning_sensory_off

Training used 60 decisions per arm.

Evaluation used three held-out seeds:

- 701
- 709
- 719

Each held-out evaluation used 20 decisions with:

- learning disabled;
- weights frozen;
- reinforcement suppressed;
- normal sensory input restored.

Aggregate held-out results:

| Arm | Mean reward | Mean food | Mean clears | Mean deaths | HOLD fraction |
| --- | ---: | ---: | ---: | ---: | ---: |
| learning_true | 2.8 | 3 | 0 | 0 | 0.50 |
| frozen_true | -0.2 | 0 | 0 | 0 | 0.75 |
| learning_scrambled | -0.2 | 0 | 0 | 0 | 0.80 |
| learning_sensory_off | 0.8 | 1 | 0 | 0 | 0.55 |

Descriptively, learning_true exceeded frozen_true and learning_scrambled by
+3.0 mean reward and +3.0 mean food, and exceeded learning_sensory_off by +2.0
mean reward and +2.0 mean food.

These are exploratory descriptive effects only. The study intentionally has no
automatic winner, confirmatory threshold, inferential test or promotion rule.

Therefore the following remain false:

- learning_validated
- generalization_validated
- causal_learning_claim_authorized
- behavioral_promotion_authorized

## What is now supported for NeuroFly v1

The evidence set supports three narrow statements:

1. a real MaleCNS backend can execute verified neural decisions in a second
   sensory-driven game through the shared environment adapter;
2. an isolated persisted NeuroFly checkpoint can survive repeated unsaved
   process crashes and be restored by a distinct real MaleCNS process;
3. a controlled real-MaleCNS four-arm learning comparison can be executed with
   isolated checkpoints and held-out frozen evaluation.

## Still open before final v1 release

The remaining major product-level evidence includes:

- confirmatory learning validation with preregistered replicate count and
  decision rule;
- longer soak evidence, including a 24-hour target if that remains the chosen
  v1 release criterion;
- final release/version/README consolidation.

The unresolved SNpp39/SNpp41 type-level polarity question remains a research
issue and is not a blocker for the product definition of NeuroFly v1.
