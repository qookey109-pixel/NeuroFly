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

### Action autonomy boundary

The decoded MaleCNS locomotor action is authoritative. NeuroFly may change only the
environmental sensory/reinforcement inputs presented to the agent; it must not
replace a decoded `HOLD`, `FORWARD`, `TURN_LEFT` or `TURN_RIGHT` with a
hand-authored movement. Stall detection never changes the decoded action. Under curriculum v4, sustained
translational stalls produce the same bounded, non-directional aversive pulse
after four stalled decisions and on each subsequent stalled decision until the
fly autonomously turns or moves. The fly still decides whether to hold, move
forward or turn. If behavior needs
to change further, the experiment must do so through reviewed sensory or
reinforcement stimuli rather than direct action overrides.

## V0.4 — Full MaleCNS Smoke + Zero-Cost Runner

V0.4 adds the operational boundary between "the code is connected" and "the full connectome actually ran", while keeping the default execution path at **zero cloud cost**.

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

Stonkfly recommends **16 GB RAM** and several GB of storage. `real-smoke` applies a low-memory guard below 12 GiB unless explicitly overridden.

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

## Free full-MaleCNS runner

The repository includes [`.github/workflows/full-malecns-free.yml`](.github/workflows/full-malecns-free.yml).

For this public repository it uses the standard `ubuntu-latest` GitHub-hosted runner rather than a paid larger runner. The workflow is bounded to 330 minutes and is designed for resumable chunks instead of pretending to be a permanent 24/7 VM.

The free runner:

1. restores a cached prepared MaleCNS dataset when available;
2. restores the newest NeuroFly brain/Maze checkpoint cache;
3. installs the exact pinned Stonkfly revision;
4. runs `stonkfly prepare` / verification;
5. runs the real MaleCNS Maze smoke;
6. saves the prepared data only when it is below the 9 GB cache safety ceiling;
7. saves the latest resumable NeuroFly state separately;
8. publishes only small evidence receipts as short-retention artifacts.

This keeps the large static dataset out of Git history and keeps evidence artifacts small.

### Important free-mode limitation

GitHub-hosted jobs are finite sessions, not always-on servers. NeuroFly therefore treats free cloud execution as:

```text
restore checkpoint
      ↓
run bounded MaleCNS session
      ↓
save checkpoint
      ↓
runner stops
      ↓
next run resumes
```

That is enough for repeated experiments and learning checkpoints, but it is not literally one uninterrupted process running forever.

## Optional local / always-on runtime

If a machine with sufficient resources is already available, NeuroFly can still run continuously without changing the experiment format:

```bash
python -m neurofly maze-server \
  --brain malecns \
  --host 0.0.0.0 \
  --port 8765 \
  --checkpoint runs/maze-fly-001/brain.npz
```

The browser visualizer can use the same-origin API or a remote backend:

```text
https://qookey109-pixel.github.io/NeuroFly/?api=https://your-neurofly-backend.example
```

No paid hosting template is included in V0.4.

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

A GitHub Pages tab by itself is not a persistent brain process. In zero-cost mode, full-MaleCNS compute is executed in bounded GitHub Actions sessions and resumed from checkpoints.

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

**v0.4 — full MaleCNS smoke tooling / free 16 GB runner / resumable experiment state**

Implemented on the V0.4 development branch:

- V0.3 reusable `MaleCNSBrain` adapter and persistent Maze authority;
- host resource/prepared-data preflight;
- bounded real-brain smoke runner;
- hashed real-smoke receipt;
- free GitHub Actions full-MaleCNS workflow for this public repository;
- separate caching for prepared MaleCNS data and resumable NeuroFly state;
- no paid Render deployment template;
- CI coverage for Python, website/API, free-runner safety and pinned Stonkfly import compatibility.

`FULL_MALECNS_SMOKE_PASS` is claimed only after the free full-brain workflow (or another prepared host) actually executes `python -m neurofly real-smoke` and produces a valid receipt.

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
