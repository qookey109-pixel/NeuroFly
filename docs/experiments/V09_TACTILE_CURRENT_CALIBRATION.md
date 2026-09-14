# V0.9 Tactile Current Calibration — Prepared MaleCNS Evidence

Status: **PASS**. This experiment calibrates an engineering current only. Runtime tactile stimulation remains disabled.

## Authority

- GitHub Actions run: `34798246806`
- Job: `103835475196`
- Tested head: `43d139682bdfa97e49f44113b37fa84aa627c885`
- Stonkfly pin: `78ef3e05ab0fa086032098558d893667068944a0`
- MaleCNS: v1.0, 166,700 neurons, 25,582,938 directed edges
- Crosswalk: `neurofly-tactile-leg-functional-crosswalk-v0.2`
- Selected tactile candidates: exactly 590 neurons

## Predeclared sweep

The workflow tested exactly:

`2, 4, 6, 8, 10, 12, 16`

Selection policy:

`lowest_predeclared_current_with_positive_response_in_all_six_exact_types`

The low-current negative results are important evidence:

| Current | Result | Selected-population spikes | Active selected neurons |
| ---: | --- | ---: | ---: |
| 2 | FAIL | 0 | 0 |
| 4 | FAIL | 0 | 0 |
| 6 | FAIL | 0 | 0 |
| 8 | PASS | 1,710 | 590 |
| 10 | PASS | 2,784 | 590 |
| 12 | PASS | 3,921 | 590 |
| 16 | PASS | 6,412 | 590 |

Therefore the selected lowest passing current is **8.0**.

## Selected current = 8.0

Selected receipt SHA-256:

`41592fd805bbfa19f73959af24479d12770e10866ed05e8fc85a86eac198f462`

Matched `contact_off` baseline produced zero spikes in the selected tactile population. At current 8.0, all 590 selected neurons became active and produced 1,710 spikes, for a positive delta of 2.8983050847457625 spikes per neuron.

All six exact type groups independently passed:

| Type | Neurons | Stimulated spikes | Active neurons | Delta spikes/neuron |
| --- | ---: | ---: | ---: | ---: |
| SNta20 | 156 | 486 | 156 | 3.1153846153846154 |
| SNta26 | 31 | 79 | 31 | 2.5483870967741935 |
| SNta27 | 47 | 157 | 47 | 3.3404255319148937 |
| SNta28 | 74 | 198 | 74 | 2.675675675675676 |
| SNta34 | 54 | 191 | 54 | 3.537037037037037 |
| SNta37 | 228 | 599 | 228 | 2.6271929824561404 |

This is stronger than selecting on aggregate population activity alone: no large SNta population was allowed to hide a non-responsive smaller type.

## Reproducibility locks

- Baseline checkpoint SHA-256: `7a35fd223407fdd7e9e319f60864d4524a0668544c1fb006dbcac543cd22a2cd`
- Crosswalk SHA-256: `4cd8a25f2647be6399642a230ee947ce19cf72f5fc22b3e5ad4591eec78ab8cc`
- Selected body-ID SHA-256: `007556a35ccfcbf41fac8b00db1f56cfddbe136a0056ed69a1724224289a6395`
- Plasticity: frozen
- Matched baseline memory: PASS
- Population counts match audit: PASS
- Runtime stimulation enabled: **false**

## Artifact

- Artifact ID: `10330805586`
- Name: `neurofly-tactile-calibration-34798246806-1`
- Size: 19,854 bytes
- Artifact ZIP SHA-256: `ae11e0d018154fe8e65682acd8a1b67536a4514b04f2766da721215da65e2203`

The artifact contains the seven candidate reports, the sweep summary, and the selected calibration report.

## Scientific boundary

This PASS demonstrates only that the engineered MaleCNS runtime responds reproducibly when current 8.0 is applied to the evidence-backed 590-neuron tactile candidate population under the matched frozen simulation setup.

It does **not** establish that 8.0 corresponds to a physical bristle force, natural receptor current, natural firing rate, natural touch localization, six-leg biomechanics, adaptation, laterality, behavioral benefit, or biological validity.

The runtime contact sensor remains an engineering blocked-forward external-touch proxy. No map geometry or collision metadata is authorized as agent input.

## Runtime decision

Calibration PASS is not runtime authorization. `runtime_stimulation_enabled=false` remains a hard boundary. A later stacked runtime-routing stage must explicitly bind the one-shot contact pulse to this frozen calibration and re-run regression / prepared-MaleCNS smoke tests before tactile current may enter normal NeuroFly decisions.
