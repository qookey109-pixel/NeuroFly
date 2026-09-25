# V1 Reward Memory KC Trace Reconstruction Audit — Run 1

## Status

**EXPLORATORY TRACE RECONSTRUCTION AUDIT COMPLETE**

Successful GitHub Actions run: `36103039412`

- scientific head: `4239a7240fd070854874b1750d28f6410e6adf95`
- artifact id: `10850146795`
- artifact digest: `sha256:590d0fd9eae139a8374c93ec314f02b35428a901fed59dfb83907a5b21c31ecd`
- receipt digest: `fb5538afb4aab6a1f1608e054bf9b5c6852c867945d0e6c198b381b6537be131`
- source checkpoint: `7e4746d08c9bca7d71403fccf0ffb0334a6098720c6fbd7d696a8fd8394ff284`

The production checkpoint was unchanged. All preregistration and evidence gates
passed.

## Core result

All changed reward edges in all four fresh trajectories carried positive
reward-time eligibility in this run.

Comparing the same trajectory after transient-state clearing:

| Metric | 1 tau / 20 decisions | 3 tau / 60 decisions |
| --- | ---: | ---: |
| mean final changed-trace cosine | 0.627708547173 | 0.995035129993 |
| mean final changed-trace L1 overlap | 0.286251777639 | 0.807160125576 |
| mean target-positive edge recovery | 0.450101550306 | 0.904601345329 |

Mean 3 tau minus 1 tau L1-overlap delta was:

`+0.520908347938`

and **4 / 4** replicates had higher final changed-edge L1 overlap with the
60-decision replay.

This directly supports the narrower mechanism that one trace time constant of
history often omits material eligibility context.

It does **not** show that three time constants perfectly reproduce the original
state, nor that the memory is a validated learned behavior.

## Replicates

### TR1 / seed 3001

- reward event index: `76`
- acquisition: `82` decisions
- changed reward edges: `1530`
- target-positive changed edges: `100%`
- 1 tau cosine: `0.525733214405`
- 3 tau cosine: `0.996193916810`
- 1 tau L1 overlap: `0.015917586426`
- 3 tau L1 overlap: `0.920615513138`
- overlap delta: `+0.904697926712`
- target-positive recovery: `0.065359477124 → 0.930718954248`

### TR2 / seed 3011

- reward event index: `105`
- acquisition: `111` decisions
- changed reward edges: `1506`
- target-positive changed edges: `100%`
- 1 tau cosine: `0.992722637623`
- 3 tau cosine: `0.992711638961`
- 1 tau L1 overlap: `0.539424258866`
- 3 tau L1 overlap: `0.554460865446`
- overlap delta: `+0.015036606580`
- target-positive recovery: `0.870517928287 → 0.859893758300`

TR2 is important for interpretation: 3 tau improved L1 overlap and normalized
L1 error only slightly, while cosine was essentially unchanged and lower by
about `1.1e-5`. Therefore the result must not be summarized as three tau being
better on every metric in every trajectory.

### TR3 / seed 3019

- reward event index: `60`
- acquisition: `66` decisions
- changed reward edges: `1528`
- target-positive changed edges: `100%`
- 1 tau cosine: `0.992378336663`
- 3 tau cosine: `0.995144383566`
- 1 tau L1 overlap: `0.589665265263`
- 3 tau L1 overlap: `0.893870988480`
- overlap delta: `+0.304205723217`
- target-positive recovery: `0.864528795812 → 0.924738219895`

### TR4 / seed 3023

- reward event index: `93`
- acquisition: `99` decisions
- changed reward edges: `1506`
- target-positive changed edges: `100%`
- 1 tau cosine: `0`
- 3 tau cosine: `0.996090580637`
- 1 tau L1 overlap: `0`
- 3 tau L1 overlap: `0.859693135242`
- overlap delta: `+0.859693135242`
- target-positive recovery: `0 → 0.903054448871`

TR4 gives the clearest example that replaying only the last 20 decisions can
miss essentially all of the original eligibility state even when the full
60-decision history reconstructs most of it.

## Mechanistic interpretation

The evidence chain can now be sharpened:

`reward-time changed edges`
→ positive prereward KC eligibility
→ 20-decision replay can reconstruct that eligibility poorly or
heterogeneously
→ 60-decision replay substantially restores the original eligibility vector
across all four trajectories by L1 overlap.

The final 3 tau mean L1 overlap of `0.807160125576` is still below 1.0, so
three time constants are not treated as an exact reconstruction or hard
historical cutoff.

This resolves an important ambiguity from temporal-index run 1: the TI2/TI3
lack of changed-KC / MBON07 expression under a 20-step replay cannot be
interpreted cleanly without accounting for older eligibility history.

## Next mechanism study

Do **not** jump directly to behavioral confirmatory.

The next clean exploratory question is whether improved 3 tau eligibility
reconstruction also stabilizes **stored-memory expression** after state
clearing.

Preregister fresh trajectories and compare, on the same trajectory:

1. paired reward-memory versus no-pulse memory branches;
2. state clear with memory preserved;
3. 1 tau versus 3 tau prereward replay;
4. changed-KC engagement;
5. MBON07 state / spike difference;
6. downstream decoder state and action as descriptive endpoints only.

No decoder/gain/pulse/KC-threshold/MBON-weight tuning should occur first.

## Claim state

All remain false:

- `learning_validated`
- `temporal_cue_index_confirmed`
- `cue_indexing_failure_confirmed`
- `memory_expression_causal`
- `replacement_confirmatory_authorized`
- `behavioral_promotion_authorized`
