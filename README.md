# NeuroFly 🧠🪰

**NeuroFly** is an experimental connectome-driven agent playground built around the Drosophila nervous system.

The project starts from the MaleCNS v1.0 connectome and is designed to let the same neural substrate interact with different environments: visual worlds, small games, mazes, control tasks and market simulations.

## Project goal

NeuroFly is **not** a claim that a connectome reconstruction is a complete living fly or that biological intelligence has been reproduced. It is a controlled platform for asking:

> What behavior emerges when a real anatomical wiring diagram is placed behind different sensory, action and reward adapters?

## First game experiment — Maze Chase

Maze Chase is an original maze-chase environment for connectome experiments. It uses food collection, navigation, enemies and temporary power states without copying protected Pac-Man maps, characters, art, audio or branding.

```text
Maze RGB frame
   -> MaleCNS visual adapter
   -> 166,700-neuron retained runtime
   -> DNp20 / DNpe017 readout
   -> TURN_LEFT / TURN_RIGHT / FORWARD / HOLD
   -> Maze Chase
   -> reward / aversive stimulation
   -> plasticity
   -> checkpoint
```

The action mapping is an engineered NeuroFly interface, not a biological claim about what those neurons naturally encode.

## V0.4 — Full MaleCNS Smoke + Cloud-Ready Runtime

V0.4 adds the operational boundary between "the code is connected" and "the full connectome actually ran".

### 1. Host preflight

```bash
python -m neurofly host-preflight
```

The report checks:

- Python 3.11+;
- C++ compiler availability;
- pinned Stonkfly installation;
- verified prepared MaleCNS graph;
- detected RAM;
- free disk space.

The first operational profile targets **16 GiB RAM** and **20 GiB free disk**. `real-smoke` applies a low-memory guard below 12 GiB unless explicitly overridden.

### 2. Prepare MaleCNS

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e '.[test,stonkfly]'

export STONKFLY_DATA="$PWD/.cache/stonkfly"
python -m stonkfly prepare
python -m neurofly host-preflight
```

The pinned upstream preparation downloads and checksum-verifies the released MaleCNS inputs and compiles the retained graph.

### 3. Run the first real-brain smoke

```bash
python -m neurofly real-smoke \
  --steps 1 \
  --checkpoint runs/maze-fly-001/brain.npz \
  --receipt runs/maze-fly-001/real-smoke-receipt.json
```

A successful receipt records the pinned upstream revision, host information, seed, action, reward, neural simulation time, compute time, spike counts, memory hash and a SHA-256 digest over the receipt.

Ordinary CI does **not** count as a full MaleCNS execution because CI deliberately does not download the multi-GB dataset.

## 24/7 runtime

### Direct persistent server

```bash
python -m neurofly maze-server \
  --brain malecns \
  --host 0.0.0.0 \
  --port 8765 \
  --checkpoint runs/maze-fly-001/brain.npz
```

### Cloud-safe first boot

```bash
python -m neurofly cloud-server \
  --host 0.0.0.0 \
  --port 8765 \
  --checkpoint /var/data/neurofly/maze-fly-001/brain.npz
```

`cloud-server` immediately exposes the website/API in a paused `preparing-malecns` phase. It performs MaleCNS preparation on the runtime disk in the background and **does not run DemoBrain actions** while preparation is in progress. Once verification and preflight pass, authority switches to `malecns-ready` and Maze episodes start.

The server exposes:

```text
GET  /api/status
GET  /api/state
POST /api/control
```

The browser visualizer can use the same-origin API or a remote backend:

```text
https://qookey109-pixel.github.io/NeuroFly/?api=https://your-neurofly-backend.example
```

## Render deployment template

The repository includes [`render.yaml`](render.yaml) for an optional always-on deployment profile:

```text
Region: Singapore
Compute: 2 CPU / 16 GB RAM
Persistent disk: 20 GB mounted at /var/data
STONKFLY_DATA: /var/data/stonkfly
Auto deploy: OFF
Health: /api/status
```

The Blueprint intentionally has `autoDeployTrigger: off`. Creating or syncing the service can provision paid cloud resources, so NeuroFly does not create the service automatically.

## Visualizer

The browser visualizer lives in [`site/`](site/) and includes:

- an original fly character;
- food and energy-food;
- autonomous enemies;
- episode/reset behavior;
- reward, survival and action telemetry;
- Brain I/O telemetry;
- pause/reset/speed controls;
- persistent-backend auto-detection with browser-demo fallback.

GitHub Pages deployment is defined in [`.github/workflows/pages.yml`](.github/workflows/pages.yml). The expected project URL after the relevant changes reach `main` is:

`https://qookey109-pixel.github.io/NeuroFly/`

A GitHub Pages tab by itself is not a 24/7 brain process. The persistent runtime must live on an always-on host if the fly should keep running while all browsers are closed.

## Stonkfly upstream

NeuroFly uses [`nftechie/stonkfly`](https://github.com/nftechie/stonkfly) as its first upstream/reference implementation.

```text
repository: https://github.com/nftechie/stonkfly
commit: 78ef3e05ab0fa086032098558d893667068944a0
license: MIT
```

Stonkfly supplies the reference MaleCNS preparation, visual input, neural dynamics, plasticity and checkpoint machinery. NeuroFly keeps trading/Coinbase behavior outside its core and owns its own environment and action interface.

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

- **Maze Chase** — food, navigation, enemies and reinforcement.
- **Light Chase** — visual orientation toward moving light.
- **Neuro Maze** — navigation and memory tasks.
- **Brain Scope** — visualize population activity while controlled stimuli change.
- **Connectome Arcade** — common adapter interface for small games.
- **Dopamine Lab** — compare engineered reinforcement schedules and plasticity controls.
- **Stonkfly Replay** — reproduce the upstream paper-trading experiment in isolation.
- **Sensory Swap** — compare neural responses to geometry, game frames and market charts.

## Safety and interpretation

NeuroFly separates experimental neural proposals from real-world actions. Environments that move money, control hardware or cause external side effects are not part of the default core loop.

Neural activity, changing weights or improved game scores alone do not establish consciousness, pain, pleasure, biological fidelity, intelligence or useful learning. Claims require explicit controls and evaluation.

## Status

**v0.4 — full MaleCNS smoke tooling / cloud-safe bootstrap / deploy-ready 24/7 profile**

Implemented on the V0.4 development branch:

- V0.3 reusable `MaleCNSBrain` adapter and persistent Maze authority;
- host resource/prepared-data preflight;
- bounded real-brain smoke runner;
- hashed real-smoke receipt;
- paused cloud preparation phase;
- automatic promotion to MaleCNS only after verified preparation;
- persistent brain + Maze checkpoint support;
- guarded Render Blueprint with auto-deploy disabled;
- CI coverage for Python, website/API, Blueprint safety and pinned Stonkfly import compatibility.

`FULL_MALECNS_SMOKE_PASS` is intentionally **not** claimed until a prepared 16 GB-class host actually executes `python -m neurofly real-smoke` and produces the receipt.

See [`docs/V0_4_FULL_MALECNS_SMOKE.md`](docs/V0_4_FULL_MALECNS_SMOKE.md), [`docs/V0_3_REAL_BRAIN_RUNTIME.md`](docs/V0_3_REAL_BRAIN_RUNTIME.md) and [`docs/24_7_RUNTIME.md`](docs/24_7_RUNTIME.md).

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
python -m neurofly ideas
python -m neurofly maze-run --brain demo --steps 5 --interval 0 --checkpoint ""
pytest -q
```

The optional Stonkfly dependency is pinned to the reviewed upstream commit rather than following upstream `main` automatically.
