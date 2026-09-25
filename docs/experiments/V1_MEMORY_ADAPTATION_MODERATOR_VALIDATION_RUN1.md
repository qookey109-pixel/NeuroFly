# V1 Adaptation Moderator Validation — Run 1

Status: **COMPLETE / FROZEN**

## Evidence integrity

- run: `36157686990`
- scientific head: `01c50082361786f2b1393a90adefdf4de1694c01`
- artifact: `10875926632`
- artifact SHA-256: `c80eba385f72c0897011759f05593bcda2bf233763e9bb6902bcaef20b32955e`
- receipt SHA-256: `cb21d9243f6ca311808b5e8403a016dc545567201606bdd0e39ecbb61030cd2c`
- source checkpoint unchanged: `bcb022cab328827de69b25a5b64fc6065dcf53b9a8143420e883f4117f556979`

All config and evidence gates passed.

## Frozen predictor

`adaptation.paired_mean.std`

Discovery-derived bands were frozen before this cohort's effect outcomes:

- engaged: `>= 0.50`
- quiescent: `<= 0.10`

The workflow collected exactly four unique histories in each stratum before
evaluating the terminal intervention effect.

## Validation result

### Engaged

- suppression: **4/4**
- reversal: 0/4
- mixed: 0/4

Mean `clear_vg_delay - intact`:

- changed-KC active fraction: `-0.281232`
- changed-edge L1 engagement: `-0.419543`
- MBON07 state-difference fraction: `-0.821429`

### Quiescent

- suppression: **0/4**
- reversal: **3/4**
- mixed: **1/4**

Mean `clear_vg_delay - intact`:

- changed-KC active fraction: `+0.125773`
- changed-edge L1 engagement: `+0.190511`
- MBON07 state-difference fraction: `+0.392857`

## Preregistered targets

Primary:

**engaged suppression count > quiescent suppression count**

Result: **PASS**

Secondary:

**engaged mean candidate-minus-intact delta is more negative than quiescent on
all three primary neural endpoints**

Result: **PASS**

Therefore the supported statement is:

**adaptation moderator replication supported.**

This does not set `moderator_confirmed=true`.

## Correlated prefix crosscheck

- engaged: lag -21 changed-KC + changed-edge jointly nonzero **4/4**
- quiescent: jointly nonzero **0/4**

Thus adaptation engagement and immediate prefix expression remain perfectly
aligned in this small stratified cohort. The study does not establish which is
causally upstream.

## Scientific boundary

Supported:

- stored synaptic memory can be expressed differently depending on transient
  physical state;
- the `v/g + refractory/delay` intervention is strongly history dependent;
- boundary adaptation engagement is a replicated predictor of the sign of that
  intervention effect in the tested assay.

Not supported:

- adaptation is a unique transient carrier;
- adaptation is a confirmed causal moderator;
- immediate prefix expression is independently causal;
- memory-expression causality is established;
- behavioral promotion is justified.

## Closure decision

The current **memory-expression mechanism localization line closes here**.

No further field-splitting or moderator mining is warranted under the current
exploratory scope.

If this line is reopened later, the next study must be separately authorized
and should directly disambiguate **adaptation state vs correlated immediate
prefix expression** under a new preregistered causal intervention design.

All scientific governance locks remain false.
