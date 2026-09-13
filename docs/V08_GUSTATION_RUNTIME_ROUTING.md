# V0.8 Gustation — calibrated runtime routing

Status: implementation under Draft PR validation. No behavioral-benefit claim.

## Purpose

Connect the already calibrated MaleCNS gustatory populations to normal NeuroFly runtime without turning taste into reward and without allowing taste at a distance.

## Calibrated populations

Only the conservative functional crosswalk is routed:

- `bitter` → exact MaleCNS type `LB1b` → 6 neurons → calibrated current `8.0`
- `sugar_water` → exact MaleCNS types `LB3a`, `LB3b`, `LB3c`, `LB3d` → 77 neurons → calibrated current `8.0`

Calibration receipt:

`595054789f40c1039b8393d32f797db299dad93b4153eecb5547fb9e7fc62610`

All other 1,345 curator-labelled gustatory neurons remain unresolved and unused.

## One-shot contact timing

Normal gameplay does not infer taste from visible food, odor, reward size, route, coordinates or the final public step event.

The session detects a real food contact by observing that the environment's cumulative eaten-food count increased during the applied agent step. It queues one private `food` gustatory event.

At the beginning of the next neural decision:

1. the pending event is converted by `contact_gustation()` into a strict `sugar_water=1.0` payload;
2. the pending event is immediately consumed;
3. MaleCNS routes that payload to the mapped LB3a-d population for that neural decision;
4. if no new food is contacted, the following decision receives zero taste.

This remains correct when eating the last pellet promotes the public event to `maze_cleared`, because taste is based on actual food consumption rather than the overwritten public event label.

Pending taste is persisted in session checkpoints so a crash/restart does not silently erase an already occurred biological contact. Restored pending taste is still consumed once.

## Taste is not reinforcement

Gustatory stimulation and reinforcement stimulation are separate runtime paths.

A food contact may independently cause both:

- a later one-shot sensory `sugar_water` pulse because the fly contacted food;
- the existing reinforcement signal because the environment reward policy assigns a reward.

The numerical reward magnitude never sets taste intensity. Changing food reward does not alter the `sugar_water=1.0` contact signal.

No rule states that sugar/water is intrinsically rewarding or bitter is intrinsically aversive.

## Wind remains enabled

The user-selected V0.7 policy remains unchanged: normal curriculum ambient airflow and calibrated JO-C/JO-E mechanosensation stay active while gustation is present. Taste does not disable, replace or gate wind sensation.

## Hard runtime gates

MaleCNS runtime rejects:

- unknown gustation model or crosswalk schema;
- privileged game-state fields inside the gustation payload;
- channel values outside `[0,1]`;
- disagreement between the `contact` flag and nonzero taste channels;
- gustatory currents other than `0.0` internal compatibility or calibrated `8.0`;
- missing mapped GRN types;
- mapped type rows not curator-classified `gustatory`;
- mapped population-count drift away from 6 bitter / 77 sugar-water neurons.

## Validation target

The prepared-MaleCNS runtime smoke must prove:

- no-contact payload creates no direct taste pulses;
- sugar/water contact yields positive LB3a-d response;
- synthetic bitter contact yields positive LB1b response;
- ambient JO airflow is still active during both taste conditions;
- frozen memory SHA stays unchanged;
- unresolved gustatory neurons remain unused.

A PASS validates runtime signal routing only. It does not prove natural receptor physiology, feeding preference, taste valence, navigation improvement, learning benefit or ecological realism.
