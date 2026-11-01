# Paper 3 — protocol v1.0

**Frozen 11 September 2026.**

Study: *Dynamic Risk Stratification for Short-Term Deterioration After Acute
Stroke: Incremental Value of Neuroimaging Beyond Dynamic ICU States* (MIMIC-IV
v3.1).

Frozen **before** M0+A, M1-D and M1-I were fitted. M0-state and M0-full were
already fitted when this version was frozen; their results are recorded in
PROTOCOL §9.1 and are marked provisional, and they play no part in defining the
confirmatory comparison.

## Files

| File | Role |
|---|---|
| `PROTOCOL_v1.0_EN.md` | **Normative.** Protocol and statistical analysis plan. |
| `Dynamic_risk_stratification_research_protocol_v1.0.docx` | English Word version, generated from `PROTOCOL_v1.0_EN.md`. Regenerate rather than edit in place. |
| `PROTOCOL_v1.0_CN.md` | Chinese translation. No independent content. |
| `急性卒中ICU动态风险分层_研究方案_v1.0_中文版.docx` | Chinese Word version, generated from `PROTOCOL_v1.0_CN.md`. Regenerate rather than edit in place. |
| `CONFIRMATION_LOG.md` | Post-freeze events that resolve open items without changing any specification. |
| `imaging_ontology_v1.0.md` | Candidate imaging feature set and the freeze rule. |
| `radiology_annotation_guideline_v1.0.md` | **Skeleton only.** Sampling and reporting rules are frozen; per-feature annotation rules are not yet written and must be completed before annotation begins. |

Endpoint, landmark and model-comparison definitions live inside the protocol
(§4, §6, §9, §10) rather than in separate files, so that a single normative
statement of each cannot drift against a copy.

## The confirmatory comparison

One, and only one (§10.1):

> **M1-D versus M0+A**, temporal validation cohort 2017–2019, pooled across all
> eight landmarks (6–48 h), ranking within each landmark, top 10% of predicted
> risk, difference in 24-hour event capture rate, patient-level clustered
> bootstrap 95% CI.

Interpretation runs on two axes (§10.2, §10.3): whether the interval excludes
zero, and where the point estimate falls against the pre-specified +5 percentage
point interpretability benchmark. A negative primary result may not be replaced
by AUROC, another risk stratum, or a single favourable landmark.

## Open item at freeze — RESOLVED 11 Sep 2026

The adverse-state definition (§6.2) was frozen provisionally as **tf_state 0**, the
respiratory-support analogue, pending confirmation by the supervising
investigators. It was **confirmed as tf_state 0 on 11 September 2026**; see
`CONFIRMATION_LOG.md`. No specification changed, no script was re-run, and the
provisional marking on the M0-state and M0-full results is lifted.

The protocol text itself is deliberately not edited: it records what was true at
the freeze.

## Amendments

Amendments create `protocol_v1.1/`. This directory is never overwritten. Each
amendment records what changed, why, and whether the change was made **before or
after** the relevant result was observed.

Model performance is not a ground for amendment.

## Analysis code

`08_paper3_multimodal/`

| Script | Produces |
|---|---|
| `31_decode_treatment_free_all.py` | treatment-free states for all 6,368 stays, with a reproduction check against the published train labels |
| `32_tf_endpoint_event_counts.py` | incident-transition event supply by landmark |
| `33_landmark_feasibility_table.py` | modality availability within each landmark's risk set |
| `34_filtered_state_decoding.py` | filtered predictor-side state posteriors |
| `35_build_landmark_dataset.py` | `landmark_dataset.csv`, one row per patient × landmark |
| `36_m0_baseline_models.py` | M0-state and M0-full, provisional |
