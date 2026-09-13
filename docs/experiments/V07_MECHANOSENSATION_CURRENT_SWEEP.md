# V0.7 Mechanosensation Current Sweep

Status: **PASS — frozen-weight current-routing calibration only**

This document freezes the first predeclared engineering-current sweep that produced a passing bilateral JO-C/JO-E response under matched frozen-weight MaleCNS conditions.

It does **not** enable mechanosensation in the live NeuroFly curriculum and does **not** establish biologically calibrated antennal current, natural wind tuning, navigation learning, or behavioral benefit.

## Relation to Attempt 1

The first full calibration at current `8.0` failed because all four crosswind response gates remained at zero spikes. That failure is preserved separately in [`V07_MECHANOSENSATION_CALIBRATION_ATTEMPT_1.md`](V07_MECHANOSENSATION_CALIBRATION_ATTEMPT_1.md) and is not overwritten by this sweep.

## Authority

- PR: `#29 — V0.7 antennal mechanosensation — fly-relative JO-C/E wind proxy`
- Branch: `feature/v0.7-antennal-mechanosensation-v1`
- Branch head tested: `761cefa1d812ef743db501452b4ae3817b1e44ce`
- GitHub Actions run: `34765143106`
- Workflow: `NeuroFly Mechanosensation Evidence`
- Artifact: `neurofly-mechanosensation-evidence-34765143106-1`
- Artifact ID: `10320610408`
- Artifact ZIP SHA-256: `0f5479fed9a374edadb8fe763c432bf0ed3c0aea7641a0a56f2c2772a05c24a5`
- Stonkfly pin: `78ef3e05ab0fa086032098558d893667068944a0`
- Prepared release: MaleCNS v1.0
- Retained neurons: `166,700`
- Directed edges: `25,582,938`

## Annotation gate repeated in this run

The evidence run re-verified the exact prepared graph before calibration.

| Family | Total | Left | Right | Unresolved |
| --- | ---: | ---: | ---: | ---: |
| JO-C | 68 | 46 | 22 | 0 |
| JO-E | 267 | 157 | 110 | 0 |

Laterality policy remained `somaSide_then_curated_instance_suffix`. In this release all 335 JO-C/JO-E candidates were lateralized by curated instance suffix; no geometry or body-ID inference was used.

## Predeclared sweep

Currents were fixed before execution:

`8.0, 10.0, 12.0, 16.0`

Selection policy:

> `lowest_predeclared_current_with_all_8_response_gates_pass`

Every current was tested with the same five conditions:

1. airflow off
2. headwind
3. tailwind
4. right crosswind
5. left crosswind

Each condition restored the same baseline checkpoint, used `learning=False`, kept weights frozen, ran for `200 ms`, and required memory SHA stability.

## Sweep result

| Current | Gates passed | Overall | Receipt SHA-256 |
| ---: | ---: | --- | --- |
| 8.0 | 4 / 8 | FAIL | `c20a258d9918fe516cc957b21a9364741e570434aee9105998fbbea5ebd208f7` |
| **10.0** | **8 / 8** | **PASS — selected** | `b3a84b5c46e97a461d4dea0673a7db216f1c810486a8d7044020c7d4d85b52cd` |
| 12.0 | 8 / 8 | PASS | `daf106bf47ca5876eb57037501d2308f8d6495e57a159df5d40494f833c7d1c5` |
| 16.0 | 8 / 8 | PASS | `7ea9a8f4ec700dc69afd2e83539ac30f6d1e18b3ac75320f30287e8459b2db5e` |

Selected engineering current: **10.0**.

## Selected-current neural response

At current `10.0`, all eight predeclared gates passed.

| Condition | Target population | Stimulated spikes / neuron | Comparison | Result |
| --- | --- | ---: | --- | --- |
| headwind | JO-E left | 3.1720 | baseline 0.0 | PASS |
| headwind | JO-E right | 4.7182 | baseline 0.0 | PASS |
| tailwind | JO-C left | 6.8261 | baseline 0.0 | PASS |
| tailwind | JO-C right | 7.0000 | baseline 0.0 | PASS |
| right crosswind | JO-C left | 1.0870 | JO-C right 0.0 | PASS |
| right crosswind | JO-E right | 0.8364 | JO-E left 0.0 | PASS |
| left crosswind | JO-C right | 0.6818 | JO-C left 0.0 | PASS |
| left crosswind | JO-E left | 1.4650 | JO-E right 0.0 | PASS |

The previous `8.0` failure is informative: with the v0.1 crosswind gain of `0.70`, the targeted crosswind current was `5.6`, which remained subthreshold in the matched calibration state. At selected current `10.0`, the corresponding crosswind channel receives `7.0` and becomes measurably active and side-selective in this engineering model.

## What this PASS means

This PASS supports the narrower statement:

> The current NeuroFly airflow-to-JO-C/JO-E adapter can route the five predeclared engineered airflow conditions into distinguishable bilateral activity in the pinned MaleCNS runtime at an engineering current of 10.0, under frozen weights and matched initial state.

It does **not** support stronger claims that:

- `10.0` is a biological antennal current;
- the simplified airflow/deflection transform is validated Drosophila biomechanics;
- all JO-C/JO-E subtypes share the assumed tuning;
- MaleCNS has learned wind navigation;
- adding this signal improves behavior;
- mechanosensation should now be enabled in the production curriculum.

## Next gate

The next implementation step is a **separate opt-in runtime integration** with default current `0.0` / disabled. It may consume only the strict `agent_input.antennal_mechanosensation` JO-C/JO-E channels, never world airflow or diagnostics.

After that, a controlled wind-on vs wind-off behavioral experiment with fixed seeds and held-out evaluation is required before considering any live-curriculum enablement.
