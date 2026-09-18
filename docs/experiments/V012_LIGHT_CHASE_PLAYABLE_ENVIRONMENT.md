# V0.12 Light Chase — Playable Sensory-Driven Environment

## Goal

Turn Light Chase from a project idea into a second executable NeuroFly
environment.

Maze Chase remains the primary training game. Light Chase exists to prove that
the brain/environment boundary is reusable rather than hard-wired to a maze.

## Environment

The world contains:

- one agent with position and cardinal heading;
- one movable light target;
- a bounded arena;
- TURN_LEFT, TURN_RIGHT, FORWARD and HOLD actions.

Moving closer to the light produces a small engineered progress reward.
Reaching the light produces a larger reward and relocates the target.

The reward policy is an engineered task definition, not a biological claim.

## Neural input

The brain does not receive the world map or target geometry.

Each decision receives:

1. an egocentric RGB frame containing a bright light cue;
2. a non-spatial sensory contract identifying the frame model.

The context explicitly declares that target coordinates, target bearing,
target distance and recommended action are not exposed.

The target's horizontal retinal position changes with agent heading and its
retinal size changes with distance.

## Privileged state separation

Target coordinates remain available in public/evaluation state so a website or
experiment evaluator can render and score the task.

They are never copied into brain context.

This distinction is intentional:

environment authority may know the world;
evaluation/UI may inspect the world;
the neural agent must sense the world.

## MaleCNS compatibility

The existing MaleCNS backend already accepts an RGB frame even when Maze-specific
fly geometry is absent. In that case it sends the supplied frame into the pinned
visual dynamics instead of reconstructing a Maze panorama.

Therefore Light Chase can use the same BrainBackend interface without adding a
privileged target adapter.

This PR adds the environment/session contract and deterministic tests. A later
real-MaleCNS receipt should be used before claiming successful Light Chase
behavior from the full connectome.

## Persistence

Light Chase saves:

- agent state;
- target state;
- counters;
- Python RNG state;
- pending reinforcement.

The brain checkpoint remains a separate coordinated file, matching the general
NeuroFly persistence pattern.

## Completion meaning

Passing CI means Light Chase is a playable environment contract with a
sensory-only brain boundary and restartable world state.

It does not prove that MaleCNS has learned to seek the light.
