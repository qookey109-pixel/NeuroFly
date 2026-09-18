# V0.12 — NeuroFly Environment Adapter Contract

## Purpose

NeuroFly v1 is intended to be a reusable connectome-agent platform rather than
a single Maze Chase experiment.

This contract introduces one shared orchestration boundary for multiple games:

world truth
→ environment adapter
→ sensory-domain NeuralObservation
→ BrainBackend
→ action
→ environment

Maze Chase and Light Chase are the first two concrete adapters.

## Three state domains

NeuroFly now treats environment information as three separate domains.

### 1. World truth

The environment is allowed to know complete simulator state such as:

- agent coordinates;
- enemy coordinates;
- target coordinates;
- maze grid;
- source locations;
- internal RNG state.

This state belongs to the simulator/control plane.

### 2. Public and evaluation state

UI and evaluation code may inspect world truth when needed for visualization,
scoring, replay and debugging.

Public visibility does not make a field legal neural input.

### 3. Neural observation

The BrainBackend may receive only sensory-domain information.

The shared adapter firewall forbids direct fields such as:

- grid;
- fly/agent coordinates;
- enemy coordinates;
- target coordinates;
- source coordinates;
- exact distance/bearing diagnostics;
- demo action;
- route/goal direction;
- recommended action.

## Maze Chase adapter

Maze Chase historically renders a top-down world image for UI/debugging.

The adapter converts that world render into an egocentric retinal proxy before
the frame reaches BrainBackend.

Olfaction is generated from private world geometry, but the adapter removes
source coordinates and source distance before constructing neural context.

Only receptor-domain values such as bilateral left/right odor intensity remain.

## Light Chase adapter

Light Chase already renders an egocentric visual frame directly.

The adapter passes that sensory frame through the same NeuralObservation
contract without target coordinates, target bearing or target distance.

## Shared EnvironmentSession

EnvironmentSession now provides the common loop:

1. request a NeuralObservation;
2. validate the sensory-only context;
3. ask BrainBackend for an action;
4. apply that action through the adapter;
5. convert outcome reward into delayed reinforcement;
6. expose public/evaluation state separately;
7. checkpoint brain plus private environment state;
8. restore pending reinforcement after restart.

Both Maze Chase and Light Chase use the same action vocabulary:

- TURN_LEFT
- TURN_RIGHT
- FORWARD
- HOLD

## CLI

The common platform entry point is:

neurofly env-run --environment maze --brain demo

or:

neurofly env-run --environment light --brain demo

The older maze-run and light-run commands remain available for compatibility.

## Adding another environment

A future game should implement the adapter contract rather than introducing a
new custom brain/session glue path.

A new adapter must provide:

- sensory observation;
- action application;
- public snapshot;
- private persistence snapshot;
- restore;
- reset semantics.

The adapter must pass the same sensory-only context firewall before its output
is eligible for BrainBackend.

## Completion boundary

Passing CI for this stage means that two structurally different games are
proven to share the same sensory-only orchestration interface and restart
contract.

It does not mean that the full MaleCNS has learned either game, nor does it
authorize privileged simulator state as neural input.
