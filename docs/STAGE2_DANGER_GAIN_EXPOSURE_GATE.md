# Stage 2 Danger ORN A/B — exposure equivalence gate

Date: 2026-10-11

## Why this gate was required

PR #219 introduced a same-checkpoint 600-decision maze evaluation of predator
olfactory-current gains `1.6` (production baseline), `2.4`, `3.2`.
All arms clone the same neural + world checkpoint, but the existing
`GoalMazeSession` runs the predator on wall-clock time (Stage 2: one
world tick every 2.0 s) rather than exactly once per neural decision.
A fixed 600-decision sample **does not guarantee the same enemy exposure**.

## Added read-only evidence

Every experiment arm now records, without changing any decoder/action:

- `world_tick_delta`: increase of the persisted `total_world_ticks` counter.
- `applied_decision_count`: decisions the environment really applied.
- `discarded_decision_count`: neural decisions discarded because the
  environment reset/advanced before they could be applied.

The source is verified byte-for-byte unchanged before and after each arm.

## Fail-closed exploratory signal policy

The exploratory gain screen may be favorable **only if**:

- Both arms started from exactly the same Stage 2 source checkpoint.
- Equal neural decision counts and complete behavior metric data.
- Both arms experienced >0 world ticks.
- Absolute world tick difference <= max(1, floor(5% of baseline ticks)).
- Discarded decisions <=10% of all decisions in each arm.
- Difference in discarded decision counts <= max(1, floor(1% of decisions)).
- All existing non-regression gates on blocked FORWARD, near-wall behavior,
  revisit rate, deaths, food and Stage 2 clears still pass.

Even when all these conditions hold, `exploratory_signal_only=true`
**does not authorize** a runtime gain change or prove causal benefit.
The candidate needs repeated, independent runs with matched world pacing
and a separate verified production promotion review.

## Interpretation

This patch improves *experiment validity*, **not** the fly's present
navigation policy. It does not raise stimulus current on the production
agent and cannot by itself produce a Stage 2 clear. Its goal is to
avoid selecting a stimulus gain based on mismatched predator pressure.
