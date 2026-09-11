# NeuroFly V0.4 — Full MaleCNS Smoke + Cloud-Ready Runtime

V0.4 turns the V0.3 integration contract into an operational runbook for the first real 166,700-neuron Maze Chase execution.

## Goals

1. detect whether a host is suitable before loading the full connectome;
2. run a bounded real-brain smoke test and write a machine-readable receipt;
3. preserve the exact Stonkfly upstream pin and MaleCNS provenance;
4. make first cloud boot health-safe while the large dataset is prepared;
5. keep cloud spending opt-in.

## Local / VPS preparation

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e '.[test,stonkfly]'

export STONKFLY_DATA="$PWD/.cache/stonkfly"
python -m stonkfly prepare
python -m neurofly host-preflight
```

The preflight reports Python, C++ compiler availability, Stonkfly installation, verified prepared graph status, detected host RAM and free disk.

NeuroFly treats 16 GiB RAM and 20 GiB free disk as recommended host targets for this first operational profile. A host below 12 GiB RAM trips a guard in `real-smoke` unless explicitly overridden.

## First real brain smoke

```bash
python -m neurofly real-smoke \
  --steps 1 \
  --checkpoint runs/maze-fly-001/brain.npz \
  --receipt runs/maze-fly-001/real-smoke-receipt.json
```

A successful receipt records:

- pinned Stonkfly commit;
- host and Python information;
- preflight report;
- exact step count and seed;
- action and reward;
- neural simulation time and wall compute time;
- total, reward, aversive and Kenyon-cell spike counts;
- memory-state hash when provided by the upstream runtime;
- a SHA-256 digest over the receipt itself.

The receipt is evidence that the full optional backend actually executed. Ordinary CI is intentionally not accepted as this evidence because CI does not download the multi-GB MaleCNS data.

## 24/7 cloud bootstrap

V0.4 adds:

```bash
python -m neurofly cloud-server \
  --host 0.0.0.0 \
  --port 8765 \
  --checkpoint /var/data/neurofly/maze-fly-001/brain.npz
```

Cloud bootstrap behavior:

1. HTTP/API starts immediately in a paused `preparing-malecns` phase.
2. No DemoBrain actions are executed or written into the persistent experiment.
3. If the verified graph is absent, the pinned Stonkfly preparation runs in a background thread using `STONKFLY_DATA`.
4. Prepared data is checksum-verified by the upstream package.
5. NeuroFly runs its host preflight.
6. The service instantiates `MaleCNSBrain` and restores the checkpoint if present.
7. Authority atomically switches to `malecns-ready`, then Maze episodes begin.
8. Any preparation failure is surfaced through `/api/status` and the Maze remains paused.

This lets a cloud host satisfy web-service health checks while large first-run data preparation occurs on the runtime persistent disk.

## Render blueprint

The repository includes `render.yaml` as a deployment template:

```yaml
plan: 2c-16g
region: singapore
autoDeployTrigger: off
```

It attaches a single persistent disk at `/var/data`, stores Stonkfly data under `/var/data/stonkfly`, stores NeuroFly checkpoints under `/var/data/neurofly`, and uses `/api/status` as the health check.

The template deliberately disables automatic deploys. Syncing or creating this Blueprint can provision paid Render resources, so service creation remains an explicit user action.

## Validation boundary

V0.4 CI may validate:

- preflight report shape;
- low-memory guard logic;
- deterministic smoke receipt generation with a fake backend;
- cloud bootstrap phase/state contract;
- `render.yaml` safety settings;
- V0.3 Python, site and pinned-Stonkfly import tests.

V0.4 CI still must not claim `FULL_MALECNS_SMOKE_PASS` until a prepared host actually runs `python -m neurofly real-smoke` and produces a valid receipt.
