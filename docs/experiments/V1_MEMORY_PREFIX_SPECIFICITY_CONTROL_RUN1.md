# V1 Reward Memory Prefix Specificity Control — Run 1

## Status

**EXPLORATORY MEMORY PREFIX SPECIFICITY CONTROL COMPLETE**

Successful GitHub Actions run: `36105949179`

- scientific head: `d4dfb515803fa156d57b06236aab2373b6263c4a`
- artifact id: `10851751103`
- artifact digest: `sha256:76a0174c2fa0324bb2cf84a26919da9f406eef043b0f4a4c91c0766d06f0bda1`
- receipt digest: `d0f0089aa19749be6bebb8c64de50576fc0d0452527bd3b1110dd97da37c2cfd`
- source checkpoint: `d2dd1cf9bd19c02f7d6cd8de5ab4d44ff3891c59744609e62ef7f79bd60e42e2`

The production checkpoint was unchanged. All preregistration and evidence gates
passed.

## Control integrity

The exact and control conditions both replayed 60 prereward decisions plus the
reward-event cue.

The rotated control preserved:

- the same 40 early frame/context pairs;
- the same number of early updates;
- the exact same `-20 ... 0` terminal sequence;
- the same paired reward/no-pulse memory state;
- frozen plasticity and zero recall reinforcement.

Only the temporal placement/order of the early `-60 ... -21` prefix changed.

## Primary result

Presence-level terminal endpoints did **not** distinguish exact from rotated
history:

| Common terminal window | Exact prefix | Rotated prefix |
| --- | ---: | ---: |
| any changed-KC activity | 4 / 4 | 4 / 4 |
| any MBON07 state difference | 4 / 4 | 4 / 4 |
| any MBON07 spike difference | 4 / 4 | 4 / 4 |
| any action divergence | 4 / 4 | 4 / 4 |
| reward-cue action divergence | 0 / 4 | 1 / 4 |

Therefore the exact early temporal ordering is **not required** to preserve the
presence of downstream memory expression in this control.

## Common-window averages

Across the preregistered `-20 ... 0` per-lag endpoints:

| Descriptive measure | Exact | Rotated |
| --- | ---: | ---: |
| mean changed-KC active fraction | 0.340829706889 | 0.318178082032 |
| mean changed-edge L1 engaged fraction | 0.505810082096 | 0.474958955507 |
| MBON07 state-difference fraction | 1.000000000000 | 0.964285714286 |
| MBON07 spike-difference fraction | 0.202380952381 | 0.238095238095 |
| action-divergence fraction | 0.166666666667 | 0.083333333333 |

The exact history has a modest average advantage in changed-KC engagement,
changed-edge L1 engagement, MBON07-state continuity, and action-divergent lag
density.

However, that advantage is not uniform:

- rotated history has slightly higher MBON07 spike-difference density;
- all four rotated replicates still show action divergence somewhere in the
  common terminal window;
- PS4 produces reward-cue action divergence under rotated history while exact
  history does not.

## Replicate-level action expression

- **PS1 / 3203**
  - exact: `-20,-19,-15,-13,-12,-2`
  - rotated: `-13,-10,-3`
- **PS2 / 3209**
  - exact: `-20,-19,-15,-11,-2`
  - rotated: `-1`
- **PS3 / 3217**
  - exact: `-11`
  - rotated: `-15,-7`
- **PS4 / 3221**
  - exact: `-3,-1`
  - rotated: `0`

This is heterogeneous rather than a clean exact-history dominance pattern.

## Interpretation

The preceding 1 tau versus 3 tau study established that additional early
history makes the terminal memory-expression state more continuous.

This matched control now narrows that result:

`more early runtime/context`
appears important,

but the **precise original ordering** of the early 40-step prefix is not yet
shown to be necessary.

The exact prefix does retain a modest average expression advantage, so a
sequence-specific contribution is not excluded. It is simply **not confirmed**
by this run.

A plausible remaining mechanism is that the extra 40 decisions allow one or
more transient internal state variables to accumulate before the identical
terminal sequence begins.

## Next mechanism test

The next clean study should localize that carried state instead of trying a new
decoder or learning rule.

Use fresh preregistered trajectories and keep exact 3 tau history in all
conditions. At the `-20` boundary, selectively clear candidate transient
state classes before replaying the identical `-20 ... 0` terminal sequence.

Candidate state classes should be tested separately, for example:

- KC eligibility / rate traces;
- membrane / conductance state;
- visual-history state;
- combinations only after single-state controls.

That design can distinguish **which transient state** carries the benefit of
the extra 40 decisions.

## Claim state

All remain false:

- `learning_validated`
- `temporal_cue_index_confirmed`
- `prefix_sequence_specificity_confirmed`
- `memory_expression_causal`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
