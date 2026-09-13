# V0.8 Gustation — Contact-only transduction

Status: sensory-contract implementation only. MaleCNS gustatory stimulation remains disabled.

## Purpose

NeuroFly may see or smell food before touching it, but it must not taste that food at a distance. This layer turns only a physical gustatory-contact event into bounded functional taste channels.

The environment may know exact food coordinates and reward values. The neural taste payload may not.

## Model

`neurofly-contact-gustation-v1`

The neural-eligible payload contains only:

- `contact`: whether a gustatory contact signal is active
- `channels.bitter`: bounded `[0, 1]`
- `channels.sugar_water`: bounded `[0, 1]`
- model / encoding / crosswalk provenance
- `stimulation_enabled: false`

It does not contain food coordinates, distance, route, target action, reward, edible flags, or global world geometry.

## Current maze mapping

The existing maze has only edible food events. `food` and `energy_food` therefore create a unit `sugar_water` contact pulse. This is intentionally not called pure sugar: the conservative MaleCNS crosswalk maps LB3a/LB3b/LB3c/LB3d to the curated FlyWire `LB3` sugar/water functional class.

Non-gustatory game events such as capture or maze clear create no taste signal.

An explicit `bitter` contact channel exists for later environments, but current maze state never infers it automatically.

## Evidence dependency

This layer depends on the conservative functional crosswalk established immediately before it:

- LB1b -> bitter: 6 retained MaleCNS neurons
- LB3a/LB3b/LB3c/LB3d -> sugar_water: 77 retained MaleCNS neurons
- mapped total: 83 / 1,428 curator-labelled gustatory neurons
- unresolved: 1,345

Unresolved neurons remain unused.

## Safety boundary

This change does **not** inject current into LB1b or LB3 neurons. The next gate is a prepared-MaleCNS current calibration/sweep performed with synthetic contact payloads. Only a validated current may later be connected to the normal runtime.

## Invariants

1. Visible/smellable food without physical contact yields zero taste channels.
2. Food contact yields `sugar_water=1.0`, `bitter=0.0` in the current maze proxy.
3. Game events unrelated to taste yield zero channels.
4. No reward value or food coordinates enter the gustatory payload.
5. All channel intensities are bounded to `[0, 1]`.
6. `stimulation_enabled` stays false in this stage.
