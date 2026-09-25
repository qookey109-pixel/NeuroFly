# V1 Memory Interaction Diversity Recovery

Status: **PREREGISTERED EXPLORATORY EXECUTION**

## Why this recovery exists

Physical-state interaction Run 1 executed correctly but its four configured
environment seeds collapsed onto one replay-relevant neural history.

Different trajectory receipt digests were not sufficient evidence of neural
diversity because context contains wall-clock-derived fields such as
`survival_seconds`.

Run 1 is therefore frozen as:

**configured n = 4; effective neural n = 1**

This recovery fixes seed selection without looking at memory-expression
outcomes.

## Frozen candidate pool

In exact order:

`5003, 5009, 5011, 5021, 5023, 5039, 5051, 5059, 5077, 5081, 5087, 5099, 5101, 5107, 5113, 5119, 5147, 5153, 5167, 5171`

No candidate may be inserted, removed or reordered after execution begins.

## Outcome-blind neural-diversity gate

For each candidate in frozen order:

1. run acquisition only;
2. select the first natural reward at or after decision 60;
3. build the pre-event brain checkpoint;
4. compute its SHA-256;
5. compute a stable sensory-sequence digest for lags `-60...0`.

The stable sensory digest includes frame SHA-256 plus canonical context after
recursively removing only these volatile time keys:

- `survival_seconds`
- `total_active_seconds`
- `first_clear_seconds`
- `latest_clear_seconds`
- `best_clear_seconds`
- `seconds`

A candidate is accepted only if **both** its pre-event checkpoint digest and
stable sensory-sequence digest are unique among already accepted candidates.

Stop at the first four accepted candidates.

If fewer than four candidates qualify, the study fails closed.

No paired memory branch, A/B intervention or memory-expression endpoint may be
computed until the four selected candidates are frozen to a selection
manifest.

## Expression conditions after selection freeze

For each of the four selected histories:

- intact
- coherent scheduler rebuild
- A: clear `v/g + adaptation`
- B: clear `luminance + refractory + queue + queue_count`
- A+B: clear both subsystems

Shared replay geometry remains exact `-60...-21` prefix plus exact
`-20...0` terminal window, learning frozen and zero recall reinforcement.

## Interaction contrast

For each endpoint:

`A+B - A - B + intact`

Negative values mean combined clearing suppresses expression more than the
additive single-subsystem effects predict.

## Governance

This is exploratory mechanism recovery, not confirmatory promotion.

No production checkpoint, decoder, reward pulse, KC threshold, MBON weight or
learning parameter changes.

All promotion/causal locks remain false.
