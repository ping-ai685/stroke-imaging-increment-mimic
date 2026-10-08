# Paper 3 — protocol v1.2

**Frozen 11 September 2026**, approved by the study lead. Supersedes v1.1; `protocol_v1.0/`
and `protocol_v1.1/` are never overwritten.

Frozen **before any validation annotation, before the extractor is frozen, and before M1-D
and M1-I are fitted**. M0-state and M0-full are unchanged; M0+A was re-fitted after the
correction in B3 and its null result stands.

## Files

| File | Role |
|---|---|
| `PROTOCOL_v1.2_EN.md` | **Normative.** Protocol and statistical analysis plan. Appendix B is the v1.1 → v1.2 amendment log. |
| `PROTOCOL_v1.2_CN.md` | Chinese translation. No independent content. |
| `Dynamic_risk_stratification_research_protocol_v1.2.docx` | English Word version, generated from the markdown. Regenerate rather than edit in place. |
| `急性卒中ICU动态风险分层_研究方案_v1.2_中文版.docx` | Chinese Word version, generated from the markdown. Regenerate rather than edit in place. |
| `imaging_ontology_v1.2.md` | **Frozen.** Phenotype fields and categories. |
| `radiology_annotation_guideline_v1.2.md` | **Frozen.** Annotation rules: global rules G1–G9, 13 phenotype sections, adjudication, template. Post-freeze clarifications go in its §9. |

## Amendments in v1.2 (Appendix B)

| | Change |
|---|---|
| B1 | Primary annotator: the study lead |
| B2 | 20% dual read deferred until a second credentialed reader exists |
| B3 | Imaging-availability implementation error corrected (1,177 admission-linked pre-admission reports had been dropped) |
| B4 | Extraction run and validation sample restricted to the analysis population: 6,994 qualifying-admission reports stored by 48 h |
| B5 | A finding never mentioned is Absent; LVO on a non-vascular study is Not assessable, Uncertain with an indirect sign, never Present |
| B6 | Extractor model, prompt, settings and prompt_version recorded at extractor freeze |
| B7 | ECG and echo availability: open, to be examined before either exploratory analysis |
| B8 | Ontology and guideline v1.2 |
| B9 | Extraction acceptance threshold: κ ≥ 0.60 and ≥ 10 annotator positives on the random set |

## Unchanged

The confirmatory comparison (§10.1) — M1-D versus M0+A, temporal validation 2017–2019, pooled
across all eight landmarks, ranking within each landmark, top 10% of predicted risk, difference
in 24-hour event capture, patient-level clustered bootstrap 95% CI — together with the
conclusion rule (§10.2) and the +5 percentage point benchmark (§10.3). Verified identical to
v1.1 by script.

## Amendments

Amendments create `protocol_v1.3/`. Each records what changed, why, and whether the change was
made **before or after** the relevant result was observed. Model performance is not a ground
for amendment.
