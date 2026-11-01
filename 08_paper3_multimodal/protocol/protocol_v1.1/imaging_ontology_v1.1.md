# Neuroimaging phenotype ontology — v1.1 (candidate set)

**Status:** candidate set. Frozen as the closed vocabulary for extraction
development; the final set is fixed at step 8b of PROTOCOL §15.
**Date:** 11 September 2026. Supersedes `protocol_v1.0/imaging_ontology_v1.0.md`.
**Governing rule:** PROTOCOL_v1.1_EN.md §8.1.

> The final feature set is determined solely on clinical relevance, definitional
> clarity and validated extraction reliability, **without reference to any
> association with the study outcome**. A feature may be removed because it cannot
> be extracted reliably. It may not be removed because it appears unrelated to the
> outcome, and no feature may be added because it appears strongly related to it.

## What changed from v1.0

1. Every phenotype carries an **assertion level**, not a bare binary.
2. Infarct territory becomes **multi-label** with a `multiple_territories` flag,
   rather than a single forced category.
3. Acute infarction and chronic ischaemic change are **two independent
   phenotypes**, not opposite values of one.
4. Midline shift is **binary-primary** with a conditional, never-imputed
   measurement.
5. Every phenotype may carry a **change-over-time** value where the report makes a
   comparison. Change values are stored but are held out of the primary M1
   feature set.

## Source

Head CT and MRI reports in MIMIC-IV-Note v2.2, restricted to parenchymal brain
examinations: exam names matching `CT HEAD*`, `PORTABLE HEAD CT*`, `MR HEAD*`,
`STROKE PROTOCOL (BRAIN*`. Vascular studies — CTA head/neck, MRA brain/neck, MRV
head, carotid imaging — form a separate tier and contribute only to the
large-vessel occlusion phenotype.

Corpus: 20,947 tier-A reports from 4,497 note-era cohort patients
(AIS 9,284 / ICH 8,270 / SAH 3,297 / ICH+SAH 96).

## Assertion scale

Applies to every phenotype below.

| Level | Meaning | Typical wording |
|---|---|---|
| `Present` | the finding is asserted | "there is", "demonstrates", "consistent with" |
| `Absent` | the finding is explicitly excluded | "no evidence of", "without", "negative for" |
| `Uncertain` | hedged, neither asserted nor excluded | "cannot exclude", "possible", "suspicious for", "equivocal" |
| `Not assessable` | this examination cannot demonstrate it | "limited by motion", "non-contrast study", vascular phenotype on a non-vascular study |

`Not assessable` is not `Absent`. The distinction matters most for large-vessel
occlusion: a non-contrast head CT that does not mention LVO has not excluded it.

Negation is scoped to what is negated. "No large territorial infarct" sets the
large-territorial phenotype to `Absent` and says nothing about infarction in
general.

For the primary M1 feature set: `Present` → positive, `Absent` → negative,
`Uncertain` and `Not assessable` → unknown. A pre-specified sensitivity analysis
counts probable/likely as positive.

## Change-over-time scale

Recorded where the report compares with a prior study; otherwise `not stated`.

| Level | Typical wording |
|---|---|
| `new` | "new since", "interval development of" |
| `increased` | "increased", "interval increase", "progression of" |
| `stable` | "unchanged", "stable" |
| `decreased` | "decreased", "interval decrease", "improved" |
| `resolved` | "resolved", "no residual" |
| `not stated` | no comparison made |

A comparison records **both** the current assertion and the change. "IVH increased
from prior" is `Present` + `increased`. "IVH unchanged" is `Present` + `stable`.
"IVH decreased" stays `Present`; only `resolved` or an explicit statement of no
residual makes it `Absent`. Change values are stored and are excluded from the
primary M1 feature set (PROTOCOL §8.1).

## Phenotypes

| # | Phenotype | Value | Notes |
|---|---|---|---|
| 1 | `acute_infarction` | assertion | independent of #12 |
| 2 | `infarct_territory` | **multi-label**: ACA, MCA, PCA, vertebrobasilar/brainstem, cerebellar, watershed, deep/lacunar | several may be present at once |
| 2b | `multiple_territories` | binary | derived from #2 |
| 3 | `large_territorial_infarct` | assertion | operational definition to be fixed at the rule session |
| 4 | `intracranial_haemorrhage` | assertion | |
| 5 | `haemorrhage_location` | multi-label: lobar, deep/basal ganglia, thalamic, brainstem, cerebellar, subarachnoid, subdural, epidural | |
| 6 | `intraventricular_haemorrhage` | assertion | |
| 7 | `cerebral_oedema` | assertion | |
| 8 | `midline_shift_present` | assertion | **primary** representation |
| 8b | `midline_shift_mm` | numeric, conditional | recorded only where stated; **never imputed**; 22.1% of midline-shift sentences carry a value |
| 9 | `hydrocephalus` | assertion | |
| 10 | `mass_effect` | assertion | |
| 11 | `herniation` | assertion | subtype recorded free-text where stated |
| 12 | `chronic_ischaemic_change` | assertion | independent of #1; both may be `Present` |
| 13 | `large_vessel_occlusion` | assertion | `Not assessable` by default on non-vascular studies |

Each phenotype additionally carries a `_change` field on the scale above.

## Findings versus impression

Where the findings section and the impression disagree, a specific, localised
positive description takes precedence over a general summary statement. A blanket
"no acute intracranial process" does not override a specific lesion described in
findings. A direct contradiction that context cannot resolve is recorded as
`Uncertain` and goes to human adjudication.

## Still to be fixed at the rule session

- The operational definition of "large territorial infarct".
- Phenotype-specific lexical exceptions on top of the assertion scale.
- Whether `midline_shift_mm` is used as a continuous secondary variable or
  dichotomised at a threshold, and which threshold.
- Herniation subtypes: free text or a closed list.

## Extraction environment

Local open-weight model on project hardware. Report text is never sent to an
external API or service (PROTOCOL §8.4).
