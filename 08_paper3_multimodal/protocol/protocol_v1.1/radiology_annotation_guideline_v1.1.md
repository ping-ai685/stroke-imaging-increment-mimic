# Radiology annotation guideline — v1.1

**Status: still incomplete, but no longer a bare skeleton.**

The sampling design, the assertion framework and the handling of the eight
ambiguous constructions are now decided. What remains is the phenotype-specific
lexical detail, which can only come from reading real reports. That is the purpose
of the rule-discovery session (PROTOCOL §15, step 8a).

**This file must be completed and re-frozen before annotation begins.**
Supersedes `protocol_v1.0/radiology_annotation_guideline_v1.0.md`.

---

## 1. Sampling and workload

**Random validation set** — approximately 200 reports, stratified random by stroke
subtype (AIS / ICH / SAH), annotated blind. Estimates phenotype prevalence,
sensitivity, specificity, negative predictive value and overall accuracy.

**Positive-enriched validation set — conditional.** Whether it is required, and for
which phenotypes, is decided **after** the random set is annotated, from the number
of true positives it yielded per phenotype. Never triggered by, or targeted using,
a phenotype's association with the study outcome. Where triggered: approximately
150–200 reports from system-identified candidate positives, estimating PPV and
positive-case agreement only — it cannot estimate sensitivity, and that is stated
wherever its results appear.

The two sets are analysed and reported separately and are never combined into a
single overall F1.

**Dual reading** — a pre-specified subset of approximately 20%, independently
annotated by a second reader. Cohen's κ and disagreement patterns are reported.

**Workload** — approximately 350–400 unique reports and 420–480 annotation reads,
if enrichment is triggered; approximately 200 reports and 240 reads if it is not.

**Roles** — a primary clinical annotator with pre-defined stroke-imaging annotation
training; a second independent annotator for the dual-read subset. Individuals are
named in the project management documentation, not here. **Every annotator must be a
credentialed PhysioNet user who has personally signed the MIMIC-IV-Note data use
agreement** — the DUA binds each individual and cannot be extended to a colleague
by another credentialed team member.

**Blinding** — annotators see report text only: no outcome, no state assignment, no
landmark risk, no model output.

**Data handling** — report text stays on project hardware and is never pasted into
any external service (PROTOCOL §8.4).

## 2. Assertion framework

Every phenotype is recorded on one scale: **Present / Absent / Uncertain / Not
assessable**. Phenotype-specific lexical exceptions sit on top of this scale and do
not replace it — the point of a common scale is that manual annotation and
automated extraction can be evaluated in the same terms.

| Level | Rule |
|---|---|
| `Present` | the finding is asserted |
| `Absent` | explicitly excluded — "no evidence of X", "without X", "negative for X" |
| `Uncertain` | hedged — "cannot exclude X", "possible", "suspicious for", "equivocal", "question of" |
| `Not assessable` | the study cannot demonstrate it — motion-limited, or a vascular phenotype on a non-vascular study |

**Negation scope.** Negation applies only to what is negated. "No large territorial
infarct" makes `large_territorial_infarct` = Absent and leaves `acute_infarction`
untouched.

**`Not assessable` ≠ `Absent`.** This matters most for large-vessel occlusion: a
non-contrast head CT that does not mention LVO has not excluded it, and must not be
recorded as Absent. In practice LVO defaults to `Not assessable` unless a vascular
study is available.

## 3. Change over time

Where the report compares with a prior study, record **both** the current assertion
and the direction of change: `new`, `increased`, `stable`, `decreased`, `resolved`,
`not stated`.

- "IVH increased from prior" → Present + increased
- "IVH unchanged" → Present + stable
- "IVH decreased" → **Present** + decreased
- "IVH resolved" / "no residual IVH" → Absent + resolved

A described reduction is not a negative. This is not a corner case: 20.9% of
intraventricular-haemorrhage sentences in this corpus are comparative.

## 4. Midline shift

Primary variable is **binary presence**. A measurement is recorded only where the
report states one, as a conditional secondary descriptor, and is **never imputed** —
only 22.1% of midline-shift sentences carry a value, and whether a number is given
is itself likely related to severity, so an unmeasured mention must not become
0 mm.

## 5. Multi-label fields

`infarct_territory` and `haemorrhage_location` are multi-label. Several may be
present simultaneously; do not force a single category. `multiple_territories` is
derived, not annotated.

## 6. Acute versus chronic

`acute_infarction` and `chronic_ischaemic_change` are independent phenotypes. One
report may have both Present. Neither implies the other is Absent.

## 7. Findings versus impression

Do not apply a blanket "impression wins" rule. A specific, localised positive
description takes precedence over a general summary — "no acute intracranial
process" in the impression does not override a specific lesion described in
findings. A direct contradiction that context cannot resolve is recorded as
`Uncertain` and goes to adjudication.

## 8. What the rule-discovery session must still settle

- [ ] Phenotype-specific lexical exceptions on top of the assertion scale
- [ ] The operational definition of "large territorial infarct"
- [ ] Whether `midline_shift_mm` is continuous or dichotomised, and at what threshold
- [ ] Herniation subtypes: free text or closed list
- [ ] Which phrasings in this corpus count as `Not assessable` for each phenotype
- [ ] Worked examples, two or three per phenotype, with the agreed label
- [ ] The adjudication procedure for dual-read disagreements
- [ ] The annotation interface or spreadsheet template

The session works from `annotation_session/annotation_workbook_v1.1.docx` (English)
or `annotation_workbook_v1.1_CN.docx` (Chinese scaffold; report text English and
verbatim in both): 50 reports, five random per subtype plus five candidates for each
of six findings, each with a Present / Absent / Uncertain / Not assessable scoring
table and a **rule note** column. The rule notes are the product of the session; the
labels are a by-product. (An earlier v1.0 workbook, built before this guideline, was
never circulated and has been withdrawn.)

**Session record, 11 September 2026.** The Chinese workbook was scored by the study lead, a
credentialed PhysioNet user, on project hardware (`annotation_workbook_v1.1_CN_scored.docx`): 50/50 reports, 650/650 rows,
one level per row — Absent 416, Present 183, Not assessable 36 (all LVO), Uncertain
15 — with 83 rule notes in 36 reports. The notes are extracted locally into
`rule_notes_digest_REVIEW.md` for review before any rule is written into this file.
The checklist above is ticked only when a rule has been written here, not when a
note exists.

**The 50 rule-discovery reports are development material.** They are excluded from
the random validation set, from any positive-enriched set, and from every evaluation
of the extractor. They may be used to develop the extractor, never to validate it:
the rules were written while reading them, so validating against them would be
circular. Their note_ids are listed in `annotation_session/session_packet_index.csv`,
and every sampling script must drop them before drawing.

The scoring columns are deliberately not expanded into the full ontology at this
stage. The session's job is to define what Present, Absent, Uncertain and Not
assessable mean. Change direction, `midline_shift_mm` and the multi-label territory
fields become machine-readable fields only after those definitions are frozen.
