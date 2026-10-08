# Paper 3 — protocol v1.3

**Frozen 1 October 2026**, approved by the study lead. Supersedes v1.2; `protocol_v1.0/`,
`protocol_v1.1/` and `protocol_v1.2/` are never overwritten.

v1.3 adds **one analysis, C1, specified after the confirmatory result was observed** (16 September
2026) and after the manuscript body was locked (18 September 2026). It was frozen **before the
second extractor was installed and before it processed any report**.

## Files

| File | Role |
|---|---|
| `PROTOCOL_v1.3_EN.md` | **Normative.** v1.2 with the header, the v1.3 summary paragraph and §14 updated, plus Appendix C. Every other section is identical to v1.2 (verified by script). |
| `PROTOCOL_v1.3_CN.md` | Chinese translation. No independent content. |
| `Dynamic_risk_stratification_research_protocol_v1.3.docx` | English Word version, generated from the markdown. Regenerate rather than edit in place. |
| `急性卒中ICU动态风险分层_研究方案_v1.3_中文版.docx` | Chinese Word version, generated from the markdown. Regenerate rather than edit in place. |
| `C1_review_draft_CN_superseded.md` | The Chinese draft the study lead reviewed on 1 October 2026. Superseded by Appendix C; kept as the record of what was reviewed and what changed (the model). |

The ontology and annotation guideline are **not** re-issued: `protocol_v1.2/imaging_ontology_v1.2.md`
and `protocol_v1.2/radiology_annotation_guideline_v1.2.md` remain in force, frozen and unchanged.

## Addition in v1.3 (Appendix C)

| | Change |
|---|---|
| C1 | Post-lock robustness analysis: the confirmatory comparison repeated with imaging features extracted by a second, larger language model — same prompt, rules, settings and guards, no tuning — on the same seven features (C1-a) and on the feature set re-derived under B9 (C1-b). Reading rules fixed before running. |

## Unchanged

Everything else. In particular the confirmatory comparison (§10.1), the conclusion rule (§10.2),
the +5 percentage point benchmark (§10.3), the frozen extractor (prompt_version 0347237dd3f5) and
the primary imaging feature set. The result obtained with the frozen extractor remains the
primary result whatever C1 shows.

## Amendments

Amendments create `protocol_v1.4/`. Each records what changed, why, and whether the change was
made **before or after** the relevant result was observed. Model performance is not a ground
for amendment.
