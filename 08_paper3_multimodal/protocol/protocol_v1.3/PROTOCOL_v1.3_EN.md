---
title: "Dynamic Risk Stratification for Short-Term Deterioration After Acute Stroke"
subtitle: "Incremental Value of Neuroimaging Beyond Dynamic ICU States — Research Protocol and Statistical Analysis Plan, MIMIC-IV v3.1"
---

# Dynamic Risk Stratification for Short-Term Deterioration After Acute Stroke

## Incremental Value of Neuroimaging Beyond Dynamic ICU States

**Research Protocol and Statistical Analysis Plan — MIMIC-IV v3.1**

| Field | Specification |
|---|---|
| Protocol version | **1.3** (supersedes v1.2; v1.0, v1.1 and v1.2 remain archived and unedited) |
| Protocol date | 1 October 2026 (v1.2: 11 September 2026) |
| Status | v1.2 was a prospective analysis plan, frozen before any validation annotation, before the extractor was frozen, and before M1-D and M1-I were fitted; every section of it is carried into v1.3 unchanged. v1.3 adds one analysis, C1 (Appendix C), **after the confirmatory result was observed** (16 September 2026) and after the manuscript body was locked (18 September 2026). C1 was frozen before the second extractor was installed and before it processed any report. |
| Normative language | English. The Chinese version is a faithful translation with matching section numbers and carries no independent content. |
| Preceding studies | Paper 1, dynamic clinical states in the first 72 h after acute stroke (MIMIC-IV v3.1; submitted to *Neurocritical Care*, 23 Aug 2026). Paper 2, external validation in eICU-CRD (submitted to *JAMIA*; preprint doi:10.64898/2026.09.07.26362407). |
| Data source | MIMIC-IV v3.1 (hosp, icu), MIMIC-IV-Note v2.2, MIMIC-IV-ECG v1.0, MIMIC-IV-Echo v1.0.1, MIMIC-IV-ED v2.2 |
| Primary analysis unit | One eligible patient-landmark |
| Confirmatory comparison | Exactly one (§10.1). Everything else is secondary or hypothesis-generating. |

> **Protocol principle.** Everything to the left of a landmark determines eligibility and predictors. Everything to the right determines the outcome only. No exception is made anywhere in this protocol, including for the construction of the risk set.

**What changed in v1.3.** One addition, C1, made on 1 October 2026 **after** the confirmatory result of §10.1 was observed: a post-lock robustness analysis that repeats the confirmatory comparison with imaging features extracted by a second, larger language model (Appendix C). No existing specification is changed: the confirmatory comparison (§10.1), the conclusion rule (§10.2), the benchmark (§10.3), the frozen extractor and the primary imaging feature set stand exactly as in v1.2, and the result obtained with the frozen extractor remains the primary result. §14 is updated to name v1.3 and to state how C1 relates to the amendment policy.

**What changed in v1.2.** Nine amendments, B1–B9, all made on 11 September 2026 before any validation annotation, before the extractor is frozen and before any imaging-content result; the full log is Appendix B. B1–B2: the study lead is the primary annotator, and the dual read is deferred until a second credentialed reader exists (§11). B3: an implementation error in imaging availability is corrected (§8.2, §8.3, §9.1). B4: the extraction run and the validation sample are restricted to the analysis population (§11, §15). B5: a rule for findings the report never mentions (§8.1). B6: how the extractor is fixed and recorded (§8.4). B7: an open question on ECG and echocardiography availability (§12). B8: ontology and annotation guideline v1.2 (§8.1). B9: a pre-specified extraction acceptance threshold (§8.1, §11). §14 is also corrected; it still named v1.0.

**What changed in v1.1.** Four amendments, A–D, all made **before any imaging result was observed**; the full log is Appendix A. A: the data-handling boundary is written into the protocol as §8.4. B: the positive-enriched validation set becomes conditional on the random set rather than pre-assigned to named findings. C: the assertion framework, the representation of midline shift, and the treatment of change-over-time statements are specified at §8.1. D: §15 is refined into the measurement chain that must run before M1.

**Resolved since v1.0.** The adverse-state definition (§6.2) was confirmed as tf_state 0 on 11 September 2026 by the supervising investigators, with no change to the definition and no script re-run. See `protocol_v1.0/CONFIRMATION_LOG.md`. The M0-state, M0-full and M0+A results are final, not provisional.

---

# 1. Background and rationale

Patients admitted to intensive care after acute stroke do not occupy a fixed clinical state. Paper 1 divided the first 72 hours of ICU care into consecutive 6-hour windows and used a hidden Markov model over 21 routinely collected variables to identify four time-varying clinical states; a substantial proportion of patients changed state at least once, and transitions ran in both directions rather than along a severity gradient. Paper 2 froze that model and applied it to eICU-CRD, showing that the representation transports across health systems with reasonable fidelity and that the current state carries information about the following 6–24 hours.

Those two studies establish what states exist and whether they travel. They leave one clinically obvious gap. The pathological process that brings these patients to the ICU is in the brain, but the state representation is built almost entirely from systemic physiology: the whole neurological axis is carried by two Glasgow Coma Scale subscores, eye and motor. Infarct extent, haemorrhage volume and location, intraventricular extension, oedema, midline shift, hydrocephalus, mass effect and large-vessel occlusion are not represented at all — although clinicians have already obtained exactly this information by CT or MRI and recorded it in the radiology report.

The question of this study is therefore not whether imaging predicts stroke outcome, which has been addressed before and with weak baselines. It is whether imaging adds anything once a strong, prospectively computed dynamic baseline is already in hand, and whether any gain comes from the imaging findings themselves or from the clinician's decision to order the scan.

## 1.1 Relation to existing literature

Four published studies sit close to this work and shape its positioning. A MIMIC-III study extracted essentially the same head-CT phenotype list by rule-based NLP and added it to structured data for in-hospital mortality, improving AUC from 0.558 to 0.616 at a single admission time point. A 2026 single-centre study combined admission structured variables with radiology report text in 426 patients with acute ischaemic stroke to predict NIHSS-defined early neurological deterioration (test AUC 0.771). A 2025 MIMIC-IV study predicted PaO2-defined respiratory failure in 3,462 ischaemic stroke ICU patients from 24-hour structured data (43 events). The ICYM2I framework formalises the estimation bias that arises when a modality is not missing at random and proposes an inverse-probability correction.

