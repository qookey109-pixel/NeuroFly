# V0.8 Gustation Runtime Smoke

Status: **PASS**

This receipt fixes the prepared-MaleCNS evidence for calibrated one-shot gustation runtime routing while normal ambient airflow remains active.

## Run

- GitHub Actions run: `34768217124`
- Artifact ID: `10321271094`
- Artifact ZIP SHA-256: `c858652d10a99e24fc782e5c0ff14ec4788226d7af7fbde27f9b4174a8bff6be`
- Runtime receipt SHA-256: `cb9a179d4ba731d964e8c3cac56cf3691ae3fda4b7b13956f2c045763489fa29`
- Seed: `109`
- MaleCNS: v1.0 / 166,700 neurons / 25,582,938 directed edges
- Calibration receipt: `595054789f40c1039b8393d32f797db299dad93b4153eecb5547fb9e7fc62610`

## No-contact gate

A strict no-contact gustation payload produced **0 direct gustatory stimulation pulses**.

This confirms that merely having visible/smellable food in the environment does not create taste current.

## Sugar/water contact

Input:

- `contact = true`
- `sugar_water = 1.0`
- `bitter = 0.0`
- calibrated sugar/water current = `8.0`
- target population = exact MaleCNS `LB3a`, `LB3b`, `LB3c`, `LB3d` / 77 neurons

Observed:

- sugar/water GRN spikes: **213**
- bitter GRN spikes: **0**
- ambient JO-C left spikes: **54**
- ambient JO-C right spikes: **0**
- ambient JO-E left spikes: **0**
- ambient JO-E right spikes: **102**
- decoded action: `TURN_RIGHT` — telemetry only, not causal evidence
- memory SHA before: `9f9c000fb9819eb99c214cc1da747d44e13f009bc4c3454f6b7dfe4ee669acf7`
- memory SHA after: `9f9c000fb9819eb99c214cc1da747d44e13f009bc4c3454f6b7dfe4ee669acf7`

## Bitter contact

Input:

- `contact = true`
- `bitter = 1.0`
- `sugar_water = 0.0`
- calibrated bitter current = `8.0`
- target population = exact MaleCNS `LB1b` / 6 neurons

Observed:

- bitter GRN spikes: **107**
- sugar/water GRN spikes: **0**
- ambient JO-C left spikes: **60**
- ambient JO-C right spikes: **0**
- ambient JO-E left spikes: **0**
- ambient JO-E right spikes: **110**
- decoded action: `TURN_RIGHT` — telemetry only, not causal evidence
- memory SHA before: `9f9c000fb9819eb99c214cc1da747d44e13f009bc4c3454f6b7dfe4ee669acf7`
- memory SHA after: `9f9c000fb9819eb99c214cc1da747d44e13f009bc4c3454f6b7dfe4ee669acf7`

## Invariants established

- taste current is absent without physical contact
- sugar/water and bitter route only into their evidence-backed mapped GRN groups
- unresolved gustatory neurons used: `0`
- taste is not reinforcement
- normal calibrated ambient airflow remains active at the same time as taste
- frozen memory SHA remains unchanged
- gustation current remains the pre-calibrated `8.0`

## Scientific boundary

This PASS establishes strict runtime routing into selected MaleCNS gustatory populations and simultaneous ambient mechanosensory activity. It does **not** establish natural receptor physiology, appetitive/aversive valence, feeding preference, navigation benefit, learning benefit, or ecological realism.
