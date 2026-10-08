# Protocol v1.2 — clarification log

Clarifications of text already frozen. They resolve an ambiguity in wording; they do not change
any specification, and they are recorded with the date and the reasoning. A change of
specification would require `protocol_v1.3/` under §14.

---

## 2026-09-12 — how κ in B9 is computed

**The ambiguity.** B9 requires "Cohen's κ ≥ 0.60" against the primary annotator but does not say
whether κ is computed on the four-level annotation scale or on a collapsed Present-versus-Absent
binary. Both readings are defensible.

**Decision — primary.**

> Primary B9 eligibility: Cohen's κ calculated on the prespecified four-level annotation scale
> (Present / Absent / Uncertain / Not assessable). Phenotypes with κ ≥ 0.60 and ≥ 10 positive
> cases in the random validation set are eligible for the primary M1 imaging feature set.

**Decision — secondary.**

> Secondary reliability analysis: among observations with definitive human labels, collapse the
> annotation to Present vs Absent; treat Uncertain and Not assessable as missing/unknown, and
> report binary Cohen's κ and corresponding agreement statistics. These results do not alter B9
> eligibility for the primary M1 model.

**Why this reading, and when it was decided.** The four-level result was computed first and was
already known when this decision was taken; the binary result was deliberately **not** computed
until the reading had been fixed, so that the rule could not be chosen by the number it
produced. The four-level scale is the scale the annotation was actually made on, and it is the
stricter of the two readings. Adopting the more permissive reading after seeing an unfavourable
strict result would be open to being read as a data-driven threshold interpretation, whatever
its methodological merit. The study lead therefore fixed the strict reading as primary.

A consequence to state plainly: if the binary κ for a phenotype is materially higher than its
four-level κ, that phenotype is still **not** returned to the primary M1 feature set. It means
its difficulty lies in the assertion/uncertainty distinctions rather than in separating clear
positives from clear negatives — an error analysis worth reporting, not an eligibility argument.

**Not yet settled by this entry.** The list fields (`infarct_territory`, `infarct_region`,
`haemorrhage_compartment`, `iph_location`) and `midline_shift_mm` are not scored with a plain
Cohen's κ: the multi-label fields are assessed per field and per category, and the millimetre
value with a continuous agreement statistic. The primary imaging feature set is frozen only once
those are done.

---

## 2026-09-12 — the B9 threshold applied to list categories

**The gap.** B9 sets κ ≥ 0.60 and ≥ 10 annotator positives for a *phenotype*. The multi-label
list fields (`infarct_territory`, `infarct_region`, `haemorrhage_compartment`, `iph_location`)
are part of the primary M1 imaging content but B9 never states a threshold for them.

**Decision.** The same thresholds apply per list *category*: a category enters the primary M1
imaging feature set if Cohen's κ ≥ 0.60 against the primary annotator and the random validation
set holds ≥ 10 annotator-positive reports for that category.

**Why this reading.** The per-category numbers were already computed when this was decided, so
the mitigation is to reuse the existing thresholds unchanged rather than invent a rule: no new
cut-off was chosen, and the same bar that excluded four phenotypes is applied to categories.

**`midline_shift_mm` is not affected by this entry.** The frozen ontology and guideline already
hold the millimetre value and the change fields out of the primary M1 feature set; their
reliability is reported descriptively only. One annotator value of 57 mm is implausible and is
being checked by the study lead; it affects the descriptive statistic, not eligibility.