Two consequences follow and are binding on this protocol. First, neither the imaging feature list nor the observation that modality availability is informative may be presented as novel; the latter is cited and applied, not claimed. Second, every one of these studies predicts from a single time point against a weak baseline (demographics, ICD codes, admission laboratory values). The distinguishing features of the present study are the strength of the baseline, the prospectively compatible state inference, and the repeated-landmark design.

# 2. Objectives

## 2.1 Primary objective

To determine whether neuroimaging information, when connected to a repeated-landmark risk-stratification system, improves the concentration of future 24-hour deterioration or death into the highest-risk patients, beyond a baseline that already contains the filtered dynamic state, contemporaneous structured ICU physiology, and knowledge of whether imaging was obtained.

## 2.2 Secondary objectives

1. To quantify how much of the routine ICU signal the four-state dynamic representation has already absorbed (M0-state versus M0-full).
2. To quantify the predictive information carried by the act of obtaining neuroimaging, separately from its content (M0+A versus M0-full).
3. To estimate the information content of the imaging findings themselves among patients in whom imaging was obtained, corrected for the selection mechanism (M1-I).
4. To determine whether the change in predicted risk between consecutive landmarks carries information beyond the current risk level.

## 2.3 Exploratory objectives

Incremental value of ECG and of echocardiography; differences across stroke subtype; and whether the availability of imaging content clarifies the weakly reproducible neurological-impairment/low-support state identified in Paper 2.

# 3. Study positioning

This is a study of **dynamic clinical risk stratification**, not of individual treatment decision support.

The model produces an individual predicted probability for every patient-landmark; the granularity of the output is individual. What the present evidence is intended to support, however, is the ranking of patients and the identification of a group in which short-term risk is concentrated — not a decision about intubation, surgery, vasoactive therapy or any other intervention in a specific patient. The intended uses are increased surveillance, earlier repeat neurological assessment, review of recent physiological trends, reconsideration of the need for repeat imaging, and the allocation of finite clinical attention.

This distinction is to be stated in the abstract, not only in the limitations.

# 4. Design

Retrospective longitudinal prediction study in MIMIC-IV v3.1, using the stroke ICU cohort and the 6-hour window framework established in Paper 1, under a **repeated-landmark prediction design**.

## 4.1 Time convention

Window *w* covers the interval [6w, 6w+6) hours from ICU admission, for *w* = 0…11, spanning the first 72 hours. A landmark sits at the **end** of window *L*, that is at 6(L+1) hours. The outcome interval for a landmark at time *T* is [*T*, *T*+24), which corresponds to windows *L*+1 … *L*+4 and requires *L* ≤ 7.

The protocol states landmarks as **landmark time → subsequent interval**, never as a list of window boundaries. For example: *the 24-hour landmark → outcome observed during 24–48 hours*; *the 48-hour landmark → outcome observed during 48–72 hours*.

## 4.2 Landmarks

Eight landmarks enter the primary repeated-landmark analysis: **6, 12, 18, 24, 30, 36, 42 and 48 hours**.

The 24-hour landmark is designated the **primary clinical presentation point**. It has the clearest clinical reading — an end-of-day-1 reassessment — and imaging availability there is materially higher than at the earliest landmarks. It is reported separately and in full, but it does not carry the confirmatory test (§10.1).

The 6-hour landmark is retained in the pooled analysis. Because imaging availability is low at that point (§8.3), its imaging-specific results are interpreted separately, and a pre-specified sensitivity analysis repeats the pooled analysis with it excluded.

# 5. Population

The base cohort is the MIMIC-IV v3.1 acute stroke ICU cohort of Paper 1 (n = 6,368): acute ischaemic stroke, intracerebral haemorrhage and subarachnoid haemorrhage, first ICU stay of the qualifying admission, traumatic intracranial haemorrhage excluded.

## 5.1 Note-era restriction

MIMIC-IV-Note covers admissions to 2019. Patients in the 2020–2022 anchor-year group have no radiology reports at all, against 92–95% coverage in each earlier group. The multimodal analysis is therefore restricted to the **2008–2019 era**. This is a database coverage boundary, not a severity-based selection, and is to be described as such.

## 5.2 Analysis population

| | Patients | Patient-landmarks | Composite events | Event rate |
|---|---|---|---|---|
| Note-era analysis cohort | 4,854 | 31,092 | — | 9.3% |
| Development, 2008–2016 | 3,530 | 22,134 | 2,214 | 10.0% |
| Temporal validation, 2017–2019 | 1,324 | 8,958 | 671 | 7.5% |

989 unique patients experience at least one composite event. Patients already in the adverse state at every candidate landmark never enter a risk set and are therefore not part of the landmark analysis population.

The development/validation split is fixed by the era boundary and by this protocol. The temporal validation cohort is used only for final locked evaluation; no variable selection, model selection or hyperparameter tuning may be informed by it. This is **temporal validation**, not external validation, and must be named as such throughout (§13).

# 6. States and outcome

## 6.1 Filtered state reconstruction

Papers 1 and 2 decoded states with a whole-sequence pass, which is appropriate for retrospective description of the clinical course. It is not admissible in a prediction study: the state assigned to window *L* is smoothed using windows after *L*.

This study therefore recomputes the **filtered state posterior**

  P(S_L = k | Y_0, …, Y_L)

from a single forward pass, using only observations up to and including the landmark. Filtered decoding is complete for all 6,368 stays and 61,718 windows. Overall agreement with the whole-sequence labels is 98.1%; disagreement is highest at the earliest window (2.7%) and falls to 0.1% at the final window, which is the expected behaviour since filtering and smoothing must coincide once no future remains. The state distribution is essentially unchanged, so the descriptive conclusions of Papers 1 and 2 are unaffected.

All predictor-side state information and all risk-set eligibility in this study use filtered inference.

## 6.2 Adverse state

