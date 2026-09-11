# NeuroFly Architecture

## Design rule

NeuroFly keeps the connectome experiment platform independent from any single environment. Trading, games, mazes, robotics-style control and visualization should attach through adapters rather than becoming assumptions inside the neural core.

## Layers

### 1. Provenance / datasets

Responsibilities:
- identify upstream datasets and exact releases
- verify checksums before preprocessing
- keep large raw data outside Git history
- retain required attribution and licenses
- distinguish source anatomy from NeuroFly-derived artifacts

Initial source: MaleCNS v1.0.

### 2. Connectome core

Responsibilities:
- neuron/cell identity and metadata
- graph construction and retained-edge policy
- transmitter/sign interpretation
- compiled graph arrays
- reproducible preprocessing receipts

The first implementation may reuse or adapt ideas from Stonkfly/DOOMFLY, but NeuroFly should expose its own stable interfaces.

### 3. Dynamics

Responsibilities:
- neural state
- time stepping / event processing
- configurable physiology approximations
- modulatory signals
- plasticity experiments
- deterministic seeds and resumable state

Model assumptions must be explicit and versioned.

### 4. Sensory adapters

A sensory adapter converts an environment observation into stimulation without changing the environment policy itself.

Examples:
- RGB/light field → visual inputs
- game frame → visual inputs
- maze landmarks → visual inputs
- market chart image → visual inputs

Raw market indicators should not silently bypass the visual/connectome pathway in experiments claiming image-driven behavior.

### 5. Action decoders

An action decoder converts measured neural activity into a bounded proposal.

Examples:
- turn left / right
- move forward
- choose target
- buy / hold / sell proposal

The decoder is an engineered interface, not a biological discovery. Its neuron selections, thresholds and mappings must be logged.

### 6. Environments

Environments execute proposals and return the next observation/reward/measurement.

Initial targets:
- Light Chase
- Neuro Maze
- Connectome Arcade
- Stonkfly Replay (paper/simulation only by default)

External side effects are never part of the core loop. Real-money or hardware actions require a separate guarded adapter and explicit opt-in.

### 7. Evaluation

Every experiment should support controls appropriate to its claim, such as:
- frozen weights
- shuffled reinforcement
- randomized decoder
- disconnected sensory input
- simple baseline policies
- multiple deterministic seeds
- held-out replay where applicable

Neural activity or weight changes alone do not establish useful learning.

## Stonkfly relationship

Stonkfly is the first reference/upstream implementation, initially pinned to commit:

`78ef3e05ab0fa086032098558d893667068944a0`

NeuroFly supports three integration levels:

1. **Reference** — inspect and compare the upstream implementation without importing it.
2. **Optional dependency** — install the pinned Stonkfly package for replay/comparison experiments.
3. **Adapted component** — copy/adapt a component only when NeuroFly needs ownership of its interface; preserve MIT attribution for copied/substantial upstream code.

We intentionally avoid making Stonkfly a Git submodule or the NeuroFly core. This keeps upstream history inspectable while allowing NeuroFly to evolve independently.
