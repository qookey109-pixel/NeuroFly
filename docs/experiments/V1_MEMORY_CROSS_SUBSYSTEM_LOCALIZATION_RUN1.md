# V1 Memory Cross-Subsystem Localization — Run 1

Status: **COMPLETE / FROZEN**

## Evidence integrity

- run: `36143667740`
- scientific head: `2d6afe8dc50d66fd74b8062d01909568e2eb223e`
- artifact: `10869666593`
- artifact SHA-256: `0b8d18dafccbcb18c4ec19bfaf3e56da1641d87f64690da6c2ae793324d5633e`
- receipt SHA-256: `b548f59b6874413dbfd38e99cbffe783618d99c24d1b23101963e99e7c337465`
- source checkpoint unchanged: `a7ca776823c84a0c633b82dd1e9dc256ef55e197d6bb7d79b2724f219577d26d`

The outcome-blind neural-diversity gate selected four unique histories:

- CS1 / seed 5209 / event 63
- CS2 / seed 5227 / event 92
- CS3 / seed 5231 / event 118
- CS4 / seed 5233 / event 74

All four have unique pre-event checkpoint and stable sensory-sequence digests.

## Cross-pair result

| Condition | KC active | changed-edge L1 | MBON07 state | MBON07 spike | action divergence |
|---|---:|---:|---:|---:|---:|
| intact | 0.328778 | 0.485259 | 1.000000 | 0.202381 | 0.214286 |
| v/g + luminance | 0.325533 | 0.481890 | 1.000000 | 0.273810 | 0.190476 |
| **v/g + refractory/delay** | **0.112447** | **0.165681** | **0.321429** | **0.083333** | **0.083333** |
| adaptation + luminance | 0.343803 | 0.498847 | 1.000000 | 0.250000 | 0.178571 |
| adaptation + refractory/delay | 0.350157 | 0.510752 | 1.000000 | 0.273810 | 0.095238 |
| broad physical clear | 0.148234 | 0.220908 | 0.440476 | 0.130952 | 0.047619 |

Relative to intact, clearing **v/g + refractory/delay** changes:

- changed-KC active fraction: `-0.216331`
- changed-edge L1 engagement: `-0.319578`
- MBON07 state-difference fraction: `-0.678571`
- MBON07 spike-difference fraction: `-0.119048`
- action-divergence fraction: `-0.130952`

It is the only tested cross-pair with the same-direction suppression of the
three primary neural-expression endpoints in **all 4/4 neural-diverse
histories**:

- changed-KC activity
- changed-edge engagement
- MBON07 state expression

The other three cross-pairs remain near intact on these endpoints.

## Important non-monotonicity

This does **not** mean the full broad-clear effect is simply equal to
`v/g + delay`.

In CS2 and CS3, `v/g + refractory/delay` suppresses neural expression more
strongly than the full broad physical clear.

Therefore the intervention system is not safely modeled as a monotonic additive
stack of state clears.

The supported statement is:

**v/g + refractory/delay is the current minimal robust suppressive
cross-subsystem ensemble candidate.**

It is **not** a confirmed unique transient carrier and does not fully explain
the broad-clear phenotype.

## Next clean step

Use a fresh outcome-blind neural-diverse cohort to replicate only:

- intact
- `v/g + refractory/delay`
- full broad clear

If the suppressive pattern reproduces, then decompose `v` versus `g`
within the delay-state background.

## Governance

Still false:

- `learning_validated`
- `temporal_cue_index_confirmed`
- `prefix_sequence_specificity_confirmed`
- `transient_state_carrier_confirmed`
- `memory_expression_causal`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`

No production checkpoint or model parameter was changed.
