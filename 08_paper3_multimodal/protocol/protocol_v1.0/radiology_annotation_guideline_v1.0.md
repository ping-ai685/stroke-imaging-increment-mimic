# Radiology annotation guideline — v1.0 SKELETON

**Status: INCOMPLETE. This is a skeleton, not a usable guideline.**

The sampling design, the workload and the reporting rules below are settled and
frozen with the protocol. The per-feature annotation rules are **not** written,
because they require clinical input that has not yet been obtained, and writing
them without that input would be guesswork presented as specification.

**This file must be completed and re-frozen before any annotation begins.** The
open items are listed in `imaging_ontology_v1.0.md` under "Open items".

---

## 1. What is settled

### 1.1 Sampling

**Random validation set** — approximately 200 reports, stratified random by stroke
subtype (AIS / ICH / SAH). Estimates feature prevalence, sensitivity, specificity,
negative predictive value and overall accuracy.

**Positive-enriched validation set** — approximately 150–200 reports, enriched from
candidate positives identified by the automated system, for midline shift,
hydrocephalus, intraventricular haemorrhage, oedema, mass effect and herniation.
Estimates positive predictive value, positive-case agreement and error patterns.

The enriched set is selected using the system's own output. It can therefore
estimate PPV but **not** sensitivity, and that limitation is stated wherever its
results appear. The two sets are analysed and reported separately and are never
combined into a single overall F1.

### 1.2 Dual reading

Approximately 20% of reports, pre-specified before annotation begins, are
independently annotated by a second reader. Cohen's κ and disagreement patterns
are reported. Disputed reports go to the adjudication procedure at §1.4.

### 1.3 Workload

Approximately **350–400 unique reports** and **420–480 annotation reads** in total.

### 1.4 Roles and adjudication

A primary clinical annotator with pre-defined stroke-imaging annotation training
labels all reports. A second independent annotator labels the dual-read subset.
Disagreements are resolved by a pre-specified adjudication procedure, to be
written into §2 of this file.

Individuals are not named here. Personnel are recorded in the project management
documentation so that a change in staffing does not require a scientific
amendment.

### 1.5 Blinding

Annotators see the report text only. They do not see the patient's outcome, state
assignment, landmark risk, or any model output.

### 1.6 Handling of the report text

MIMIC text stays on project hardware. It is not pasted into any external service,
LLM API or cloud document, under the data use agreement.

---

## 2. What is NOT yet written

- [ ] Per-feature operational definitions for all 13 features in the ontology
- [ ] Negation and uncertainty rules
- [ ] Rules for comparison statements referring to a prior study
- [ ] Midline shift: binary, millimetres, or threshold — and which threshold
- [ ] "Not assessable" versus "absent" for findings a given modality cannot show
- [ ] Worked examples, ideally two or three per feature, with the correct label
- [ ] The adjudication procedure for disagreements
- [ ] The annotation interface or spreadsheet template

Completing these requires a clinician to go through a sample of real reports and
fix the conventions. That session is the true start of Phase 4.
