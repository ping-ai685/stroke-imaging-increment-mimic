# Neuroimaging feature ontology — v1.0 (candidate set)

**Status:** candidate set, frozen as the closed vocabulary for extraction development.
**Date:** 11 September 2026.
**Governing rule:** PROTOCOL_v1.0_EN.md §8.1.

> The final feature set is determined solely on clinical relevance, definitional
> clarity and validated extraction reliability, **without reference to any
> association with the study outcome**. A feature may be removed because it cannot
> be extracted reliably. It may not be removed because it appears unrelated to the
> outcome, and no feature may be added because it appears strongly related to it.

## Source

Head CT and MRI reports in MIMIC-IV-Note v2.2, restricted to parenchymal brain
examinations. The exam-name filter used to identify them (tier A of the linkage
analysis) matches `CT HEAD*`, `PORTABLE HEAD CT*`, `MR HEAD*` and
`STROKE PROTOCOL (BRAIN*`. Vascular studies — CTA head/neck, MRA brain/neck, MRV
head, carotid imaging — form a separate tier and contribute only the large-vessel
occlusion feature below.

## Candidate features

| # | Feature | Type | Notes |
|---|---|---|---|
| 1 | Cerebral infarction present | binary | acute/subacute; chronic change recorded separately |
| 2 | Infarct territory | categorical | ACA / MCA / PCA / vertebrobasilar / watershed / multiple |
| 3 | Large territorial infarction | binary | definition to be fixed in the annotation guideline |
| 4 | Intracranial haemorrhage present | binary | |
| 5 | Haemorrhage location | categorical | lobar / deep / brainstem / cerebellar / subarachnoid / subdural |
| 6 | Intraventricular haemorrhage | binary | low frequency; enriched validation |
| 7 | Cerebral oedema | binary | low frequency; enriched validation |
| 8 | Midline shift | binary + mm where stated | low frequency; enriched validation |
| 9 | Hydrocephalus | binary | low frequency; enriched validation |
| 10 | Mass effect | binary | low frequency; enriched validation |
| 11 | Herniation | binary | low frequency; enriched validation |
| 12 | Chronic ischaemic change / old infarct | binary | distinguishes background from acute injury |
| 13 | Large-vessel occlusion | binary | vascular-tier reports only; recorded as not assessable when no vascular study is available |

## Open items to be settled in the annotation guideline, before extraction

- Negation and uncertainty handling ("no evidence of", "cannot exclude",
  "possible", "unchanged from prior").
- Comparison statements referring to a prior study ("increased midline shift"):
  whether the feature is recorded as present, as a change, or both.
- Whether midline shift is used as a binary, as millimetres, or as a threshold,
  and what threshold.
- Static versus evolving findings, which determines the landmark update rule at
  PROTOCOL §8.2.
- Which findings are recorded as "not assessable" rather than absent when the
  examination cannot demonstrate them (for example LVO on non-contrast CT).

## Extraction

Extraction runs on a **local open-weight model** on project hardware. MIMIC text
must not be sent to any external LLM API; that would violate the data use
agreement. Only the cohort's own reports are processed, not the full 2.3 million.
