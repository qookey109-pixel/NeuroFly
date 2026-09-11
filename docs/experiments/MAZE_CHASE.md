# Maze Chase — NeuroFly Experiment 001

Maze Chase is the first game environment for NeuroFly. It is an original maze-chase experiment inspired by the general arcade pattern of navigating corridors, collecting pellets, avoiding enemies, and temporarily reversing the risk relationship after consuming a power item. It must not copy protected Pac-Man maps, characters, art, audio, or branding.

## Research question

Can the same MaleCNS-derived connectome substrate produce measurably different navigation behavior after repeated exposure to visual observations and engineered reinforcement?

The goal is not to claim that the fly "understands" the game. The goal is to measure whether controlled sensory-action-reward coupling changes behavior in a reproducible way.

## Environment loop

```text
rendered game frame
    -> visual sensory adapter
    -> NeuroFly connectome runtime
    -> neural activity
    -> bounded action decoder
    -> Maze Chase environment
    -> reward / aversive event
    -> modulation / plasticity
    -> next frame
```

## Phase 1 action space

Keep the first action space deliberately small:

- TURN_LEFT
- TURN_RIGHT
- FORWARD
- HOLD

The environment should prevent illegal movement through walls rather than teaching a physics engine.

A later phase may use absolute UP/DOWN/LEFT/RIGHT actions for controlled comparison.

## Visual observation

Primary path: render an RGB game view and feed it through the visual adapter rather than exposing maze coordinates directly to the brain.

Initial renderer requirements:

- deterministic rendering
- high-contrast corridors and pellets
- distinct enemy and power-item colors
- fixed camera geometry
- no hidden policy-relevant metadata in the image

A symbolic observation mode may exist only as a control experiment and must be labeled separately.

## Reward design

Initial engineered reinforcement schedule:

| Event | Score | Neural feedback |
| --- | ---: | --- |
| ordinary pellet | +0.05 | small positive accumulator |
| power item | +0.50 | positive reward |
| enemy captured during power state | +1.00 | positive reward |
| maze cleared | +5.00 | strong positive reward |
| invalid/wall action | -0.02 | no reward; logged penalty |
| agent captured / life lost | -2.00 | aversive signal |
| idle step | -0.001 | score-only pressure; no direct aversive pulse initially |

Reward shaping is an engineered experimental choice, not biological feeding physiology. The mapping to PAM/PPL-like circuits must remain configurable and logged.

## Training curriculum

### Stage A — Sensorimotor sanity

- empty corridor
- pellet directly ahead
- no enemies
- verify visual input changes neural activity
- verify decoder can produce bounded movement

### Stage B — Choice junction

- T-junction
- one branch contains pellets
- repeat with mirrored layouts
- measure left/right bias and adaptation

### Stage C — Small maze

- pellets
- no enemies
- reward efficient collection
- compare trained vs frozen-weight control

### Stage D — Avoidance

- introduce one deterministic enemy
- measure survival time and collision rate
- compare reward-only vs reward+aversive configurations

### Stage E — Full Maze Chase

- multiple enemies
- power item
- pellet clearing objective
- randomized but seeded layouts

## Measurements

Every episode should record at least:

- seed
- brain/checkpoint identity
- steps survived
- pellets collected
- maze completion
- wall/invalid actions
- enemy collisions
- path trace
- action distribution
- total reward
- reward and aversive pulse counts
- selected neural population firing summaries
- synaptic/plasticity state hash
- wall-clock compute time

## Required controls

Before any learning claim, compare against:

1. random action agent
2. fixed-rule baseline
3. NeuroFly with frozen weights
4. NeuroFly with shuffled reward timing
5. NeuroFly with randomized action decoder
6. multiple deterministic seeds
7. held-out maze layouts

Improved score alone is not enough; the behavior must survive appropriate controls.

## First implementation target

The first runnable milestone is intentionally smaller than full Pac-Man-like gameplay:

**one deterministic maze + pellets + one enemy + RGB renderer + four actions + episode log**.

The connectome integration comes after the environment can be replayed deterministically with baseline agents. This prevents game bugs from being mistaken for neural learning.