The adverse physiological state is defined using the **treatment-free** state representation established as a sensitivity analysis in Paper 1, in which states are identified from 17 continuous physiological and neurological variables without mechanical ventilation, CRRT, vasopressors or sedation. The purpose is to avoid defining patient deterioration as a treatment decision made by a clinician.

The adverse state is **tf_state 0**, the respiratory-support analogue (16.1% of windows), confirmed by the supervising investigators on 11 September 2026. Its definition is physiological — GCS eye 1, motor 4 — while 71.4% of its windows happen to carry mechanical ventilation; that co-occurrence is evidence to be reported, not part of the definition.

## 6.3 Risk set

At each landmark the at-risk population comprises patients classified as being outside the adverse physiological state using **filtered** state probabilities based exclusively on observations available up to that landmark.

Using the whole-sequence state to decide who may enter the risk set would allow future windows to determine whom the model is permitted to predict for, which is future-informed selection even though those windows never enter the model. Over landmarks in the note era the two definitions disagree for approximately 0.7% of landmarks and the risk sets overlap by more than 99%, so nothing is lost by taking the defensible option.

A pre-specified sensitivity analysis excludes discordant landmarks — those at which the filtered state is non-adverse but the retrospective whole-sequence state is adverse.

## 6.4 Primary operational outcome

For each eligible patient-landmark with landmark time *T*:

**Event = 1** if, during [*T*, *T*+24), the patient has an incident transition into the adverse physiological state, or dies before such a transition occurs.

**Event = 0** if, during [*T*, *T*+24), no transition into the adverse state occurs and the patient survives to the end of the interval; or the patient leaves the ICU alive without having entered the adverse state.

This binary composite label is the basis of all risk ranking, event capture, PPV, lift, discrimination and calibration analyses.

## 6.5 Competing-risk secondary outcome

Physiological deterioration and death are distinct clinical processes. A secondary cause-specific analysis therefore takes incident adverse transition as the event of interest and death before transition as a competing event. This analysis serves interpretation of the disease course; it does not replace the composite label for risk stratification.

# 7. Predictors

## 7.1 State representation

Models use the full filtered posterior rather than a hard state label, since a patient at 0.99/0.01/0/0 and a patient at 0.42/0.38/0.15/0.05 are not the same patient even though both are assigned the same state. The four probabilities sum to one, so three independent components are entered, expressed as log-ratios against the preserved/low-support state as reference.

State entropy H = −Σ p_k log p_k is a pre-specified **secondary** candidate predictor, included to explore whether ambiguity about the current state precedes transition. It is not a primary claim and is not to be presented as one.

## 7.2 Structured ICU information

The 17 continuous physiological, neurological, renal, metabolic, haematological and temperature variables of the Paper 1 feature set, taken from the window ending at the landmark, together with fixed baseline covariates (age, sex, stroke subtype, Charlson index, hypertension, diabetes, atrial fibrillation, heart failure, chronic kidney disease) and landmark time.

## 7.3 Treatment variables as predictors

Defining the outcome on a treatment-free state does not exclude treatment from the predictors. Mechanical ventilation, CRRT, vasopressor administration and sedation already in place at the landmark are information genuinely available to the clinician at that moment, and their use as predictors is not leakage.

M0-full retains them. A pre-specified sensitivity analysis removes all four, to establish whether model performance rests principally on prior treatment.

# 8. Neuroimaging

## 8.1 Source and features

Neuroimaging is the only pre-specified additional modality. Features are extracted from head CT/MRI reports in MIMIC-IV-Note. The feature set is given in `imaging_ontology_v1.2.md` and the annotation rules in `radiology_annotation_guideline_v1.2.md`, both frozen with this version (B8). Relative to v1.1: haemorrhage is recorded in two layers — compartment, and the site of intraparenchymal haemorrhage; infarct territory is recorded separately from anatomical region, with no inference between them; herniation is a closed list of subtypes; chronic small-vessel ischaemic change counts as chronic ischaemic change, while white-matter change the report does not attribute to ischaemia does not; and "no definite X" is Absent unless the statement also carries a hedge.

**Ontology freeze rule.** The final imaging feature set is determined solely on the basis of clinical relevance, definitional clarity and validated extraction reliability, **without reference to any association with the study outcome**. A feature may be dropped because it cannot be extracted reliably; it may not be dropped because it appears unrelated to the outcome, and no feature may be added because it appears strongly related to it.

**Assertion framework (v1.1).** Every phenotype is recorded on one common four-level scale — **Present / Absent / Uncertain / Not assessable** — rather than as a bare binary, so that manual annotation and automated extraction share a single evaluation scheme. Phenotype-specific lexical and contextual exceptions sit on top of that scale; they do not replace it. "No evidence of X" is Absent; "cannot exclude X" is Uncertain; a study that cannot demonstrate X is Not assessable, which is not the same as Absent. Negation is scoped to what is actually negated: "no large territorial infarct" negates the large-territorial phenotype, not infarction in general.

For modelling, the primary M1 feature set treats **Present as positive, Absent as negative, and Uncertain and Not assessable as unknown**. A pre-specified sensitivity analysis instead counts probable/likely statements as positive.

**Midline shift (v1.1).** The primary variable is **binary presence**. A measured value is recorded as a conditional secondary severity descriptor only where the report states one, and is **never imputed**: only 22.1% of midline-shift sentences in this cohort carry a millimetre or centimetre value, and whether a number is recorded is itself likely to be related to severity, so treating an unmeasured mention as 0 mm would be wrong.

**Change over time (v1.1).** A statement that compares with a prior study records **both** the current state and the direction of change: "IVH increased from prior" is present with change = increased; "IVH unchanged" is present with change = stable; "IVH decreased" remains present unless the report states resolution or absence of residual. This prevents a described reduction from being read as a negative. The change variables are stored but are **excluded from the primary M1 feature set**; they are reserved for a secondary exploratory analysis of dynamic imaging.

**Not mentioned (B5).** A finding the report never mentions is Absent — except a phenotype the examination cannot demonstrate, in practice large-vessel occlusion on a non-vascular study, which is Not assessable. An indirect vascular sign on such a study (for example a hyperdense-vessel sign) makes large-vessel occlusion Uncertain, never Present.

