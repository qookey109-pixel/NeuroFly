# V1 Memory Interaction Diversity Recovery — Run 1

Status: **COMPLETE / FROZEN**

## Evidence integrity

- run: `36121847253`
- scientific head: `534842993208a53a3a99eda003ce917897ad226f`
- artifact: `10857919835`
- artifact SHA-256: `f63bab9f9e93ae148b9d621fe13d5aa11a3a4f1025d1f1235070773f28f2a7e7`
- receipt SHA-256: `281d9fd7fc77752a7cab450c880c26437549e8e77674b6dfcb53c391435d88fd`
- source checkpoint unchanged: `a2972a6234cb60e67f311300d352d8083d6e4ba79be042a77eeaf1c7c11160a0`

The outcome-blind diversity gate selected the first four eligible candidates:
`5003, 5009, 5011, 5021`.

All four have unique pre-event brain checkpoint SHA-256 values and unique
stable sensory-sequence SHA-256 values. Their reward-event indices are
`62, 65, 80, 146`.

This repairs the replicate-collapse problem discovered in #157.

## Scheduler equivalence

The coherent scheduler rebuild is again **exactly identical to intact at every
terminal per-lag endpoint in all 4 neural-diverse histories**.

Scheduler bookkeeping remains excluded as the positive expression carrier.

## A / B / A+B result

A = clear `v/g + adaptation`

B = clear `luminance + refractory + delayed-event queue`

A+B = clear both subsystems.

| Endpoint | Intact | A | B | A+B | Interaction |
|---|---:|---:|---:|---:|---:|
| changed-KC active fraction | 0.338900 | 0.343199 | 0.341945 | 0.088507 | -0.257737 |
| changed-edge L1 engaged | 0.509325 | 0.504667 | 0.510869 | 0.133756 | -0.372455 |
| MBON07 state-difference fraction | 1.000000 | 1.000000 | 1.000000 | 0.261905 | -0.738095 |
| MBON07 spike-difference fraction | 0.250000 | 0.273810 | 0.273810 | 0.047619 | -0.250000 |
| action-divergence fraction | 0.190476 | 0.226190 | 0.190476 | 0.023810 | -0.202381 |

For upstream KC activity, changed-edge engagement and MBON07 state expression,
the interaction contrast is negative in all four independently selected neural
histories.

DR3 is the strongest example: broad clearing removes all terminal changed-KC,
changed-edge, MBON07-state, MBON07-spike and action expression, while neither
single subsystem clear does so.

## Mechanistic conclusion

The Run 1 hypothesis from #157 now **replicates across four genuinely distinct
neural histories**.

The extra-history memory-expression benefit is robust when either physical
subsystem is cleared alone, but strongly reduced when both are removed
together.

The supported description is therefore:

**non-additive joint physical-state dependency, consistent with redundant or
compensatory support across the two subsystems.**

This does not identify a unique carrier and does not establish behavioral
memory causality.

Reward-cue action divergence is not stable enough to open a cue-specific claim.

## Next localization

The next efficient layer is a preregistered cross-subsystem decomposition:

- `v/g + luminance`
- `v/g + refractory/delay`
- `adaptation + luminance`
- `adaptation + refractory/delay`

against intact and full A+B clearing, using the same outcome-blind neural
diversity gate.

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
