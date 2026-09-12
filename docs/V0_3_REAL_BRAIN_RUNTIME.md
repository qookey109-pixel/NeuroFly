# NeuroFly V0.3 — Real Brain Runtime

V0.3 connects the Maze Chase environment to an optional MaleCNS v1.0 neural runtime derived from the pinned Stonkfly implementation.

## Runtime loop

```text
Maze RGB frame
  -> MaleCNS visual adapter
  -> 166,700-neuron retained graph
  -> DNp20 / DNpe017 readout
  -> TURN_LEFT / TURN_RIGHT / FORWARD / HOLD
  -> Maze Chase environment
  -> reward / aversive event
  -> modulatory stimulation + plasticity
  -> checkpoint
```

The motor mapping is an engineered BCI-style interface, not a biological claim that these cells encode game actions.

## Modes

- `demo`: deterministic lightweight controller for CI and UI validation.
- `malecns`: real Stonkfly `VisualMemoryBrain` using the prepared MaleCNS v1.0 graph.

The site must label which backend produced telemetry.

## Real-brain prerequisites

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e '.[test,stonkfly]'
python -m stonkfly prepare
python -m neurofly brain-status
```

`stonkfly prepare` downloads and checksum-verifies the released MaleCNS inputs and compiles the retained graph. Several GB of local storage are required and a C++17 compiler is needed for the native neural kernel.

## Persistent training

For 24/7 operation, run the headless worker or API server on an always-on machine. Browser/GitHub Pages rendering is an observer, not the authority for neural state.

```bash
python -m neurofly maze-run --brain malecns --checkpoint runs/maze-fly-001/brain.npz
```

or

```bash
python -m neurofly maze-server --brain malecns --host 0.0.0.0 --port 8765 --checkpoint runs/maze-fly-001/brain.npz
```

The worker checkpoints periodically and restores the same brain state on restart when the checkpoint exists.

## V0.3 validation boundary

CI validates the complete runtime contract with the lightweight controller. CI does not download the multi-GB MaleCNS dataset. A real-brain smoke test therefore requires a prepared host and is reported separately from ordinary CI.