**Extraction acceptance threshold (B9).** For each phenotype in the primary M1 feature set, extractor output is compared with the primary annotator's labels on the random validation set. A phenotype enters primary M1 only if **Cohen's κ ≥ 0.60** and the random set contains **at least 10 annotator-positive reports**. A phenotype that fails either condition leaves primary M1 and is retained only in a pre-specified sensitivity analysis. The extractor is never re-tuned on validation data. This replaces v1.1's undefined "cannot be extracted reliably", which left room to choose features after seeing results.

## 8.2 Availability timing

A report does not exist as clinical information at the moment the scan is performed; it exists when it is written. For the cohort's head CT/MRI reports, storetime minus charttime has a median of 2.25 hours and a 90th percentile of 15.2 hours.

Availability is therefore keyed on **storetime**, or on whatever field is verified to best represent the report's entry into the clinical record. A report finalised after a landmark may not be used at that landmark. A report belongs to the qualifying admission if its hadm_id is that admission's, or — when it carries no hadm_id — if it was performed on or after admission (B3). This includes the diagnostic scan performed in the emergency department before the admission timestamp, which the first implementation wrongly excluded. The same principle governs ECG and echocardiography. Where a patient has several reports, the most recent clinically available report before the landmark is used, under update rules that distinguish static from evolving findings; those rules are locked before modelling.

## 8.3 Availability is not random

`img_available` is 1 at a landmark if a qualifying report was clinically available before it, and 0 otherwise. Availability rises from 36.4% at the 6-hour landmark to 63.7% at 24 hours and 73.7% at 48 hours, and 26.1% of patients already have a report at ICU admission (figures corrected under B3; v1.1 gave 24.8%, 57.9% and 71.0%). Absence of imaging is a clinical decision, not ordinary random missingness, and absence of imaging is not evidence of absence of pathology.

## 8.4 Computing environment and data handling

All work on raw report text — rule development, manual annotation, extractor
development and automated extraction — is performed in a local environment
compliant with the PhysioNet data use agreement.

Report text is never transmitted to an external large-language-model API, a cloud
document service, a general-purpose assistant, or any party outside the
credentialed study team. Automated extraction runs on a local open-weight model on project hardware. Only the cohort's own reports are processed. The model, prompt, generation settings and a prompt_version hash are fixed and recorded when the extractor is frozen (§15 step 8e), before it is evaluated on the random set; any later change produces a new prompt_version and requires re-evaluation (B6).

Derived artefacts that contain no report text — aggregate counts, note-id indices,
extraction performance tables — may circulate within the credentialed team. Files
that do contain report text are labelled as such and remain on project hardware.

# 9. Models

Five models are fitted in a pre-specified ladder.

| Model | Content | Question answered |
|---|---|---|
| **M0-state** | fixed covariates + filtered state posterior (+ entropy) | How much does the dynamic state representation itself carry? |
| **M0-full** | M0-state + contemporaneous structured ICU information | The strong clinical baseline. |
| **M0+A** | M0-full + `img_available` | What does the decision to image carry, separately from content? |
| **M1-D** | deployable: M0+A plus imaging content where available, falling back to M0+A where not | If imaging is connected to a real risk-stratification system, how much does ranking improve? |
| **M1-I** | imaging content among `img_available = 1`, with stabilized IPW for the selection mechanism | How much information do the imaging findings themselves carry? |

M1-D and M1-I answer different questions and need not agree. Imaging content may be strongly informative among patients who are scanned while the deployed system improves overall capture only modestly, because many patients are not scanned. That divergence is itself a substantive finding and is to be reported as one.

## 9.1 Provisional baseline result

M0-state and M0-full have been fitted (development 2008–2016, evaluated on temporal validation 2017–2019): AUROC 0.795 and 0.849 respectively, difference +0.055 (95% CI +0.031 to +0.077) by patient-level bootstrap. The dynamic state has therefore **not** absorbed contemporaneous routine physiology, and M0-full is confirmed as the strong baseline against which imaging is judged. The adverse state was confirmed on 11 September 2026, so these figures are final. M0+A, re-fitted after the correction in B3, gives AUROC 0.850: the difference from M0-full is +0.001 (95% CI −0.000 to +0.001) and the top-10% capture difference +0.01 percentage points (−0.61 to +0.56). Imaging acquisition is prognostic on its own — event rate 10.4% at landmarks with imaging against 8.0% without — but adds nothing once the filtered state and contemporaneous physiology are known. Availability still depends strongly on the other predictors, so the IPW of §9.2 remains required for M1-I.

## 9.2 IPW specification for M1-I

An availability model estimates P(A = 1 | X) from information available before the landmark. Stabilized inverse probability weights are used, truncated at the 1st and 99th percentiles in the primary analysis and at the 2.5th and 97.5th percentiles in sensitivity analysis. Weight distributions before and after truncation, effective sample size, propensity score distributions, common support and landmark-specific positivity are all reported.

Truncation cannot repair a structural positivity violation. If, at a given landmark, clinical strata exist in which imaged patients are effectively absent and common support therefore fails, that landmark is excluded from the M1-I estimand while being retained in the M1-D analysis. The two estimands are not required to have identical ranges of identifiability.

# 10. Statistical analysis

## 10.1 Confirmatory comparison

There is exactly one.

| Element | Specification |
|---|---|
| Comparison | **M1-D versus M0+A** |
| Population | Temporal validation cohort, 2017–2019 |
| Landmarks | Pooled across all eight (6–48 h) |
| Ranking | Within each landmark separately; patient-landmarks are never pooled before ranking |
| Resource constraint | Top 10% of predicted risk |
| Metric | Difference in 24-hour event capture rate, ΔCapture(10%) |
| Uncertainty | Patient-level clustered bootstrap, 95% CI |

Pooling across landmarks is a design requirement, not a search for significance. The 24-hour landmark alone contains 86 events in the validation cohort; a bootstrap of a genuine effect of this size at that landmark alone yields a 95% CI approximately 16 percentage points wide, which crosses zero, while the pooled estimate over 671 events yields a CI approximately 8 points wide. Assigning the confirmatory test to a single landmark would be a design inefficiency capable of declaring a real effect absent.

