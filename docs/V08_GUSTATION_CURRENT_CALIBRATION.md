# V0.8 Gustation — prepared MaleCNS current calibration

Status: **PASS**. Normal NeuroFly runtime gustatory stimulation remains disabled in this PR.

## Goal

Find the lowest predeclared engineered current that produces a positive frozen-weight response in each evidence-backed gustatory functional population.

The two classes were calibrated independently:

- `bitter`: MaleCNS type `LB1b`, 6 retained neurons
- `sugar_water`: MaleCNS types `LB3a`, `LB3b`, `LB3c`, `LB3d`, 77 retained neurons

The unresolved 1,345 curator-labelled gustatory neurons were not stimulated.

## Sweep

Predeclared candidate currents:

`6, 8, 10, 12, 16, 20`

Each candidate ran three matched frozen conditions for 200 ms neural time:

1. `contact_off` — no gustatory stimulation
2. `bitter` — direct stimulation of only the six mapped LB1b neurons
3. `sugar_water` — direct stimulation of only the 77 mapped LB3a-d neurons

All conditions used seed 109 and matched visual/environment state. Plasticity was frozen and matched baseline memory was required.

## Result

The first candidate, current `6.0`, produced zero target spikes in both functional classes and failed both response gates.

Current `8.0` was the first predeclared candidate to pass both independently evaluated class gates:

- bitter / LB1b: baseline 0 spikes → 107 stimulated spikes; 6/6 mapped neurons active; 17.8333 spikes/neuron
- sugar_water / LB3a-d: baseline 0 spikes → 195 stimulated spikes; 77/77 mapped neurons active; 2.53247 spikes/neuron

Higher currents also passed and produced larger responses, but were not selected because the predeclared rule chooses the lowest passing current.

Selected engineered currents:

- `bitter_current = 8.0`
- `sugar_water_current = 8.0`

Selected calibration receipt SHA-256:

`595054789f40c1039b8393d32f797db299dad93b4153eecb5547fb9e7fc62610`

Matched baseline checkpoint SHA-256:

`7a35fd223407fdd7e9e319f60864d4524a0668544c1fb006dbcac543cd22a2cd`

Functional crosswalk SHA-256:

`e3232acc0a8148f3ebf06d86fa176a8a37285c16f9d5d8901baf64248a4ddc61`

## Workflow evidence

GitHub Actions run: `34767612210`

Artifact ID: `10321083455`

Artifact ZIP SHA-256:

`64c22f4a4ef6f7a0aed7afa4df7d774b374f980ea9cd1d46d3ec24926d7e2e02`

The permanent machine-readable evidence is stored in:

`data/gustation_current_calibration_v1.json`

## Class gate

A functional class passed a current only when:

- its target population had at least one active neuron
- target spikes per neuron were strictly greater than the matched `contact_off` baseline
- mapped population counts still matched the audited pinned MaleCNS dataset
- plasticity stayed frozen
- memory SHA was unchanged

Decoder action was telemetry only and was **not** a PASS condition.

## Scientific boundary

This PASS establishes engineered current routing into the exact evidence-backed MaleCNS groups under the matched frozen calibration. It does not establish natural taste-receptor physiology, appetitive/aversive valence, feeding preference, reinforcement value or behavioral benefit.

The next gate may use the selected current `8.0` for strict contact-only runtime routing, while taste remains separate from reward/reinforcement and while unresolved gustatory neurons remain unused.
