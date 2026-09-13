# NeuroFly Curriculum Run 19 — Behavior Baseline

Status: **historical evidence receipt — completed run**  
Run ID: `34679327709`  
Job ID: `103514869530`  
Training decisions: `1200`  
Receipt schema: `neurofly-self-training-v3`  
Final artifact ID: `10294716209`  
Artifact name: `neurofly-v06-curriculum-34679327709-1`  
Artifact digest: `sha256:a239a0d02730035b7d847234605a2ca784ceb3140ca6042503afd6422777a872`  
Receipt SHA-256: `44996546185b2d4667fc86578264240960c4cfd6aecaea9f90ec5089f9a6cf07`  
Run head SHA: `5f3a998cb403a6fa7ac69178e00486481a38622d`  
Published authority commit: `fe60ab8fdc69ce8f4fa0c5801993473ca2717199`  

> This document freezes descriptive evidence from the **final Run 19 GitHub Actions artifact** before its short retention expires. It does **not** assert learned navigation. Run 19 executed the `main` runtime that existed before Behavior Evidence v1 and Anti-stall v2 were integrated; the metrics below were reconstructed from its final signed training receipt.

## Provenance correction

An earlier draft of this baseline was reconstructed from a non-final snapshot and did not match the final Run 19 artifact. This version replaces those values with the final artifact listed above. The receipt digest was independently recomputed with the same canonical JSON procedure used by NeuroFly and matches `receipt_sha256` exactly.

## Verified run outcome

- backend: `malecns`
- passed: `true`
- curriculum: `neurofly-curriculum-v2`
- curriculum stage for all 1200 observations: `1 — full-maze-food-only`
- clears before / after: `0 / 0`
- batch clears: `0`
- total deaths at finish: `0`
- episode remained `1`
- all 1200 observations are `neural_decision` states with `decision_applied=true`
- world states seen: `3616`
- live states published: `4567`
- wall time: `4576.405483 s`
- total active time at final state: `12908.5 s`
- global decisions/ticks at final state: `3600`
- total world ticks at final state: `10853`
- final fly position: `(1, 5)`, facing `LEFT`

## Food outcome

- food at batch start: `144`
- food remaining at finish: `79`
- food acquired: **65**
- food per 100 neural decisions: **5.416667**
- positive food events: `65`
  - ordinary food: `64`
  - energy food: `1`
- total reward across the 1200 observations: `54.0`

Run 19 acquired food, but it did **not** clear the maze. Zero clears must remain reported as zero.

## Raw MaleCNS actions

| Raw action | Count | Share |
| --- | ---: | ---: |
| TURN_RIGHT | 575 | 47.92% |
| HOLD | 507 | 42.25% |
| TURN_LEFT | 64 | 5.33% |
| FORWARD | 54 | 4.50% |

These are decoded MaleCNS actions before the engineered anti-stall floor.

## Applied environment actions

| Applied action | Count | Share |
| --- | ---: | ---: |
| TURN_RIGHT | 531 | 44.25% |
| HOLD | 338 | 28.17% |
| TURN_LEFT | 55 | 4.58% |
| FORWARD | 276 | 23.00% |

The difference between raw and applied distributions is material and must not be hidden in later comparisons.

## Anti-stall contribution

- anti-stall policy: `neurofly-anti-stall-v1`
- overridden decisions: **263 / 1200 = 21.9167%**
- reasons:
  - `anti_stall_hold_forward`: `87`
  - `anti_stall_followup_forward`: `143`
  - `anti_stall_blocked_forward_turn`: `33`

Raw `FORWARD` was only `4.50%`, while applied `FORWARD` was `23.00%`. Therefore Run 19's locomotion and food outcome cannot be interpreted as pure MaleCNS navigation behavior without controlling for engineered overrides.

## Bilateral food-cue / raw action association

Food-cue side counts across the 1200 neural decisions:

- LEFT stronger: `568`
- RIGHT stronger: `600`
- BALANCED: `32`

Among the `617` raw directional turns (`TURN_LEFT` / `TURN_RIGHT`) that occurred under a non-balanced food cue:

- turn aligned with the stronger food cue: `307`
- alignment rate: **49.7569%**

This is descriptive association only. A rate near 50% in this single run does not show an obvious raw directional-turn bias toward the stronger food cue. It is not a statistical significance test and does not prove absence of sensory influence.

## Persistent memory / plasticity evidence

- first observed memory SHA-256: `967ac9d97f2f42a882079a3d5d970770964ddd0d70554590566ad23165fba655`
- last observed memory SHA-256: `77a18417052136e312a6aed9659b0bb8df42b506a03a8ef74fa03cd1c1de88e5`
- unique observed memory SHA values: `1200 / 1200`

The simulated memory/plasticity state changed throughout the run. State change alone is **not** evidence that useful navigation learning occurred.

## Interpretation boundary

Run 19 establishes that verified MaleCNS neural activity produced raw decoded actions, the environment applied those actions plus transparent anti-stall interventions, food was acquired, and persistent memory state changed. It does **not** establish learned navigation, general intelligence, biological intent, or subjective experience.

The controlled-learning protocol `neurofly-learning-evaluation-v1` remains **not yet executed**. Claims of learning require the candidate, frozen-plasticity, randomized/sham-reward, odor-off, and held-out validation comparisons defined there.