## 10.2 Conclusion rule

If the 95% CI for ΔCapture(10%) lies entirely above zero, the study concludes that imaging content provides statistically supported incremental risk-stratification value beyond the dynamic state, contemporaneous physiology and the imaging acquisition decision.

If the CI includes zero, the primary conclusion is that no statistically supported incremental value was observed. In that event the primary conclusion may **not** be replaced by AUROC, AUPRC, the top 5% or top 20% strata, a single favourable landmark, or any other outcome. All such results continue to be reported in full as secondary evidence.

## 10.3 Clinically interpretable effect benchmark

A benchmark of **ΔCapture = +5 percentage points** is pre-specified as a scale for interpretation. It is explicitly **not** a second significance threshold and is not claimed to be an externally established minimal clinically important difference for ICU risk stratification, for which no such value exists.

Its meaning at the primary presentation point: among approximately 1,177 patients at risk at the 24-hour landmark, flagging the highest-risk 10% selects about 118 patients; a 5-point gain in capture corresponds to identifying roughly 4 additional patients who go on to deteriorate or die within 24 hours.

Results are then reported against both axes — whether the interval excludes zero, and where the point estimate falls relative to the benchmark — which permits honest descriptions such as *statistically supported but clinically modest* or *clinically meaningful point estimate with imprecise interval*.

## 10.4 Risk-stratification metrics

At each landmark, patients are ranked within that landmark's risk set and the top 5%, 10% and 20% are selected. For each stratum the following are reported: event capture rate, positive predictive value, absolute event rate, and lift (event rate in the selected group divided by the overall event rate at that landmark).

## 10.5 Standard performance metrics

AUROC, AUPRC, sensitivity, specificity, PPV, NPV, Brier score, calibration intercept, calibration slope and calibration plots, for every model. All confidence intervals and model comparisons account for the clustering of multiple landmarks within a patient, by patient-level clustered bootstrap. Decision curve analysis is reported over a clinically plausible threshold range.

## 10.6 Base-rate change between eras

The event rate falls from 10.0% in development to 7.5% in temporal validation. PPV is sensitive to base rate, so development and validation PPV are **not** directly comparable and a fall in validation PPV is not by itself evidence of degraded discrimination. Lift, which is expressed relative to the contemporaneous base rate, is the appropriate cross-era comparison, and discussion of temporal stability rests on lift and calibration rather than on absolute PPV. Intercept-only recalibration, preserving the relative risk structure, is a pre-specified secondary analysis.

## 10.7 Multiplicity

Only the comparison in §10.1 is confirmatory. All other analyses — the top 5% and 20% strata, individual landmarks including the 24-hour presentation point, AUROC and AUPRC, risk trajectories, subtype analyses, competing-risk analyses, treatment-variable sensitivity, ECG and echocardiography — are secondary or hypothesis-generating and are not subject to formal multiplicity adjustment. All are reported as effect estimates with 95% confidence intervals rather than as *p* values alone.

## 10.8 Sample size and model complexity

989 unique patients experience at least one composite event. Repeated landmarks are not independent observations, so model complexity is judged against the number of independent event patients, the patient-level effective sample size and the validation event count — never against the 31,092 patient-landmarks. This study deliberately does not pursue a high-dimensional black-box model; the planned predictor count is well within what this event supply supports, and parsimony is a design choice rather than a constraint.

# 11. Extraction validation

Automated extraction from radiology reports is validated against manual gold-standard labels in two separate samples, reported separately. They are never combined into a single overall F1.

**Random validation set**, 200 reports drawn from the analysis population — reports of the qualifying admission stored by the 48 h landmark (B4) — one per patient, stratified by AIS/ICH/SAH, excluding the 50 development reports and all reports of their patients. Estimates phenotype prevalence, sensitivity, specificity, negative predictive value, overall accuracy, and the κ of the acceptance threshold (§8.1, B9).

**Positive-enriched validation set — conditional (amended in v1.1).** Whether this set is required, and for which phenotypes, is decided **after** the random set has been annotated, from the number of true positives it yielded for each phenotype. It is not pre-assigned to a named list of findings.

The reason for the change: keyword mention rate is not phenotype-positive prevalence. In this cohort several findings previously assumed to be low-frequency are mentioned often — midline shift in 34.0% of reports, mass effect in 55.0%, intraventricular haemorrhage in 17.7% — but a large share of those mentions are negations (39.6% of midline-shift sentences, 62.0% of large-territorial sentences), so mention rate cannot establish that the random set will supply enough true positives. Only the annotated random set can.

Where an enriched set is triggered, it comprises approximately 150–200 reports drawn from candidate positives identified by the automated system, and estimates positive predictive value, positive-case agreement and error patterns. Because it is selected using the system's own output it can estimate PPV but not sensitivity, and that limitation is stated wherever its results appear.

**Enrichment is never triggered by, or targeted using, a phenotype's association with the study outcome.** The trigger is the observed count of true positives in the random set and nothing else.

A pre-specified subset of approximately 20% is independently annotated by a second credentialed reader once one is available (B2); inter-rater agreement is reported as Cohen's κ with disagreement patterns, and disputed reports are resolved by a pre-specified adjudication procedure.

Total workload is approximately **350–400 unique reports and 420–480 annotation reads**.

Annotation is performed by the study lead as primary annotator, trained on the frozen guideline (B1); the study lead is named in the project log, not here. Every annotator must hold their own PhysioNet credential and MIMIC-IV-Note data use agreement. Until a second credentialed reader is available (B2), extractor performance is reported against the primary annotator's labels and no inter-rater agreement is claimed.

# 12. Secondary and exploratory analyses

**Dynamic risk trajectory.** The repeated-landmark design yields a sequence of risk estimates per patient. ΔRisk_t = P_t − P_{t−6} is computed for patients eligible at consecutive landmarks, and persistently low, persistently high, increasing and decreasing risk groups are compared, to explore whether the rate of change carries information beyond the current level. Pre-specified secondary analysis.

