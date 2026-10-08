RULES (condensed from the frozen annotation guideline v1.2; the guideline is normative)

GLOBAL
G1. A finding the report does not mention is Absent. The only exception is large-vessel occlusion on a
study that cannot assess vessel patency, which is Not assessable. A head CT or MRI CAN assess every
parenchymal finding (infarct, haemorrhage, intraventricular blood, oedema, midline shift,
hydrocephalus, mass effect, herniation, chronic ischaemic change). For these, answer Not assessable
ONLY if the report explicitly says that finding or its region could not be evaluated.
G2. "no X", "no evidence of X", "without X", "negative for X", "no definite X" and "no definite evidence
of X" are Absent. If the same statement also hedges ("but cannot exclude", "possibly"), it is Uncertain.
G3. Uncertain wording: possible, possibly, probable, likely, most likely, suggestive of, suspicious for,
concerning for, cannot exclude, cannot be excluded, may represent, equivocal, questionable,
indeterminate, early / impending / at risk of. Present wording: consistent with, compatible with,
represents, demonstrates, there is.
G4. A hedge together with a technical limitation ("possible mild oedema, limited by artefact") is
Uncertain.
G5. Negation covers only what it names. "No large territorial infarct" makes infarct_large Absent and
says nothing about infarct_acute.
G6. A comparison describes change, not presence. A lesion that is stable, decreased or increased but
still there is Present. "No new haemorrhage" does NOT mean there is no haemorrhage: an existing
haemorrhage with no new bleeding is Present. Only "resolved" or "no residual" makes a lesion Absent.
G7. No inference. A large infarct does not make oedema Present. Mass effect does not make herniation
Present. A lobe does not imply a vascular territory; a territory does not imply a lobe.
G8. A specific, localised positive description in the findings outranks a general summary such as "no
acute intracranial process" in the impression. A true contradiction is Uncertain.
G9. Findings coexist. Lists may hold several items. Acute and chronic change are independent.

PHENOTYPES
infarct_acute: Present when the report describes infarct or infarction and does NOT mark it as chronic,
old, remote or chronic encephalomalacic change, and nothing else shows the lesion is chronic. An infarct
with no acuity word is Present. Subacute infarction is Present. A purely chronic or old infarct, or
encephalomalacia alone, is Absent here (record it under chronic_isch). "Cannot exclude a subacute
component" is Uncertain. [clarification C2 of the guideline, 12 Sep 2026]
territory: only a vascular territory the report names: ACA, MCA, PCA, vertebrobasilar, watershed.
region: anatomical regions of infarction as the report states them.
infarct_large: Present only with size wording — large, extensive, massive, large territorial, complete or
near-complete territory, malignant infarction, most of a hemisphere. An infarct without size wording is
Absent here.
haem: any current haemorrhage in any compartment (intraparenchymal, subarachnoid, subdural, epidural,
intraventricular). A focus that may be a microbleed or a non-haemorrhagic change is Uncertain.
haem_compartment: intraparenchymal, subarachnoid, subdural, epidural. Intraventricular blood goes in ivh,
not here.
iph_site: for intraparenchymal haemorrhage only: lobar, deep_basal_ganglia, thalamic, brainstem,
cerebellar.
ivh: Present while blood remains in the ventricles, even if decreased, stable or redistributed.
oedema: clearly described oedema or swelling is Present; only suspected is Uncertain.
mls: any stated shift of midline structures is Present. mls_mm only if a number is stated (cm converted to
mm); never estimate.
hydro: hydrocephalus. "Ventricles normal in size" and "no definite evidence of hydrocephalus" are Absent.
Enlarged, prominent or dilated ventricles, or ventriculomegaly, WITHOUT an explicit diagnosis of
hydrocephalus is Absent — the more so with atrophy or ex vacuo dilatation. Do not infer hydrocephalus from
ventricular size. But if the report hedges hydrocephalus itself ("possible hydrocephalus"), that is
Uncertain. [clarification C1 of the guideline, 12 Sep 2026]
mass_effect: effacement, compression or displacement of brain structures is Present, even if stable or
improved. A "mass" (tumour) is not mass effect: "cannot exclude an underlying mass" says nothing about
mass_effect.
herniation: IF THE REPORT MENTIONS HERNIATION ANYWHERE — findings or impression — YOU MUST PUT AN ENTRY IN
THE herniation LIST. Use the named subtype: subfalcine (including parafalcine), uncal, transtentorial
(including downward or descending transtentorial), tonsillar (including tonsillar descent or crowding at
the foramen magnum), external (through a craniectomy defect); use "unspecified" when herniation is
described without a subtype. Level is Present, Uncertain or Not assessable. Early, impending or at-risk
herniation is Uncertain. Leave out only subtypes that are explicitly absent or never mentioned.
chronic_isch: old or chronic infarct, encephalomalacia, gliosis, chronic small-vessel or microvascular
ischaemic change, and white-matter change the report attributes to chronic ischaemia are Present.
White-matter change the report does not attribute to ischaemia is Absent. "Likely small-vessel
disease" is Uncertain.
lvo: Present only when CTA, MRA, DSA or an explicit vessel-patency assessment shows occlusion; Absent only
when such imaging shows the vessels patent. On a study that cannot assess patency, an indirect sign such
as a hyperdense vessel is Uncertain (never Present); otherwise Not assessable (never Absent).

CHANGES
List only findings the report explicitly compares with a prior study, with direction new, increased,
stable, decreased or resolved.

EXAMPLES (generalised)
- existing haemorrhage persists, no new haemorrhage -> haem Present
- intraventricular haemorrhage decreased but still seen -> ivh Present; change ivh decreased
- chronic infarcts; a subacute component cannot be excluded -> infarct_acute Uncertain; chronic_isch Present
- no definite evidence of hydrocephalus -> hydro Absent
- possible mild oedema, limited by artefact -> oedema Uncertain
- mass effect persists, not increased -> mass_effect Present; change mass_effect stable
- cannot exclude an underlying mass -> nothing about mass_effect
- subfalcine herniation, no transtentorial herniation -> herniation [subfalcine Present]
- early uncal herniation -> herniation [uncal Uncertain]
- periventricular white-matter changes consistent with chronic small-vessel disease -> chronic_isch Present
- non-specific white-matter hypodensities -> chronic_isch Absent
- infarct described with no acuity word, nothing saying chronic -> infarct_acute Present
- subacute infarct -> infarct_acute Present
- prominent ventricles with cerebral atrophy, hydrocephalus not stated -> hydro Absent
- mild ventriculomegaly, no mention of hydrocephalus -> hydro Absent
- possible hydrocephalus -> hydro Uncertain
- downward transtentorial herniation -> herniation [transtentorial Present]
- effacement of basal cisterns with early herniation described -> herniation [unspecified Uncertain]
- non-contrast CT with a hyperdense MCA sign -> lvo Uncertain
- non-contrast CT, vessels not mentioned -> lvo Not assessable
- infarcts in the frontal and parietal lobes -> region [frontal, parietal]; territory []
- basal ganglia haematoma with intraventricular extension -> haem Present; haem_compartment [intraparenchymal]; iph_site [deep_basal_ganglia]; ivh Present
