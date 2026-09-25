# V1 Memory v/g + Delay Replication — Run 1

Status: **COMPLETE / FROZEN — PARTIAL REPLICATION**

## Evidence integrity

- run: `36148793925`
- scientific head: `ff539e38c0f38955f4d128712cec594f34af8d69`
- artifact: `10871256365`
- artifact SHA-256: `80c6501f91ae768a540d31de0c20ddc5ea31970b12c00a9db2e3d69cf6bc769b`
- receipt SHA-256: `bbdc1132f72ee59577859ffd56bd73fc66db447476f21664a96e6c67af95a40e`
- source checkpoint unchanged: `4530cb286a2dcaf8a3cc938cc70453983c868065f945b1ad0b77306ff2779a71`

The outcome-blind gate selected four unique neural histories:

- VR1 / seed 5407 / event 63
- VR2 / seed 5413 / event 90
- VR3 / seed 5417 / event 62
- VR4 / seed 5419 / event 69

All have unique pre-event checkpoint and stable sensory-sequence digests.

## Aggregate result

| Condition | KC active | changed-edge L1 | MBON07 state | MBON07 spike | action divergence |
|---|---:|---:|---:|---:|---:|
| intact | 0.218218 | 0.324843 | 0.654762 | 0.190476 | 0.059524 |
| v/g + refractory/delay clear | 0.077491 | 0.117592 | 0.238095 | 0.035714 | 0.035714 |
| broad clear | 0.108516 | 0.164621 | 0.333333 | 0.035714 | 0.035714 |

Aggregate `v/g + delay` minus intact:

- changed-KC active fraction: `-0.140727`
- changed-edge L1 engagement: `-0.207251`
- MBON07 state-difference fraction: `-0.416667`
- MBON07 spike-difference fraction: `-0.154762`

So the aggregate suppression from #159 is present again.

## Preregistered history-level replication

The preregistered descriptive target was stricter:

> `v/g + delay` must be lower than intact on all three primary neural
> endpoints in each of the four selected histories.

Observed:

- VR1: PASS
- VR2: PASS
- VR3: PASS
- **VR4: FAIL / reversed**

Therefore:

**preregistered history-level replication = 3/4, not 4/4.**

VR4 reverses direction on all three primary endpoints:

- KC active: `0.158045 → 0.239776`
- changed-edge L1: `0.243136 → 0.365989`
- MBON07 state fraction: `0.476190 → 0.761905`

## Mechanistic conclusion

The data do **not** support treating `v/g + refractory/delay` as a
history-general robust suppressive ensemble.

The supported statement is narrower:

**v/g + refractory/delay has a strong aggregate suppressive effect, but its
effect is strongly history dependent and can reverse direction in a distinct
neural history.**

This means the next step should **not** be `v` versus `g` decomposition.

Instead, the next clean layer is an explicitly exploratory moderator audit
using only pre-intervention / trajectory features from the neural-diverse
histories already collected, asking what distinguishes suppression from
reversal. Any resulting moderator hypothesis must then be frozen and tested
in a new outcome-blind cohort.

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