**Stroke subtype.** Patient counts, landmark counts, event rates, imaging availability, imaging phenotype prevalence and model performance are reported for AIS, ICH and SAH separately; subtype × imaging interaction is examined if the event supply permits. Not a primary conclusion.

**ECG and echocardiography.** Neither is required for this study to stand. After the imaging analysis is complete, inclusion is decided on landmark-specific availability, event supply and incremental signal. ECG is a secondary multimodal extension; availability at the 24-hour landmark is 31.8% and is comparatively flat across subtypes (AIS 35.4%, ICH 25.1%, SAH 26.5%). Echocardiography is exploratory and focused on AIS, because availability is strongly subtype-dependent (AIS 40.9%, ICH 10.7%, SAH 14.0%) and therefore heavily confounded by indication. No complete-case CT + ECG + echo cohort is used as a primary analysis population: all three modalities are simultaneously available for at most 13.3% of the risk set. ECG and echocardiography availability still use a timestamp-on-or-after-admission rule and may share the problem corrected for imaging under B3; this is examined before either exploratory analysis (B7).

## 12.1 Pre-specified sensitivity analyses

1. Exclusion of filtered/whole-sequence discordant landmarks.
2. 12-hour prediction horizon.
3. Treatment-inclusive outcome state definition.
4. Deterioration alone, death as a competing event.
5. M0-full without mechanical ventilation, CRRT, vasopressors and sedation.
6. Hard filtered state label in place of the posterior.
7. Alternative imaging-missingness strategies: a model with native missing-value handling; and imaging features set to reference with `img_available` retained — the latter reported as sensitivity only, because absence of imaging is not confirmed absence of pathology.
8. Alternative imaging update rules.
9. Alternative availability-model specifications and weight truncation thresholds.
10. Pooled analysis with the 6-hour landmark excluded.

# 13. Limitations to be stated in the manuscript

1. The model outputs individual risk probabilities, but the evidence supports group-level risk stratification, not individual treatment decisions. This belongs in the abstract.
2. The outcome is short-term physiological deterioration or death, not long-term functional outcome, quality of life or neurological recovery.
3. Imaging information comes from clinical radiology reports, not from CT/MRI pixels; what is evaluated is clinically documented imaging information, not the imaging phenotype.
4. MIMIC is a single health system. This study has temporal validation only; eICU carries no comparable radiology reports, so genuine multicentre multimodal external validation is not available.
5. Imaging acquisition is subject to a clear selection mechanism. Inverse probability weighting cannot remove unmeasured clinical-selection bias.
6. Risk-set composition differs between early and late landmarks, so landmark-specific performance must be read together with the composition of that landmark's risk set.
7. Until a second credentialed reader is available, the reference standard for extraction is a single annotator's labels, and no inter-rater agreement is reported.

# 14. Amendment policy

This protocol was frozen at v1.2 on 11 September 2026 and at v1.3 on 1 October 2026. Amendments create `protocol_v1.4/` and never overwrite this version or its predecessors. Each amendment records what changed, why, and **whether the change was made before or after the relevant result was observed**.

After the freeze, legitimate grounds for amendment are: implementation errors; factual errors about data fields or their contents; and a pre-specified analysis that proves impossible to execute as written. (The adverse-state open item of v1.0 was resolved on 11 September 2026.)

Model performance is not a ground for amendment. The primary estimand at §10.1 does not move because a result is disappointing.

**C1 is not an amendment in the sense of this section (v1.3).** It changes no existing specification and is not justified by any of the three grounds above. It is an additional analysis specified after the confirmatory result was known, recorded in the protocol rather than only in the project log so that its specification and reading rules carry a date and cannot be altered once its results exist. It is labelled as a post-result addition wherever it is reported.

# 15. Analysis sequence

1. Filtered state reconstruction — **complete**.
2. Landmark risk-set construction, 6–48 h, filtered eligibility — **complete**.
3. Composite endpoint construction — **complete**.
4. M0-state — **complete, provisional**.
5. M0-full — **complete, provisional**.
6. Imaging linkage: per-landmark availability, report timestamps, most recent available report — **complete**.
7. M0+A — **complete**.
8. The imaging measurement chain, in this order and no other:
   a. rule-discovery session over the 50-report workbook — **complete** (scored by the study lead);
   b. annotation guideline and phenotype ontology frozen — **complete** (v1.2, with this protocol);
   c. random validation set of 200 reports from the analysis population (B4), annotated blind by the primary annotator; the pre-specified dual-read subset follows once a second credentialed reader exists (B2);
   d. from the true-positive counts in (c), decide which phenotypes if any require a positive-enriched set;
   e. extractor developed on the 50 development reports only, then frozen, with model, prompt, settings and prompt_version hash recorded (B6);
   f. extractor evaluated on the random set; acceptance threshold applied per phenotype (B9);
   g. extractor run over the analysis population — the 6,994 qualifying-admission reports stored by the 48 h landmark (B4) — not all 20,947 tier-A reports.
9. M1-D and M1-I. Not before step 8g.
10. Within-landmark ranking, top 5/10/20%, capture, PPV, lift.
11. Locked evaluation in the 2017–2019 temporal validation cohort.
12. Secondary and exploratory analyses.

# 16. Study logic

Paper 1 asked what states exist and how patients move between them. Paper 2 asked whether that representation transports across health systems and whether it carries information about the near future.

Paper 3 asks: using only what was actually knowable at each clinical moment, can we repeatedly identify the patients most likely to deteriorate in the next 24 hours — and does information that directly describes the brain injury add clinically meaningful stratification on top of a dynamic state and contemporaneous physiology that are already strong?

This is therefore neither a radiology-NLP prediction paper nor a multimodal-AI paper. It is a repeated-landmark clinical risk-stratification study built on a prospectively compatible dynamic state representation, in which neuroimaging is used to test whether brain-injury information carries independent incremental value above a strong physiological baseline.

# Appendix A. Amendment log, v1.0 → v1.1

All four amendments were made on 11 September 2026, **before any imaging feature
was extracted and before any imaging-related result was observed**. None of them
touches the confirmatory comparison at §10.1, which is unchanged.

