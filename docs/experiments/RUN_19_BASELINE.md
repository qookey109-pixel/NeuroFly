# NeuroFly Curriculum Run 19 — Behavior Baseline

Status: **historical evidence receipt — completed run**  
Run ID: `34679327709`  
Job ID: `103514869530`  
Training decisions: `1200`  
Receipt schema: `neurofly-self-training-v3`  
Receipt SHA-256: `2cae2f881937666565275c524767f49d3874da45a23df44e474797efccfb9112`  
Published authority commit: `fe60ab8fdc69ce8f4fa0c5801993473ca2717199`  

> This document freezes descriptive evidence from Run 19 before the short-retention GitHub artifact expires. It does **not** assert learned navigation. Run 19 executed the `main` runtime that existed before Behavior Evidence v1 and Anti-stall v2 were integrated; the metrics below were reconstructed from its signed training receipt.

## Verified run outcome

- backend: `malecns`
- passed: `true`
- curriculum: `neurofly-curriculum-v2`
- curriculum stage at finish: `1 — full-maze-food-only`
- clears before / after: `0 / 0`
- batch clears: `0`
- deaths: `0`
- episode remained `1`
- stale/discarded neural decisions: `0`
- world states seen: `9253`
- live states published: `3600`
- wall time: `4576.41953 s`
- total active time at final state: `12908.540772 s`
- global decisions/ticks at final state: `3600`
- total world ticks at final state: `10853`

## Food outcome

- food at batch start: `144`
- food remaining at finish: `79`
- food acquired: **65**
- food per 100 neural decisions: **5.416667**
- positive food events: `65`
  - ordinary food: `64`
  - energy food: `1`
- total reward across observations: `54.0`

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
  - `anti_stall_hold_forward`: `111`
  - `anti_stall_followup_forward`: `111`
  - `anti_stall_blocked_forward_turn`: `41`

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

- first observed memory SHA-256: `213a882b60ffb66007efbc54759665ab00081cb4b9885ed5aeb7af7a2ad6dcbb`
- last observed memory SHA-256: `94359ccb76c6e8b90efdeb20d75c6a7b5ad95e643dcce19ee454442dea51b268`
- unique observed memory SHA values: `1063`

The simulated memory/plasticity state changed during the run. State change alone is **not** evidence that useful navigation learning occurred.

## Interpretation boundary

Run 19 establishes that verified MaleCNS neural activity produced raw decoded actions, the environment applied those actions plus transparent anti-stall interventions, food was acquired, and persistent memory state changed. It does **not** establish learned navigation, general intelligence, biological intent, or subjective experience.

The controlled-learning protocol `neurofly-learning-evaluation-v1` remains **not yet executed**. Claims of learning require the candidate, frozen-plasticity, randomized/sham-reward, odor-off, and held-out validation comparisons defined there.
