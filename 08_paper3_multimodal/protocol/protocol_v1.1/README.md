# Paper 3 — protocol v1.1

**Frozen 11 September 2026.** Supersedes v1.0. `protocol_v1.0/` is never
overwritten and remains as the record of what was true at the first freeze.

Frozen **before M1-D and M1-I were fitted**. M0-state, M0-full and M0+A were
fitted under v1.0 and are unchanged by this version; no imaging feature had been
extracted and no imaging-related result had been observed when these amendments
were made.

## Files

| File | Role |
|---|---|
| `PROTOCOL_v1.1_EN.md` | **Normative.** Protocol and statistical analysis plan. Appendix A is the amendment log. |
| `PROTOCOL_v1.1_CN.md` | Chinese translation. No independent content. |
| `Dynamic_risk_stratification_research_protocol_v1.1.docx` | English Word version, generated from the markdown. Regenerate rather than edit in place. |
| `急性卒中ICU动态风险分层_研究方案_v1.1_中文版.docx` | Chinese Word version, generated from the markdown. Regenerate rather than edit in place. |
| `imaging_ontology_v1.1.md` | Phenotype ontology: assertion scale, multi-label territory, acute/chronic split, conditional midline-shift measurement, change-over-time scale. |
| `radiology_annotation_guideline_v1.1.md` | Annotation rules. Framework decided; phenotype-specific lexical detail still open, to be settled at the rule-discovery session. |

## What changed from v1.0

Four amendments, A–D, all before any imaging result. Full log in Appendix A of the
protocol.

- **A** — the data-handling boundary becomes a protocol provision (§8.4): all work
  on raw report text happens in a DUA-compliant local environment, and report text
  never reaches an external LLM API or anyone outside the credentialed team.
- **B** — the positive-enriched validation set becomes **conditional** on the
  annotated random set (§11), instead of being pre-assigned to six named findings.
  Mention rate is not positive prevalence, and a large share of mentions are
  negations, so only the annotated random set can settle whether enrichment is
  needed. Never triggered by association with the outcome.
- **C** — the assertion framework (Present / Absent / Uncertain / Not assessable),
  binary-primary midline shift with a never-imputed conditional measurement, and
  the both-state-and-change rule for comparison statements (§8.1).
- **D** — §15 refined into the measurement chain: rule session → guideline and
  ontology freeze → random annotation → conditional enrichment → extractor freeze
  → full run over all 20,947 tier-A reports → only then M1.

## Unchanged

The confirmatory comparison (§10.1) is untouched: M1-D versus M0+A, temporal
validation 2017–2019, pooled across all eight landmarks, ranking within each
landmark, top 10% of predicted risk, difference in 24-hour event capture,
patient-level clustered bootstrap 95% CI. Interpreted against the +5 percentage
point benchmark (§10.3) and the conclusion rule at §10.2.

## Amendments

Amendments create `protocol_v1.2/`. Each records what changed, why, and whether
the change was made **before or after** the relevant result was observed. Model
performance is not a ground for amendment.
