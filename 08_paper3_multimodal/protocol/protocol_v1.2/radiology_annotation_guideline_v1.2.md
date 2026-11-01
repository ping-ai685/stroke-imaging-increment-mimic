# Radiology annotation guideline — v1.2

**Status: FROZEN, 11 September 2026** — approved by the study lead, together with
`imaging_ontology_v1.2.md` and protocol v1.2. Changes are made only under protocol §14 and
logged in §9.
Supersedes `protocol_v1.1/radiology_annotation_guideline_v1.1.md`.

**Source.** The study lead's rule draft (`annotation_session/rules_draft_study_lead_v0.md`),
written while scoring the 50 development reports, and the decisions of 11 September 2026.
No rule was chosen with reference to outcome data.

---

## 1. Scope, roles and sampling

**Primary annotator** — the study lead, personally (named in `PROJECT_LOG.md`), trained on this
guideline. Every annotator must be a credentialed PhysioNet user who has personally signed the
MIMIC-IV-Note data use agreement; the DUA binds each individual and cannot be extended to a
colleague.

**Dual reading** — the pre-specified 20% subset (40 reports) is read independently by a second
credentialed reader once one is available (protocol v1.2). Until then, extractor performance
is reported against the primary annotator's labels and no inter-rater agreement is claimed.

**Random validation set** — `annotation_validation/random200_index.csv` (v2): 200 reports from
the analysis population — reports of the qualifying admission stored by the 48 h landmark —
stratified by stroke subtype, one per patient. The 50 development reports and all reports of
their 47 patients are excluded. The development reports may be used to develop the extractor,
never to validate it.

**Positive-enriched set — conditional.** Triggered per phenotype only if the random set yields
too few true positives; never triggered or targeted by association with the outcome. It
estimates PPV, not sensitivity. The two sets are reported separately and never merged into
one F1.

**Blinding** — the annotator sees report text only: no outcome, no state assignment, no landmark
risk, no extractor output.

**Data handling** — report text stays on project hardware and is never pasted into any external
service, including any AI tool (protocol §8.4).

## 2. Assertion scale and global wording rules

Every assertion field takes exactly one value.

| Level | Meaning |
|---|---|
| `Present` | the finding is asserted |
| `Absent` | the finding is explicitly excluded, or is never mentioned (G1) |
| `Uncertain` | hedged — neither asserted nor excluded |
| `Not assessable` | the examination cannot demonstrate the finding, or the report says the region could not be evaluated, without suggesting the finding is there |

The global rules below apply to every phenotype. Phenotype-specific rules in §4 sit on top of
them and never replace them.

**G1 — Not mentioned.** A finding the report never mentions is `Absent` — except a phenotype
the examination cannot demonstrate, which is `Not assessable`: in practice, large-vessel
occlusion on a non-vascular study; an indirect sign on such a study makes it Uncertain (§4.13). (Decided 11 Sep 2026; this was the study lead's practice in
292 of 315 not-mentioned rows of the development set.)

**G2 — Negation.** "No X", "no evidence of X", "without X", "negative for X", **"no definite X"**
and **"no definite evidence of X"** are `Absent` — unless the same statement also carries a
hedge ("…but cannot exclude", "…possibly"), in which case it is `Uncertain`. "Definite" alone is
a routine qualifier, not a hedge. (Decided 11 Sep 2026; supersedes the draft's hydrocephalus
example.)

**G3 — Hedges and assertions.**
`Uncertain`: possible, possibly, probable, likely, most likely, suggestive of, suspicious for,
concerning for, cannot exclude, cannot be excluded, may represent, equivocal, questionable,
indeterminate, early / impending / at risk of (for an event that has not happened).
`Present`: consistent with, compatible with, represents, demonstrates, there is, compatible
with residual.
The primary M1 feature set treats `Uncertain` as unknown; a pre-specified sensitivity analysis
counts probable/likely as positive (protocol §8.1).

**G4 — Hedge plus technical limitation.** If a report both hedges a finding and cites a
limitation ("possible mild oedema, limited by artefact"), the finding is `Uncertain`. It is
`Not assessable` only when the report says the finding or region cannot be evaluated without
suggesting the finding is present.

**G5 — Negation scope.** Negation covers only what it names. "No large territorial infarct"
makes `large_territorial_infarct` Absent and says nothing about `acute_infarction`.

