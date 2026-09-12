# NeuroFly Run #19 — Retrospective Behavior Evidence

Status: observational retrospective only; **not** a learning claim.

Source authority:
- GitHub Actions run: `NeuroFly Curriculum Training #19`
- run id: `34679327709`
- artifact: `neurofly-v06-curriculum-34679327709-1`
- verified receipt schema: `neurofly-self-training-v3`
- receipt SHA-256: `44996546185b2d4667fc86578264240960c4cfd6aecaea9f90ec5089f9a6cf07`
- Stonkfly pin and receipt verification remained governed by the existing V0.6 workflow.

## Batch outcome

- neural decisions: **1200**
- world states observed: **3616**
- curriculum stage: **1 — full-maze-food-only**
- episode remained: **1**
- food remaining: **144 -> 79**
- food acquired: **65**
  - ordinary food events: **64**
  - energy-food events: **1**
- food / 100 decisions: **5.416667**
- clears: **0**
- deaths: **0**
- final cumulative reward: **44.0**
- final total active seconds: **12908.5**
- workflow training wall seconds: **4576.405483**

Zero clears are reported as zero; no success is inferred from food acquisition alone.

## Raw MaleCNS action distribution

| Raw action | Count |
| --- | ---: |
| TURN_RIGHT | 575 |
| HOLD | 507 |
| TURN_LEFT | 64 |
| FORWARD | 54 |

## Applied action distribution

| Applied action | Count |
| --- | ---: |
| TURN_RIGHT | 531 |
| HOLD | 338 |
| FORWARD | 276 |
| TURN_LEFT | 55 |

The difference between raw and applied actions is engineered anti-stall intervention, not a change in the MaleCNS decoder.

## Anti-stall intervention

- overridden decisions: **263 / 1200**
- override rate: **21.916667%**

Reasons:

| Override reason | Count |
| --- | ---: |
| `anti_stall_followup_forward` | 143 |
| `anti_stall_hold_forward` | 87 |
| `anti_stall_blocked_forward_turn` | 33 |

This comparatively high intervention rate is a locomotion-quality signal. It must not be presented as learned behavior.

## Food-cue / raw-action association

Food bilateral cue side across the 1200 neural decisions:

| Stronger food cue | Decisions |
| --- | ---: |
| RIGHT | 600 |
| LEFT | 568 |
| BALANCED | 32 |

Raw MaleCNS action conditioned on food cue:

| Cue | TURN_LEFT | TURN_RIGHT | FORWARD | HOLD |
| --- | ---: | ---: | ---: | ---: |
| LEFT | 32 | 279 | 21 | 236 |
| RIGHT | 31 | 275 | 32 | 262 |
| BALANCED | 1 | 21 | 1 | 9 |

Among non-balanced cue states where the raw MaleCNS action was specifically `TURN_LEFT` or `TURN_RIGHT`, the turn aligned with the stronger food cue **307 / 617 = 49.7569%** of the time.

### Interpretation boundary

This batch does **not** show a directional food-odor turning advantage. A ~49.8% alignment rate is approximately chance-like for this binary directional comparison and must not be described as learned odor-guided navigation.

The batch does show that the persistent agent can acquire food while remaining alive in the fixed Stage-1 world, but that observation is confounded by environment geometry, persistent starting state, prior plasticity, and engineered anti-stall actions.

## What would count as stronger learning evidence

Use the versioned learning-evaluation protocol in this branch rather than this single batch alone. At minimum compare:

- plasticity enabled vs frozen
- real reward vs randomized reward
- odor-on vs odor-off
- repeated fixed-maze batches
- unseen validation maze
- food / 100 decisions
- raw action distribution
- odor-turn association
- clear/death outcomes
- anti-stall rate
- checkpoint identity and persistence

Do not claim learning unless improvement survives those controls and is not explained by engineered applied-action overrides.
