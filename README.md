# NeuroFly 🧠🪰

**NeuroFly** is an experimental connectome-driven agent playground built around the Drosophila nervous system.

The project starts from the MaleCNS v1.0 connectome and is designed to let the same neural substrate interact with different environments: visual worlds, small games, mazes, control tasks, and market simulations.

## Project goal

NeuroFly is **not** a claim that a connectome reconstruction is a complete living fly or that biological intelligence has been reproduced. It is a platform for controlled experiments that ask a simpler question:

> What interesting behavior emerges when a real anatomical wiring diagram is placed behind different sensory and action adapters?

## First game experiment: Maze Chase

The first formal game environment is **Maze Chase**, an original maze-chase experiment built for connectome learning research. It uses the general arcade pattern of collecting pellets, navigating corridors, avoiding enemies and receiving temporary power-state opportunities, without copying protected Pac-Man maps, characters, art, audio or branding.

The first runnable milestone is deliberately small:

```text
RGB maze frame
   -> visual adapter
   -> NeuroFly brain
   -> LEFT / RIGHT / FORWARD / HOLD
   -> maze environment
   -> reward / aversive feedback
   -> plasticity
```

The initial environment contains a deterministic maze, food, energy-food and autonomous enemies. It is validated with a visible baseline agent before connectome learning is enabled. See [`docs/experiments/MAZE_CHASE.md`](docs/experiments/MAZE_CHASE.md).

### Visualizer

A browser-based live visualizer is available in [`site/`](site/). It includes:

- an original fly character rendered directly on the maze canvas;
- food and energy-food;
- autonomous enemies;
- episode/reset behavior;
- live reward, survival and action telemetry;
- a visible Brain I/O panel;
- pause/reset/speed controls.

The current visualizer intentionally labels its controller as **Demo Agent**. It validates the game/environment interface and does not pretend that demo telemetry is MaleCNS activity.

GitHub Pages deployment is defined in [`.github/workflows/pages.yml`](.github/workflows/pages.yml). After Pages is enabled for the repository and the deployment reaches `main`, the expected project URL is:

`https://qookey109-pixel.github.io/NeuroFly/`

### 24/7 operation

The public website can stay hosted 24/7, but browser-side simulation stops when the page is closed or suspended. A fly that keeps learning while nobody is watching requires an always-on NeuroFly brain worker running separately from the website.

See [`docs/24_7_RUNTIME.md`](docs/24_7_RUNTIME.md) for the persistent runtime architecture.

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

## Playground ideas

- **Maze Chase** — first formal game experiment: pellets, maze navigation, enemies and reinforcement.
- **Light Chase** — let the connectome control a tiny agent that tries to orient toward a moving light.
- **Neuro Maze** — map selected descending-neuron activity to left/right/forward movement.
- **Brain Scope** — visualize which neural populations become active while changing controlled stimuli.
- **Connectome Arcade** — plug the same neural core into small browser/game environments.
- **Dopamine Lab** — compare engineered reinforcement schedules and plasticity controls.
- **Stonkfly Replay** — reproduce the paper-trading experiment in an isolated adapter and compare against controls.
- **Sensory Swap** — show the same brain price charts, geometry, motion and game frames and compare neural responses.

## Safety and interpretation

NeuroFly separates experimental neural proposals from real-world actions. Environments that can move money, control external hardware, or cause other side effects should remain opt-in and guarded. Paper/simulated environments are the default.

Any learning, intelligence, market skill, pain, pleasure, consciousness, or biological fidelity claim requires evidence beyond neural activity or changing weights.

## Status

**v0.2 — Maze Chase visualizer / browser environment / 24/7 runtime design**

Current work:

- establish provenance and licensing;
- pin the first Stonkfly upstream revision;
- create a clean experiment/adaptor architecture;
- keep large MaleCNS datasets outside Git history;
- run the Maze Chase visual environment with an autonomous baseline controller;
- deploy the visualizer through GitHub Pages;
- prepare the persistent backend interface for real MaleCNS telemetry.

## Development

Python 3.11+ is the initial target.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
python -m neurofly ideas
pytest -q
```

Run the visualizer locally:

```bash
python3 -m http.server 4173 --directory site
```

Then open `http://127.0.0.1:4173/`.

Optional Stonkfly reference installation:

```bash
pip install -e '.[stonkfly]'
python -m neurofly upstream-status
```

The optional dependency is pinned to the reviewed upstream commit rather than following `main` automatically.
