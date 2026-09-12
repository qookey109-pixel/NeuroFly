# NeuroFly V0.4 — Full MaleCNS Smoke + Zero-Cost Runner

V0.4 turns the V0.3 integration contract into an operational runbook for the first real 166,700-neuron Maze Chase execution while keeping paid cloud resources out of the default path.

## Goals

1. detect whether a host is suitable before loading the full connectome;
2. run a bounded real-brain smoke test and write a machine-readable receipt;
3. preserve the exact Stonkfly upstream pin and MaleCNS provenance;
4. support free, resumable full-MaleCNS sessions on standard GitHub-hosted runners;
5. keep all paid cloud provisioning out of the repository's default workflow.

## Local preparation

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e '.[test,stonkfly]'

export STONKFLY_DATA="$PWD/.cache/stonkfly"
python -m stonkfly prepare
python -m neurofly host-preflight
```

The preflight reports Python, C++ compiler availability, Stonkfly installation, verified prepared graph status, detected host RAM and free disk.

Stonkfly recommends 16 GB RAM and several GB of storage. NeuroFly keeps a low-memory guard below 12 GiB for `real-smoke` unless explicitly overridden.

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

The receipt is the authority for `FULL_MALECNS_SMOKE_PASS`.

## Free GitHub Actions execution

The repository contains:

```text
.github/workflows/full-malecns-free.yml
```

It uses a standard `ubuntu-latest` runner for this public repository. It does not request GitHub larger runners and does not provision any external paid service.

The workflow is bounded to 330 minutes and performs:

1. restore of the prepared MaleCNS data cache;
2. restore of the latest resumable NeuroFly state cache;
3. installation of the exact pinned Stonkfly revision;
4. MaleCNS preparation / verification;
5. host preflight;
6. one or more real MaleCNS Maze decisions;
7. checkpoint + receipt generation;
8. cache save for prepared MaleCNS data only when below a 9 GB safety ceiling;
9. separate cache save for the latest NeuroFly brain/Maze state;
10. upload of only the small preflight and receipt files as a 1-day evidence artifact.

Separating static MaleCNS data from changing experiment state avoids copying the multi-GB dataset into every new state cache.

## Free-mode continuity model

GitHub-hosted runners are finite jobs, so zero-cost NeuroFly does not pretend that a single OS process remains alive 24/7.

Instead:

```text
latest checkpoint
       |
       v
free 16 GB runner
       |
       v
bounded MaleCNS session
       |
       v
new checkpoint + receipt
       |
       v
runner exits
       |
       +---- next run restores here
```

This preserves learning state across sessions and supports repeated experiments without paid hosting.

## Optional always-on host

If an adequate machine is already available at no additional cost, V0.3's persistent server remains usable:

```bash
python -m neurofly maze-server \
  --brain malecns \
  --host 0.0.0.0 \
  --port 8765 \
  --checkpoint runs/maze-fly-001/brain.npz
```

V0.4 intentionally includes no paid Render Blueprint.

## Validation boundary

Normal CI validates:

- preflight report shape;
- low-memory guard logic;
- deterministic smoke receipt generation with a fake backend;
- V0.3 Python, site and pinned-Stonkfly import tests;
- presence and safety properties of the zero-cost workflow;
- absence of the former paid Render deployment template.

The separate `Free Full MaleCNS Smoke` workflow is the path that may legitimately produce `FULL_MALECNS_SMOKE_PASS`, because it downloads/prepares the actual MaleCNS data and invokes the real backend.
