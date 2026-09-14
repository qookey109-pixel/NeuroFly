# V0.10 SNpp41 Instance Exception Audit

Status: **REVIEW_REQUIRED** identity receipt; no promotion, current calibration, or stimulation.

## Why this exists

The FeCO hook-pair evidence gate established a reproducible mixed-subclass condition in pinned MaleCNS v1.0:

- 21 `SNpp41` rows are `mechanosensory_proprioceptive / chordotonal organ`;
- 1 `SNpp41` row is `mechanosensory_proprioceptive / leg`.

Type-level sources call `SNpp41` a FeCO hook, but NeuroFly does not discard a row-level annotation conflict just to obtain a clean exact-type population.

## First prepared discovery run

Prepared workflow run `34805000350` intentionally started without a frozen identity and exited red after publishing the exact exception record.

The discovered pinned MaleCNS identity is:

```json
{
  "body_id": "905407",
  "instance": "",
  "type": "SNpp41",
  "class": "mechanosensory_proprioceptive",
  "subclass": "leg",
  "superclass": "vnc_sensory",
  "soma_side": ""
}
```

Structural evidence remained exactly:

- 22 total SNpp41 rows;
- 21 chordotonal-organ rows;
- 1 leg-subclass exception;
- no other unexpected SNpp41 rows.

## Blank metadata is evidence

Body `905407` has no populated `instance` and no populated `somaSide` in the pinned annotations exposed through Stonkfly.

NeuroFly treats those blank values as part of the frozen receipt. It does **not** infer an instance suffix, laterality, or leg identity from neighboring neurons, morphology, body ID, or expected bilateral symmetry.

The audit therefore fails if a future dataset unexpectedly changes either blank field without an explicit evidence review. It also fails if the body ID or taxonomy changes.

## Frozen verification gate

The source now freezes the exact identity above. A green prepared workflow is allowed only when the current pinned dataset reproduces all of these fields exactly, including the blank `instance` and blank `soma_side`.

A successful verification still reports:

- `status=REVIEW_REQUIRED`;
- `promotion_ready=false`;
- `stimulation_enabled=false`;
- `runtime_transduction_enabled=false`;
- `current_calibration_authorized=false`.

It does not convert SNpp41 into a clean exact-type stimulation population.

## Machine gates

The audit requires:

- exact SNpp41 type-row count = 22;
- exact accepted chordotonal count = 21;
- exact leg-exception count = 1;
- exception body ID present;
- type/class/subclass/superclass present;
- frozen body ID = `905407`;
- frozen instance = empty string;
- frozen soma side = empty string;
- exact frozen identity match;
- promotion/current/stimulation remain blocked.

An invented `SNpp41_R`, an inferred `R/L` soma side, another body ID, an extra exception, or a missing exception all fail closed.

## Interpretation boundary

This audit establishes reproducible annotation identity only. It does not determine why body `905407` differs from the other SNpp41 rows.

Possible explanations still include:

- curator annotation drift;
- segmentation/reconstruction ambiguity;
- a legitimate mixed systematic type;
- missing instance/laterality metadata;
- a cross-dataset naming mismatch;
- another biological/annotation issue.

Those possibilities require body-level morphology/connectivity and curator/cross-dataset evidence. The blank instance/somaSide must not be filled speculatively.

## Next evidence gate

The next safe step is a body-level audit of **MaleCNS body 905407**:

1. obtain its current public MaleCNS/VFB/type-resource representation where available;
2. compare its morphology/connectivity with the 21 chordotonal SNpp41 rows and with other leg-subclass sensory neurons;
3. check whether the exception is reproducible across relevant datasets/curator exports;
4. preserve a distinction between annotation evidence and biological interpretation.

Separately, `SNpp39/SNpp41 -> extension/flexion` sensory tuning remains unresolved and must not be inferred from downstream motor effects.

No proprioceptive current should be enabled from this audit alone.
