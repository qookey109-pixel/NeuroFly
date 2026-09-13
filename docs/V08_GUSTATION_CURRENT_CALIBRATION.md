# V0.8 Gustation — prepared MaleCNS current calibration

Status: calibration gate. Normal NeuroFly runtime gustatory stimulation remains disabled.

## Goal

Find the lowest predeclared engineered current that produces a positive frozen-weight response in each evidence-backed gustatory functional population.

The two classes are calibrated independently:

- `bitter`: MaleCNS type `LB1b`, expected 6 retained neurons
- `sugar_water`: MaleCNS types `LB3a`, `LB3b`, `LB3c`, `LB3d`, expected 77 retained neurons

The unresolved 1,345 curator-labelled gustatory neurons are not stimulated.

## Sweep

Predeclared candidate currents:

`6, 8, 10, 12, 16, 20`

Each candidate runs three matched frozen conditions for 200 ms neural time:

1. `contact_off` — no gustatory stimulation
2. `bitter` — direct stimulation of only the six mapped LB1b neurons
3. `sugar_water` — direct stimulation of only the 77 mapped LB3a-d neurons

All conditions start from the same checkpoint state for that candidate and use the same seed, visual frame, fly pose and enemy layout.

## Class gate

A functional class passes a current when:

- its target population has at least one active neuron
- target spikes per neuron are strictly greater than the matched `contact_off` baseline
- mapped population counts still match the audited pinned MaleCNS dataset
- plasticity stays frozen
- memory SHA is unchanged

Decoder action is recorded as telemetry only and is **not** a PASS condition.

## Selection

The workflow chooses the lowest passing current independently for `bitter` and `sugar_water`. The two selected currents may differ.

## Scientific boundary

A calibration PASS establishes only engineered current routing into the exact evidence-backed MaleCNS groups. It does not establish natural taste-receptor physiology, appetitive/aversive valence, feeding preference, reinforcement value or behavioral benefit.

Normal runtime stimulation stays disabled until the selected currents and receipts are reviewed and fixed in a later runtime-routing change.