**G6 — Current state versus change.** A comparison describes change, not presence. "Stable",
"decreased" and "increased" leave a lesion that is still there `Present`. **"No new X" does not
mean X is absent**: an existing haemorrhage with no new bleeding is `Present`.

**G7 — No inference.** Record only what the report states. A large infarct does not make
oedema Present; mass effect does not make herniation Present; a lobe does not imply a vascular
territory.

**G8 — Findings versus impression.** A specific, localised positive description outranks a
general summary: "no acute intracranial process" in the impression does not cancel a lesion
described in the findings. A direct contradiction that context cannot resolve is `Uncertain`
and sets `adjudication_flag` (§5).

**G9 — Coexistence.** Several pathological states may coexist. Territories, regions,
compartments and herniation subtypes are multi-label; acute and chronic change are independent.

## 3. Change over time

Where the report compares with a prior study, record both the current assertion and the
direction: `new`, `increased`, `stable`, `decreased`, `resolved`, `not_stated`.

- lesion increased from prior → Present + increased
- lesion unchanged → Present + stable
- lesion decreased but still visible → **Present** + decreased
- lesion resolved / no residual → Absent + resolved

## 4. Phenotype rules

### 4.1 Acute infarction — `acute_infarction`
Present when the report clearly describes acute or subacute infarction. Absent when acute
infarction is excluded. Uncertain when only an acute component is suggested ("cannot exclude a
subacute component") without a clear diagnosis. Chronic or old infarction and encephalomalacia
are not evidence of acute infarction.
- clear acute infarct → Present
- no acute infarct → Absent
- chiefly chronic infarction, a subacute component cannot be excluded → Uncertain

### 4.2 Territory and region — `infarct_territory`, `infarct_region`
Record only when the report states them; multi-label; never force a single category.
`infarct_territory` (vascular, only when named): ACA, MCA, PCA, vertebrobasilar, watershed.
`infarct_region` (anatomical, as stated): frontal, parietal, temporal, occipital, insula,
basal ganglia, thalamus, deep white matter, brainstem, cerebellum.
A lobe does not imply a territory, and a territory does not imply a lobe (G7).
- infarct in the MCA territory involving the basal ganglia → territory MCA; region basal ganglia
- infarcts in frontal, parietal, temporal and occipital lobes → four regions; territory empty
  unless named

### 4.3 Large territorial infarct — `large_territorial_infarct`
Present only when the report's wording supports a large or extensive territorial infarct: e.g.
large, extensive, massive, large territorial, complete or near-complete [vessel] territory,
malignant [MCA] infarction, involving most of a hemisphere. An infarct without size wording is
not large (G1, G7).
- extensive infarction of multiple regions of one hemisphere → Present
- small focal infarct → Absent

### 4.4 Intracranial haemorrhage — `intracranial_haemorrhage`
Present when any haemorrhagic component is currently present in any compartment —
intraparenchymal, subarachnoid, subdural, epidural or intraventricular. "No new haemorrhage" is
not absence of an existing one (G6). A finding whose differential includes haemorrhage and a
non-haemorrhagic change (possible microbleed versus other) is Uncertain.
- existing haemorrhage persists, no new haemorrhage → Present
- focus may be a microbleed or a non-haemorrhagic change → Uncertain
- findings describe new haemorrhage, impression denies it → Uncertain + adjudication_flag

### 4.5 Haemorrhage compartment and site — `haemorrhage_compartment`, `iph_location`
Two layers, both multi-label and recorded only as stated (decided 11 Sep 2026).
**Layer 1 — `haemorrhage_compartment`:** intraparenchymal, subarachnoid, subdural, epidural,
intraventricular. Intraventricular is derived from §4.6 and is not annotated a second time.
**Layer 2 — `iph_location`:** for intraparenchymal haemorrhage only, the anatomical site —
lobar, deep / basal ganglia, thalamic, brainstem, cerebellar. Infratentorial origin is derived
(brainstem or cerebellar), not annotated.
- intraparenchymal and intraventricular haemorrhage → compartment intraparenchymal (+ intraventricular via §4.6)
- subarachnoid, subdural and intraventricular blood → compartments subarachnoid + subdural (+ intraventricular via §4.6); no iph_location
- basal ganglia haematoma → compartment intraparenchymal; iph_location deep / basal ganglia
- cerebellar haematoma → compartment intraparenchymal; iph_location cerebellar (infratentorial, derived)

### 4.6 Intraventricular haemorrhage — `intraventricular_haemorrhage`
Present while blood or blood products remain in the ventricles, even if decreased, stable or
redistributed. Record the change separately.
- IVH decreased but still visible → Present; change decreased
- IVH unchanged → Present; change stable
- no IVH → Absent

### 4.7 Cerebral oedema — `cerebral_oedema`
Present when oedema is clearly described. Uncertain when it is only suspected, including when a
hedge is combined with an artefact or technical limitation (G4). Infarction or haemorrhage alone
does not imply oedema (G7).
- clear perilesional oedema → Present
- possible mild oedema, study limited by artefact → Uncertain

### 4.8 Midline shift — `midline_shift_present`, `midline_shift_mm`
`midline_shift_present` is the primary variable: Present for any stated shift; Absent when
shift is excluded or never mentioned. When the report gives a value, record it in
`midline_shift_mm` (cm converted to mm). A missing number is never 0 mm and never makes the
shift Absent. Record change separately. If two parts of one report give different values, keep
both, set `adjudication_flag`, and do not average.
- about 6 mm shift, increased from prior → Present; 6 mm; increased
- mild shift, stable → Present; mm missing; stable
- no midline shift → Absent

### 4.9 Hydrocephalus — `hydrocephalus`
Present when hydrocephalus is clearly present; Absent when it is excluded — including
"no definite evidence of hydrocephalus" (G2) and "ventricles normal in size". Uncertain only with
a hedge.
- hydrocephalus persists → Present
- no hydrocephalus / no definite evidence of hydrocephalus / ventricles normal in size → Absent
- possible early hydrocephalus → Uncertain

### 4.10 Mass effect — `mass_effect`
Present while mass effect is still present — effacement, compression or displacement of brain
structures — even if described as unchanged, not increased or improved (G6). A "mass" (tumour)
is not mass effect: "cannot exclude an underlying mass" says nothing about mass effect.
Uncertain when mass effect can only be inferred and the study is clearly limited (G4).
- mass effect persists, not increased → Present; stable
- ventricular compression suggested, study markedly limited → Uncertain
- no mass effect → Absent

### 4.11 Herniation — `herniation_*`, derived `herniation`
Record each subtype separately: subfalcine (including parafalcine), uncal, transtentorial,
tonsillar, external (through a craniectomy defect), unspecified. Subtypes may differ in status.
Predictive or warning language — early, impending, at risk of — is Uncertain, not Present.
Overall `herniation` is derived: Present if any subtype is Present; otherwise Uncertain if any
is Uncertain; otherwise Absent.
- subfalcine herniation present, no transtentorial herniation → subfalcine Present;
  transtentorial Absent
- early / impending uncal herniation → uncal Uncertain
- brain herniating through the craniectomy defect → external Present
- tonsillar descent with foramen magnum crowding → tonsillar Present

### 4.12 Chronic ischaemic change — `chronic_ischaemic_change`
Present when the report describes old or chronic infarction, chronic ischaemic injury,
encephalomalacia, gliosis, **chronic small-vessel / microvascular ischaemic change, or
white-matter change the report attributes to chronic ischaemia** (decided 11 Sep 2026 — the
practice used on the 50 development reports). **White-matter hypodensity or abnormality that
the report does not attribute to ischaemia is not inferred to be Present** (G7). Hedged
attribution ("likely chronic small-vessel disease") is Uncertain (G3). Independent of acute
infarction: both may be Present.
- old infarct and encephalomalacia → Present
- new acute infarct on a background of chronic infarction → chronic Present; acute Present
- periventricular white-matter changes consistent with chronic small-vessel disease → Present
- non-specific white-matter hypodensities, no cause given → Absent (not attributed to ischaemia)

### 4.13 Large-vessel occlusion — `large_vessel_occlusion`
The four levels are defined as follows (confirmed 11 Sep 2026).

| Level | Condition |
|---|---|
| `Present` | appropriate vessel imaging — CTA, MRA, DSA, or a report that explicitly evaluates vessel patency — directly shows occlusion of a large vessel |
| `Absent` | appropriate vessel imaging directly shows the large vessels patent |
| `Uncertain` | a study that cannot directly assess vessel patency shows an indirect vascular sign suggesting occlusion, such as a hyperdense-vessel sign |
| `Not assessable` | a study that cannot directly assess vessel patency, with no such indirect sign |

On a study that cannot directly assess vessel patency, occlusion is **never** recorded Absent
merely because none is described (G1). A hyperdense-vessel sign is indirect evidence: it
suggests occlusion but does not demonstrate it, and is **never upgraded to Present**.
- non-vascular study with an indirect sign suggesting occlusion (e.g. a hyperdense-vessel sign) → Uncertain
- non-vascular study with no mention of any occlusion sign → Not assessable, not Absent
- CTA / MRA directly shows occlusion / patency → Present / Absent

## 5. Adjudication

A report gets `adjudication_flag` when a conflict cannot be resolved by the rules: a findings /
impression contradiction (G8), conflicting measurements (§4.8), or a genuine boundary case.

**Until a second credentialed reader exists:** flagged reports are resolved by the primary
annotator in a separate second pass, after the first pass over all 200 is complete and without
seeing extractor output. Each resolution is written as a rule and logged in §9; it applies
prospectively, and reports already annotated are re-checked against it, with every changed
label logged.

**Once a second reader exists:** disagreements in the dual-read subset are resolved by
discussion; if unresolved, by a third credentialed reader.

## 6. Annotation template

The same workbook format as the 50 development reports — one report per page, report text
verbatim and untranslated — with the scoring table expanded to every field in
`imaging_ontology_v1.2.md`: the ten assertion phenotypes with their change fields, the six herniation subtypes, the four lists (territory, region, compartment, intraparenchymal site), `midline_shift_mm`, `adjudication_flag` and a rule note.
Generated from `annotation_validation/random200_index.csv` after the freeze.

## 7. Primary M1 features

Which fields enter M1, and how, is fixed in protocol §8.1, not here: Present → positive,
Absent → negative, Uncertain and Not assessable → unknown; change fields and
`midline_shift_mm` are held out of the primary feature set.

## 8. Closure of the v1.1 open items

| v1.1 §8 item | Closed by |
|---|---|
| Phenotype-specific lexical exceptions | §2 (G1–G9) and §4 |
| Operational definition of large territorial infarct | §4.3 |
| Midline-shift measurement | §4.8 — recorded as stated; not in primary M1 |
| Herniation subtypes | §4.11 — closed list, per-subtype status |
| Not assessable phrasings | G1, G4, §4.13 |
| Worked examples | §4 |
| Adjudication procedure | §5 |
| Annotation template | §6 |

## 9. Post-freeze clarification log

Clarifications of rules that are already frozen. They do not change the specification, they are
applied prospectively, and each records its date and basis. Both entries below were made on
12 September 2026 from disagreements on the **development** set — before the extractor was
frozen and before the random validation set was touched.

**C1 — 12 September 2026 — hydrocephalus (§4.9).** Enlarged, prominent or dilated ventricles, or
ventriculomegaly, **without an explicit diagnosis of hydrocephalus, is not hydrocephalus**
(Absent); the more so when the report describes atrophy or ex vacuo dilatation. This follows G7:
a phenotype the report does not state is not inferred. It does **not** override G3: if the report
hedges hydrocephalus itself ("possible hydrocephalus"), the answer is Uncertain.
*Basis:* in all seven development disagreements the word "hydrocephalus" never appeared; four
described enlarged or prominent ventricles, three mentioned atrophy or ex vacuo, and the
annotator scored Absent.

**C2 — 12 September 2026 — acute infarction (§4.1).** `acute_infarction` is **Present** when the
report describes infarct or infarction, the lesion is not marked chronic, old, remote or a
chronic encephalomalacic change, and there is no other clear evidence that it is chronic.
**Subacute infarction is also Present.** The phenotype therefore captures the current
acute/subacute infarct burden rather than a narrow radiological acute-only window, and the
manuscript names it the **acute/subacute infarction phenotype** so that the name and the rule
agree.
*Basis:* of ten development disagreements, nine reports used the word "infarct" but only four
said "acute" and four said "subacute"; none said chronic or old, and the annotator scored Present.

**No further rule tuning.** Once the extractor is frozen, development rules are not revisited,
whatever the random validation set shows; otherwise the blinded validation loses its meaning.
