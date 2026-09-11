# NeuroFly 🧠🪰

**NeuroFly** is an experimental connectome-driven agent playground built around the Drosophila nervous system.

The project starts from the MaleCNS v1.0 connectome and is designed to let the same neural substrate interact with different environments: visual worlds, small games, mazes, control tasks, and market simulations.

## Project goal

NeuroFly is **not** a claim that a connectome reconstruction is a complete living fly or that biological intelligence has been reproduced. It is a platform for controlled experiments that ask a simpler question:

> What interesting behavior emerges when a real anatomical wiring diagram is placed behind different sensory and action adapters?

## Stonkfly upstream

NeuroFly uses [`nftechie/stonkfly`](https://github.com/nftechie/stonkfly) as its first upstream/reference implementation.

Stonkfly demonstrates a MaleCNS-based spiking-network experiment that turns a rendered BTC-USDC chart into visual neural input, advances a retained 166,700-neuron graph, decodes neural activity into buy/sell/hold proposals, and optionally paper-trades or executes guarded Coinbase Advanced orders.

NeuroFly does **not** make trading the core architecture. Instead, Stonkfly is treated as one optional adapter/reference so that the same connectome ideas can be reused for other environments.

The initial upstream pin is:

```text
repository: https://github.com/nftechie/stonkfly
commit: 78ef3e05ab0fa086032098558d893667068944a0
license: MIT
```

See [`THIRD_PARTY.md`](THIRD_PARTY.md) for attribution and data licensing.

## Planned architecture

```text
MaleCNS v1.0
     │
     ▼
Connectome Core
     │
     ├── Sensory adapters
     │    ├── vision
     │    ├── light / color
     │    ├── game state
     │    └── market chart
     │
     ├── Neural simulation
     │    ├── graph
     │    ├── dynamics
     │    ├── state
     │    └── plasticity / modulation experiments
     │
     └── Action adapters
          ├── move / turn
          ├── maze navigation
          ├── game controller
          ├── robot-style control
          └── paper trading
```

## First playground ideas

- **Light Chase** — let the connectome control a tiny agent that tries to orient toward a moving light.
- **Neuro Maze** — map selected descending-neuron activity to left/right/forward movement.
- **Brain Scope** — visualize which neural populations become active while stimuli change.
- **Connectome Arcade** — plug the same neural core into small browser/game environments.
- **Dopamine Lab** — compare different engineered reinforcement signals without claiming biological equivalence.
- **Stonkfly Replay** — reproduce the paper-trading experiment in an isolated adapter and compare against controls.
- **Sensory Swap** — show the same brain price charts, geometric shapes, motion fields, or game frames and compare neural responses.

## Safety and interpretation

NeuroFly separates experimental neural proposals from real-world actions. Environments that can move money, control external hardware, or cause other side effects should remain opt-in and guarded. Paper/simulated environments are the default.

Any learning, intelligence, market skill, pain, pleasure, consciousness, or biological fidelity claim requires evidence beyond neural activity or changing weights.

## Status

**v0.1 — platform bootstrap / Stonkfly upstream integration**

Current work:

- establish provenance and licensing
- pin the first Stonkfly upstream revision
- create a clean experiment/adaptor architecture
- keep large MaleCNS datasets outside Git history
- add a minimal runnable NeuroFly CLI before integrating the full connectome runtime

## Development

Python 3.11+ is the initial target.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
python -m neurofly ideas
pytest -q
```

Optional Stonkfly reference installation:

```bash
pip install -e '.[stonkfly]'
python -m neurofly upstream-status
```

The optional dependency is pinned to the reviewed upstream commit rather than following `main` automatically.
