# NeuroFly 🧠🪰

**NeuroFly** is an experimental connectome-driven agent playground built around the Drosophila nervous system.

The project starts from the MaleCNS v1.0 connectome and is designed to let the same neural substrate interact with different environments: visual worlds, small games, mazes, control tasks, and market simulations.

## Project goal

NeuroFly is **not** a claim that a connectome reconstruction is a complete living fly or that biological intelligence has been reproduced. It is a platform for controlled experiments that ask a simpler question:

> What interesting behavior emerges when a real anatomical wiring diagram is placed behind different sensory and action adapters?

## First game experiment: Maze Chase

The first formal game environment is **Maze Chase**, an original maze-chase experiment built for connectome learning research. It uses the general arcade pattern of collecting food, navigating corridors, avoiding enemies and receiving temporary power-state opportunities, without copying protected Pac-Man maps, characters, art, audio or branding.

V0.3 supports this loop:

```text
Maze RGB frame
   -> MaleCNS visual adapter
   -> retained connectome runtime
   -> DNp20 / DNpe017 readout
   -> TURN_LEFT / TURN_RIGHT / FORWARD / HOLD
   -> Maze Chase environment
   -> reward / aversive signal
   -> plasticity
   -> checkpoint
```

The action mapping is an engineered NeuroFly interface, not a biological claim about what those neurons naturally encode.

## V0.3 — Real Brain Runtime

V0.3 separates the **world authority** from the browser. A headless Python Maze runtime can continue running even when nobody has the website open.

Two brain backends are available:

- `demo` — lightweight deterministic baseline used by CI and browser fallback;
- `malecns` — the pinned Stonkfly `VisualMemoryBrain` using prepared MaleCNS v1.0 data.

### Check the real brain runtime

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e '.[test,stonkfly]'
python -m stonkfly prepare
python -m neurofly brain-status
```

`stonkfly prepare` downloads and checksum-verifies the released MaleCNS inputs, prepares the retained graph and requires several GB of storage. A C++17 compiler is required for the native neural kernel.

### Run headless 24/7-style training

```bash
python -m neurofly maze-run \
  --brain malecns \
  --checkpoint runs/maze-fly-001/brain.npz
```

The process owns the Maze state, reward loop and neural decisions. Brain checkpoints are written periodically and can be restored on restart.

### Run the live website + API

```bash
python -m neurofly maze-server \
  --brain malecns \
  --host 0.0.0.0 \
  --port 8765 \
  --checkpoint runs/maze-fly-001/brain.npz
```

Then open:

`http://127.0.0.1:8765/`

The same server exposes:

```text
GET  /api/status
GET  /api/state
POST /api/control
```

The visualizer automatically detects a same-origin NeuroFly API. When using GitHub Pages with a separately hosted backend, append:

```text
?api=https://your-neurofly-backend.example
```

The UI clearly labels whether telemetry comes from `Demo Agent` or the `MaleCNS` backend.

See [`docs/V0_3_REAL_BRAIN_RUNTIME.md`](docs/V0_3_REAL_BRAIN_RUNTIME.md) and [`docs/24_7_RUNTIME.md`](docs/24_7_RUNTIME.md).

## Visualizer

The browser visualizer lives in [`site/`](site/) and contains:

- an original fly character;
- food and energy-food;
- autonomous enemies;
- episode/reset behavior;
- reward, survival and action telemetry;
- live Brain I/O telemetry;
- pause/reset/speed controls;
- persistent-backend auto-detection with browser demo fallback.

GitHub Pages deployment is defined in [`.github/workflows/pages.yml`](.github/workflows/pages.yml). After Pages is enabled and the relevant changes are on `main`, the expected project URL is:

`https://qookey109-pixel.github.io/NeuroFly/`

A GitHub Pages tab by itself is **not** a 24/7 brain process. The persistent `maze-run` or `maze-server` process must live on an always-on machine/service if the fly should keep learning while all browsers are closed.

## Stonkfly upstream

NeuroFly uses [`nftechie/stonkfly`](https://github.com/nftechie/stonkfly) as its first upstream/reference implementation.

The pinned revision is:

```text
repository: https://github.com/nftechie/stonkfly
commit: 78ef3e05ab0fa086032098558d893667068944a0
license: MIT
```

Stonkfly supplies a reference implementation for MaleCNS preparation, visual input, neural dynamics, plasticity and checkpointing. NeuroFly keeps market/Coinbase behavior outside its core and owns its own environment/action interface.

See [`THIRD_PARTY.md`](THIRD_PARTY.md) for attribution and data licensing.

## Architecture

```text
MaleCNS v1.0
     │
     ▼
Connectome / Dynamics
     │
     ├── Sensory adapters
     │    ├── RGB vision
     │    ├── light / color
     │    ├── game frames
     │    └── market charts
     │
     ├── Action decoders
     │    ├── movement / turn
     │    ├── game controls
     │    └── paper-trading proposals
     │
     └── Environments
          ├── Maze Chase
          ├── Light Chase
          ├── puzzle / cube
          ├── racing / arcade
          └── market replay
```

## Playground ideas

- **Maze Chase** — first formal game experiment: food, navigation, enemies and reinforcement.
- **Light Chase** — visual orientation toward a moving light.
- **Neuro Maze** — pure navigation and memory tasks.
- **Brain Scope** — visualize population activity while controlled stimuli change.
- **Connectome Arcade** — common adapter interface for small games.
- **Dopamine Lab** — compare engineered reinforcement schedules and plasticity controls.
- **Stonkfly Replay** — reproduce the upstream paper-trading experiment in isolation.
- **Sensory Swap** — compare neural responses to geometry, game frames and market charts.

## Safety and interpretation

NeuroFly separates experimental neural proposals from real-world actions. Environments that can move money, control external hardware or create other external side effects are not part of the default core loop.

Neural activity, changing weights or improved game scores alone do not establish consciousness, pain, pleasure, biological fidelity, intelligence or useful learning. Claims require explicit controls and evaluation.

## Status

**v0.3 — real brain runtime / persistent Maze server / MaleCNS adapter**

Implemented on the V0.3 development branch:

- headless Maze Chase environment;
- reusable Brain Backend contract;
- `DemoBrain` CI baseline;
- optional real `MaleCNSBrain` adapter;
- RGB Maze rendering for visual neural input;
- DNp20 / DNpe017 maze action decoder;
- reward / aversive stimulation path;
- persistent brain checkpoints;
- 24/7-compatible headless loop;
- HTTP state/control API;
- browser visualizer that can observe the persistent backend;
- CI smoke coverage without downloading the multi-GB MaleCNS dataset.

The ordinary GitHub CI verifies the runtime contract with the lightweight backend. A true 166,700-neuron smoke run requires a host on which the MaleCNS dataset has been prepared; it is not falsely reported as CI-tested when that dataset is absent.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
python -m neurofly ideas
python -m neurofly maze-run --brain demo --steps 5 --interval 0 --checkpoint ""
pytest -q
```

Optional real MaleCNS runtime:

```bash
pip install -e '.[stonkfly]'
python -m stonkfly prepare
python -m neurofly brain-status
```

The optional dependency is pinned to the reviewed upstream commit rather than following upstream `main` automatically.