**A — data-handling boundary written into the protocol (§8.4, new).** The
requirement that all work on raw report text occur in a DUA-compliant local
environment, and that report text never reach an external LLM API or any party
outside the credentialed team, existed in practice and in
`imaging_ontology_v1.0.md` but not in the protocol. It is now a protocol
provision.

**B — positive-enriched validation set becomes conditional (§11).** v1.0
pre-assigned an enriched set to six named "low-frequency" findings. Mention-rate
counts over the 20,947 tier-A reports showed those findings are not rare as
mentions, while a large fraction of mentions are negations — so mention rate
cannot settle whether the random set will yield enough true positives. The
decision now follows the annotated random set. The trigger is the true-positive
count and never a phenotype's association with the outcome.

**C — assertion framework, midline shift, and change over time specified
(§8.1).** v1.0 named the candidate features but did not say how a finding is
asserted. v1.1 fixes a common four-level scale (Present / Absent / Uncertain / Not
assessable) with phenotype-specific lexical exceptions on top; makes midline shift
binary-primary with a non-imputed conditional measurement; and requires comparison
statements to record both current state and direction of change, with the change
variables held out of the primary M1 feature set.

**D — §15 refined into the measurement chain.** The imaging steps are ordered
explicitly — rule session, guideline and ontology freeze, random annotation,
conditional enrichment, extractor freeze, full run — and M1 is stated to come
after the full run and not before.

# Appendix B. Amendment log, v1.1 → v1.2

All nine amendments were made on 11 September 2026, **before any validation annotation, before
the extractor was frozen, and before any imaging-content result was observed**. The
confirmatory comparison at §10.1 is unchanged.

**B1 — primary annotator (§11).** The study lead annotates personally, to understand the rules
first-hand before explaining them to others. v1.1 specified a clinical annotator.

**B2 — dual read deferred (§11, §13).** The second expert's PhysioNet credentialing was
postponed. The 20% dual read, and therefore κ between readers, waits for a second credentialed
reader; meanwhile extractor performance is reported against the primary annotator.

**B3 — implementation error corrected (§8.2, §8.3, §9.1).** Imaging availability had required
every report's timestamp to be on or after hospital admission, which dropped 1,177
admission-linked reports performed before the admission timestamp — chiefly the diagnostic scan
in the emergency department. Found when two admission rules were compared. Corrected rule:
hadm_id match, or no hadm_id and performed on or after admission. Availability figures are
corrected; M0-state and M0-full reproduced exactly; M0+A was re-fitted and its null is
unchanged. No imaging-content result existed.

**B4 — analysis population (§11, §15).** A report stored after the 48 h landmark can never be a
predictor. The extraction run is restricted to qualifying-admission reports stored by 48 h
(6,994) instead of all 20,947 tier-A reports, and the random validation sample is redrawn from
that population: the earlier draw had only 81 of its 200 reports in it. Nobody had read the
earlier draw.

**B5 — not-mentioned rule (§8.1).** v1.1's four-level scale had no value for a finding the
report never mentions. It is Absent, except a phenotype the examination cannot demonstrate
(large-vessel occlusion on a non-vascular study), which is Not assessable; an indirect vascular
sign on such a study makes it Uncertain, never Present. This matches the study lead's practice
in 292 of 315 not-mentioned rows of the development set.

**B6 — extractor specification (§8.4, §15).** The extractor's model, prompt, settings and
prompt_version hash are fixed and recorded at extractor freeze, before evaluation on the random
set; any later change requires re-evaluation.

**B7 — ECG and echocardiography availability (§12).** Open: both still use a
timestamp-on-or-after-admission rule and may share B3's problem. To be examined before either
exploratory analysis.

**B8 — ontology and guideline v1.2 (§8.1).** From the study lead's rule draft, written on the
development reports, and the decisions of 11 September 2026: haemorrhage in two layers;
territory separated from region; herniation subtypes; chronic small-vessel change counted and
non-attributed white-matter change not; "no definite X" Absent unless hedged. No outcome data
were consulted.

**B9 — extraction acceptance threshold (§8.1).** v1.1 allowed a feature to be dropped if it
"cannot be extracted reliably" without defining reliability, which left room for selection after
seeing results. Now: κ ≥ 0.60 against the primary annotator and at least 10 annotator-positive
reports on the random set; otherwise the phenotype leaves primary M1 and is kept only in a
sensitivity analysis. The extractor is never re-tuned on validation data.

# Appendix C. Addition in v1.3

One entry, made on 1 October 2026 by decision of the study lead, **after the confirmatory result
was observed**. Frozen before the second extractor was installed and before it processed any
report, real or fictional.

## C1 — post-lock robustness analysis with a second extraction model

### C1.1 Status

The confirmatory comparison (§10.1) was run on 16 September 2026: ΔCapture(10%) = +0.15
percentage points, 95% CI −2.31 to +1.91. The manuscript body was locked on 18 September 2026,
with the decision that no further models would be added. The study lead reopened that decision on
1 October 2026 for this analysis alone.

C1 is a **post-result addition**. It changes nothing that exists: the confirmatory comparison
(§10.1), the conclusion rule (§10.2), the +5 percentage point benchmark (§10.3), the frozen
extractor (prompt_version 0347237dd3f5) and the primary imaging feature set frozen on 12 September
2026 all stand. C1 is called a *post-lock robustness analysis*. It is not a sensitivity analysis
in the sense of §12.1, whose list was fixed before any result and is not extended.

### C1.2 Question

The primary result is a null. The imaging features come from a language model of 7 billion
parameters; the seven features in the primary model reached κ 0.64–0.80 against the annotator,
and four phenotypes were excluded because κ was below 0.60. A null may therefore reflect
extraction error rather than absence of incremental information in the reports.

C1 asks one question: **when the extraction model is replaced by a substantially more capable
one and everything else is held fixed, does the result of the confirmatory comparison change?**

### C1.3 The second extractor

