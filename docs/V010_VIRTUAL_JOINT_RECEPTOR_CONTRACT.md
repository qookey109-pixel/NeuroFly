# V0.10 Virtual Joint Receptor Contract

Status: pre-runtime engineering contract. No proprioceptive current and no normal-runtime proprioceptive input are enabled by this stage.

## Why this stage exists

The V0.10 FeCO functional crosswalk established a conservative 102-neuron hook+club candidate subset, but a neuron population alone does not define a biological input signal.

NeuroFly must not inject world-space game variables such as `x/y`, heading, raw velocity, route progress, reward, or desired action and call them proprioception.

A receptor-accessible body layer must exist first.

## V0.10 first receptor contract

Model:

`neurofly-feco-motion-proxy-v0.1`

Encoding:

`virtual-joint-motion-only-proxy`

The contract takes only internal virtual joint mechanics as its transducer input:

- signed joint displacement for one internal body step;
- internal mechanical vibration magnitude.

Those private body variables are transformed into bounded receptor-like channels:

- `hook_extension`
- `hook_flexion`
- `club_motion`
- `club_vibration`

The signed joint displacement itself is **not** exported to neural input.

## Directional hook proxy

A positive internal joint displacement produces only `hook_extension`.
A negative internal joint displacement produces only `hook_flexion`.
The two directional channels are mutually exclusive.

This is an engineering motion-direction proxy consistent with the current hook functional crosswalk. It is not a validated reconstruction of natural FeCO receptor mechanics.

## Club proxy

The absolute internal joint displacement produces `club_motion`.
An independent internal mechanical vibration magnitude produces `club_vibration`.

Both are bounded to `[0, 1]`.

## Claw remains unavailable

There is deliberately **no claw position channel** in this contract.

The conservative pinned MaleCNS crosswalk did not authorize the current `SNpp50/51` exact labels because they crossed curator annotation boundaries. Therefore:

`claw_position_available=false`

must remain a hard gate.

## Forbidden shortcuts

The following must not be used as direct proprioceptive neural input:

- world `x/y` position;
- heading;
- raw game velocity;
- world displacement;
- map geometry;
- route progress;
- collision target identity;
- reward;
- desired action;
- raw motor command labels such as `FORWARD` / `TURN_LEFT` / `TURN_RIGHT`.

A later body-dynamics layer may use motor output to drive a physical virtual joint model, but the neural sensory payload must contain only the resulting receptor-like mechanical channels.

## Runtime boundary

This stage does not yet connect `neurofly-feco-motion-proxy-v0.1` to `MaleCNSBrain` or `GoalMazeSession`.

Hard flags remain:

- `stimulation_enabled=false`
- `runtime_transduction_enabled=false`

The next implementation stage must define how the compact NeuroFly body produces internal joint mechanics without reading solved world geometry. Only after that body mechanics layer is validated should prepared-MaleCNS proprioceptive current calibration be considered.

## Relationship to the crosswalk

Current clean crosswalk population:

- `SNpp39`: 39 hook candidates
- `SNpp58`: 16 club candidates
- `SNpp59`: 6 club candidates
- `SNpp60`: 41 club candidates

Total: 102 candidates.

This document does not authorize current injection into those neurons. It only defines the first allowed receptor-domain data shape that a future runtime adapter may consume.
