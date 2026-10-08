# Paper 3 — protocol v1.4

**Frozen 4 October 2026**, approved by the study lead. Supersedes v1.3; `protocol_v1.0/` to
`protocol_v1.3/` are never overwritten.

v1.4 corrects **one implementation error, D1, found after every result — including C1 — had been
observed**: the risk set admitted landmarks at or after the patient's recorded death, and windows
after death entered the full-sequence decoding that adjudicates the outcome. The corrected
analyses replace the original ones. No specification changes.

## Files

| File | Role |
|---|---|
| `PROTOCOL_v1.4_EN.md` | **Normative.** v1.3 with the header, the v1.4 summary paragraph and §14 updated, plus Appendix D. Every other section is identical to v1.3 (verified by script). |
| `PROTOCOL_v1.4_CN.md` | Chinese translation. No independent content. |
| `Dynamic_risk_stratification_research_protocol_v1.4.docx` | English Word version, generated from the markdown. |
| `急性卒中ICU动态风险分层_研究方案_v1.4_中文版.docx` | Chinese Word version, generated from the markdown. |
| `D1_review_draft_CN_superseded.md` | The Chinese draft the study lead reviewed and approved on 4 October 2026; superseded by Appendix D. |

The ontology and annotation guideline remain those of `protocol_v1.2/`, unchanged.

## Amendment in v1.4 (Appendix D)

| | Change |
|---|---|
| D1 | Implementation error (§14), found after all results: landmarks at or after death removed from the risk set (script 35); windows after a death within 72 h removed before full-sequence decoding of the outcome (script 31), as in the revision of the earlier study. Everything re-run; the corrected results replace the original ones. |

## Amendments

Amendments create `protocol_v1.5/`. Each records what changed, why, and whether the change was
made **before or after** the relevant result was observed. Model performance is not a ground
for amendment.