| Element | Specification |
|---|---|
| Prompt template, `rules_v1.2.md`, output JSON schema | Identical to the frozen extractor; not edited |
| Generation settings | Identical: temperature 0, seed 0, num_ctx 6144, output constrained by the JSON schema |
| Deterministic post-processing | Identical: Not-assessable guard, mention guard, large-vessel-occlusion guard, change cleanup, derived fields |
| Failure handling | Identical: a report that fails twice is quarantined and treated as an extraction failure, never as a negative finding |
| Tuning | **None.** The second extractor is not run on the 50 development reports, and no prompt, rule, setting or guard is changed in the light of any extraction output |
| Runtime | Ollama, local, listening on the loopback address only; the installed version is recorded |

**Model.** The current generation of the same model family, chosen by a fixed order and by
technical criteria only. Candidates, in order:

1. `qwen3.8:27b-q4_K_M`
2. `qwen3.6:35b`
3. `qwen3.5:35b`
4. `qwen2.5:32b-instruct-q4_K_M`

The model used is the **first** candidate that passes both technical criteria on the four
fictional reports in `extractor/fictional_test_reports.json`, which contain no MIMIC text:

- it returns schema-valid output for all four reports without a timeout, under the settings
  above; and
- at the measured speed, the 6,994 reports of the analysis population would take no more than
  five days (at most 61 seconds per report).

Agreement with any label — on the fictional reports or anywhere else — plays no part in the
choice. The choice is made before any MIMIC report is processed by any candidate. If no candidate
passes, C1 is not carried out and that fact is reported.

**Technical adaptation.** Models of the current generation can produce a reasoning trace before
their answer. The request asks for this to be switched off (`think: false`). This is the only
permitted difference in the request, it is applied to every candidate that supports it, and what
the chosen model actually did is stated in the freeze record. No other adaptation is permitted.

**Identity and record.** The model name enters the prompt_version hash, so the second extractor
has its own prompt_version. `extract_v12.py` and `rules_v1.2.md` are not edited; the second
extractor calls them through a wrapper that replaces the model name and adds the field above.
Before validation a freeze record is written: model tag and digest, quantisation, Ollama version,
prompt_version, hardware, and the measurements on the fictional reports for every candidate tried.

### C1.4 Validation

The second extractor is run on the same 200 random validation reports and scored against the
primary annotator's labels with the scripts used for the frozen extractor: Cohen's κ on the
four-level scale (the primary reading fixed on 12 September 2026) and agreement, per phenotype
and per list category; binary κ as a secondary statistic that does not affect eligibility.

Those labels have already been used to evaluate the frozen extractor. The second extractor is
tuned on nothing, so they remain a valid test of it, and using the same reports gives a paired
comparison of the two extractors. The results are reported whatever they are, and the second
extractor is not changed in the light of them.

### C1.5 Full extraction and feature sets

The second extractor is run on all 6,994 reports of the analysis population. Features are merged
to the landmarks under the update rule locked on 16 September 2026, unchanged.

The confirmatory comparison is repeated on two feature sets, both fixed here:

- **C1-a — the same seven features** (the principal robustness analysis): midline shift,
  intraventricular haemorrhage, intracranial haemorrhage, haemorrhage compartments
  intraparenchymal and subarachnoid, infarct territory MCA, infarct region cerebellum, with
  values from the second extractor. A feature is used even if its κ under the second extractor
  is below 0.60, and that κ is reported. Only the extraction model differs from the primary
  analysis.
- **C1-b — the feature set re-derived under B9.** The thresholds of B9 and of the clarification
  of 12 September 2026 (κ ≥ 0.60 on the four-level scale and at least 10 annotator-positive
  reports; the same for list categories) are applied to the second extractor. Features that pass
  enter; no new threshold is introduced. Large-vessel occlusion stays out on the structural
  ground already recorded. `midline_shift_mm` and the change fields stay out, as in the frozen
  ontology.

Both use the estimand of §10.1 without change: M1-D versus M0+A, temporal validation 2017–2019,
pooled over the eight landmarks, ranked within each landmark, top 10% of predicted risk,
difference in 24-hour event capture, patient-level clustered bootstrap 95% CI with 2,000
replicates and the analysis seed. Model specification and the encoding of Present, Absent and
unknown are those of the primary analysis.

Also reported, as aggregates only: agreement between the two extractors over all reports, per
feature (κ and percentage agreement), and the proportion of validation landmarks at which a
feature value differs.

### C1.6 Reading rules, fixed before running

1. **The result obtained with the frozen extractor remains the primary result.** Nothing found
   under C1 replaces the conclusion of §10.1 (§10.2).
2. A C1 result is **consistent** with the primary result if its 95% CI includes zero and its
   upper bound is below +5 percentage points. C1-a and C1-b are read separately.
3. **If both are consistent**, the manuscript states that the result was unchanged when
   extraction was repeated with a larger model: the figures in the supplement, one sentence in
   Results and one in Limitations. The wording boundaries of this study still apply — "no
   incremental value was observed", no statement that the state absorbed imaging information,
   and no equivalence language.
4. **If either is not consistent** — an interval excluding zero, or an upper bound at or above
   +5 percentage points — the manuscript states in the abstract, Results and Limitations that
   the conclusion is sensitive to the extraction model, and gives the results of both extractors.
   The primary conclusion is not rewritten as a positive finding. How the paper is then positioned
   is for the study lead to decide; this entry does not pre-empt that decision.
5. **No third model.** No further model, feature set or metric is added because of what C1 shows.
   The only route to a different model is the ordered technical selection of C1.3.
6. **No exit after validation.** Once a second extractor has been selected under C1.3, steps
   C1.4 and C1.5 are completed and reported, whatever the validation κ.

### C1.7 Data handling

As §8.4. Report text is processed on project hardware only and is sent to no external service.
The extraction scripts print no report text. Work with an AI coding assistant is limited to
code, counts and summary statistics.

### C1.8 Sequence

1. v1.3 frozen and recorded in `PROJECT_LOG.md`.
2. Ollama installed; candidates tested in order on the fictional reports; model selected.
3. Freeze record of the second extractor written.
4. The 200 validation reports extracted and scored; results logged.
5. The 6,994 reports extracted.
6. Features merged; C1-a and C1-b run; agreement between extractors computed; results logged.
7. Changes to the manuscript proposed separately and made only after the study lead confirms.
