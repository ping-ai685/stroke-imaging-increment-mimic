# Neuroimaging phenotype ontology — v1.2

**Status: FROZEN, 11 September 2026** — approved by the study lead, together with
`radiology_annotation_guideline_v1.2.md` and protocol v1.2. Supersedes `protocol_v1.1/imaging_ontology_v1.1.md`.
**Date:** 11 September 2026 — before any validation annotation and before any imaging-content
result.

> The final feature set is determined solely on clinical relevance, definitional clarity
> and validated extraction reliability, **without reference to any association with the
> study outcome**. A feature may be removed because it cannot be extracted reliably. It may
> not be removed because it appears unrelated to the outcome, and no feature may be added
> because it appears strongly related to it.

## What changed from v1.1

All five changes come from the study lead's rule draft, developed on the 50 development
reports, and the decisions of 11 September 2026. None was informed by outcome data.

1. **Haemorrhage is recorded in two layers.** Layer 1, `haemorrhage_compartment` =
   intraparenchymal / subarachnoid / subdural / epidural / intraventricular, with
   intraventricular derived from its own phenotype rather than annotated twice. Layer 2,
   `iph_location`, records the anatomical site of intraparenchymal haemorrhage — lobar,
   deep / basal ganglia, thalamic, brainstem, cerebellar — so that neither the SAH / SDH / IVH
   information nor the site that matters for ICH severity is lost. Infratentorial origin, a
   component of the ICH score, is derived from layer 2 (brainstem or cerebellar).
2. **Infarct location is split into two lists.** `infarct_territory` holds vascular
   territories and is filled only when the report names one; `infarct_region` holds
   anatomical regions as stated. Neither is inferred from the other. The 50 development
   labels recorded both in a single field; they are development material and are not
   re-annotated, so development-set agreement on these two lists is only approximate.
3. **Herniation becomes a closed list of subtypes**, each with its own assertion; overall
   `herniation` is derived.
4. **`chronic_ischaemic_change` explicitly includes chronic small-vessel / microvascular
   ischaemic change** and white-matter change the report attributes to chronic ischaemia — the
   practice used on the 50 development reports. Non-specific white-matter change that the
   report does not attribute to ischaemia is not inferred to be Present.
5. **Two global wording rules are fixed** (guideline §2): a finding never mentioned is Absent,
   except one the examination cannot demonstrate (LVO on a non-vascular study), which is Not
   assessable; and "no definite X" is Absent unless the same statement carries a hedge.

## Source

Head CT and MRI reports in MIMIC-IV-Note v2.2, parenchymal brain examinations (exam names
`CT HEAD*`, `PORTABLE HEAD CT*`, `MR HEAD*`, `STROKE PROTOCOL (BRAIN*`), belonging to the
qualifying admission and stored by the 48 h landmark (protocol v1.2): 6,994 reports from
3,643 patients.

## Scales

**Assertion:** `Present` / `Absent` / `Uncertain` / `Not assessable`. Definitions and the
global wording rules are in guideline §2.

**Change over time:** `new` / `increased` / `stable` / `decreased` / `resolved` /
`not_stated`. A comparison records both the current assertion and the change; a reduction is
still Present. Change values are stored but are **not** in the primary M1 feature set.

## Fields

| # | Field | Type | Values and notes |
|---|---|---|---|
| 1 | `acute_infarction` | assertion + change | acute or subacute infarction |
| 2 | `infarct_territory` | list | `ACA`, `MCA`, `PCA`, `vertebrobasilar`, `watershed` — only when the report names the territory |
| 3 | `infarct_region` | list | `frontal`, `parietal`, `temporal`, `occipital`, `insula`, `basal_ganglia`, `thalamus`, `deep_white_matter`, `brainstem`, `cerebellum` — as stated |
| 3b | `multiple_territories` | derived | two or more entries in #2 |
| 4 | `large_territorial_infarct` | assertion + change | only when the report's wording supports it (guideline §4.3) |
| 5 | `intracranial_haemorrhage` | assertion + change | any compartment |
| 6 | `haemorrhage_compartment` | list — layer 1 | `intraparenchymal`, `subarachnoid`, `subdural`, `epidural`; `intraventricular` is derived from #8, not annotated here |
| 7 | `iph_location` | list — layer 2 | `lobar`, `deep_basal_ganglia`, `thalamic`, `brainstem`, `cerebellar` — intraparenchymal haemorrhage only, as stated |
| 7b | `infratentorial_iph` | derived | `brainstem` or `cerebellar` in #7 |
| 8 | `intraventricular_haemorrhage` | assertion + change | present while blood remains in the ventricles |
| 9 | `cerebral_oedema` | assertion + change | |
| 10 | `midline_shift_present` | assertion + change | primary representation |
| 10b | `midline_shift_mm` | number, conditional | as stated; never imputed; conflicting values within one report are flagged, not averaged; not in the primary M1 feature set |
| 11 | `hydrocephalus` | assertion + change | |
| 12 | `mass_effect` | assertion + change | a "mass" (tumour) is not mass effect |
| 13 | `herniation_subfalcine` · `herniation_uncal` · `herniation_transtentorial` · `herniation_tonsillar` · `herniation_external` · `herniation_unspecified` | assertion each | subfalcine includes parafalcine; external = through a craniectomy defect |
| 13b | `herniation` | derived | Present if any subtype is Present; otherwise Uncertain if any is Uncertain; otherwise Absent |
| 14 | `chronic_ischaemic_change` | assertion + change | old infarct, encephalomalacia, gliosis, chronic small-vessel / microvascular ischaemic change, white-matter change attributed to chronic ischaemia; non-attributed white-matter change is not Present; independent of #1 |
| 15 | `large_vessel_occlusion` | assertion + change | Present / Absent only from appropriate vessel imaging (CTA, MRA, DSA, or an explicit patency assessment); on a study that cannot assess patency: Uncertain if an indirect sign such as a hyperdense vessel is described — never Present — otherwise Not assessable, never Absent |
| — | `adjudication_flag` | per report | set when a conflict cannot be resolved by the rules (guideline §5) |

## Extraction environment

A local open-weight model on project hardware. Report text is never sent to any external
API or service (protocol §8.4).
