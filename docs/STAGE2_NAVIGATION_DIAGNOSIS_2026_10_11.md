# NeuroFly Stage 2 — Live Predator-Odor / Action Audit

Source frozen at **2026-10-11 01:37:32 UTC** (verified publication Git blob
`063b401dcf21f78be0adbf3561f31759ca88e954`, commit
`782835816a76069dc9f4d89f0c7141ceec73bf4a`).

## Observed behavior in the latest 240-decision playback

The source is **one Stage 2 episode**, not 240 independent trials.

| Odor contrast grouping | Decisions | Away-side decoded turns | Toward-side decoded turns | Forward |
| --- | ---: | ---: | ---: | ---: |
| All playback | 240 | 32 | 45 | 163 |
| Strong lateral predator odor (`abs(left-right) >= 0.10`) | 162 | 19 | 32 | 111 |
| Weak lateral predator odor | 78 | 13 | 13 | 52 |

The "away" label follows the operational proxy already introduced in PR #218:
under higher left danger-ORN drive, `TURN_RIGHT` is coded as away; under higher
right drive, `TURN_LEFT` is coded as away. **This is not evidence of a
validated escape direction** or of biological turning polarity.

State counters at that checkpoint: `curriculum_stage=2`,
`curriculum_stage_clears=0`, `total_clears=2` (both Stage 1),
`total_deaths=21934`, `total_ticks=4842498`.

## Interpretation / next gates

- Signed predator smell is reaching telemetry, but a reliable autonomous
  away-turn advantage is not apparent in this observational sample.
- The 240 decisions share the same episode and autocorrelated spatial context.
  Do not apply independent-trial binomial significance tests to these counts.
- No intervention efficacy, safety, or Stage 2 clear is established.
- Review the existing #219 same-checkpoint, multi-gain Stage 2 maze report.
  Its wall-clock enemy cadence and single trial per gain are confounds; do not
  interpret positive deltas as causal until repeated matched-clock studies.
- Next experiment should distinguish neural steering under predator odor from
  wall-related stimuli and food-conflict cases, with no privileged direction
  supplied to the brain.
- Preserve the action-autonomy boundary: change only reviewed sensory input,
  never force turns, pathfind, or overwrite the motor decoder.

The read-only audit code under `src/neurofly/odor_behavior_audit.py` makes these
definitions reproducible for future verified snapshots. It cannot approve any
production parameter change.
