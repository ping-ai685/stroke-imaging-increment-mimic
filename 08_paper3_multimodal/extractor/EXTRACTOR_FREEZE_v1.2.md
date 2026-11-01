# Extractor freeze record — v1.2

**FROZEN 12 September 2026.** Protocol v1.2 §15 step 8e, amendment B6.

From this point the extractor is not changed and development rules are not revisited,
whatever the random validation set shows. Any change produces a new `prompt_version`, and the
validation would have to be repeated under a protocol amendment.

## What is frozen

| | |
|---|---|
| `prompt_version` | **0347237dd3f5** |
| Model | `qwen2.5:7b` (Q4_K_M, 4.7 GB) via Ollama 0.13.1, local |
| Generation | `temperature 0`, `seed 0`, `num_ctx 6144`, output constrained by JSON schema |
| Code | `extract_v12.py` |
| Rules in the prompt | `rules_v1.2.md` — condensed from guideline v1.2 including clarifications C1 and C2. **Do not edit: its text is hashed into `prompt_version`** |
| Deterministic post-processing | Not-assessable guard (sentence-scoped), mention guard (phenotype and list terms), LVO guard (§4.13), change cleanup, derived fields. Every application is flagged; nothing is changed silently |

## Development performance (the 50 development reports, annotator labels v2)

50/50 extracted, 0 failures, 19.1 s/report.

**Agreement 560/650 = 86.2%** (strict mapping). The seven phenotypes that enter primary M1:
**297/350 = 84.9%**. Progression across development versions: 80.3% → 84.9% → 86.2%.

| Phenotype | Agreement | In primary M1 |
|---|---|---|
| Cerebral oedema | 45/50 | yes |
| Chronic ischaemic change | 45/50 | yes |
| Midline shift | 44/50 | yes |
| Mass effect | 43/50 | yes |
| Intraventricular haemorrhage | 42/50 | yes |
| Acute/subacute infarction | 39/50 | yes |
| Intracranial haemorrhage | 39/50 | yes |
| Large territorial infarct | 45/50 | sensitivity only (B9) |
| Herniation | 43/50 | sensitivity only (B9) |
| Hydrocephalus | 38/50 | sensitivity only (B9) |
| Large-vessel occlusion | 47/50 | excluded (B9, structural) |
| Haemorrhage compartment / site | 48/50 | yes (as lists) |
| Infarct territory | 42/50 | yes (as lists) |

Development agreement is **not** the acceptance criterion. B9 is decided on the random
validation set: κ ≥ 0.60 against the primary annotator and ≥ 10 annotator positives.

## Known residual weaknesses, stated before validation

- **Acute/subacute infarction, 9 missed positives.** Not caused by the guards — they never
  fired on that field in those reports; the model itself answered Absent.
- **Hydrocephalus, 38/50**, the weakest field: 4 missed positives and 3 Absent → Uncertain.
- **Intracranial haemorrhage, 39/50**, a mix of 4 missed and 3 over-called.
- **Herniation: 6 reports downgraded to Uncertain** where the annotator said Present, and none
  of those reports contains hedging wording near the herniation sentence — a habit of the
  model, not a rule effect. The earlier failure (omitting herniation entirely) is fixed.
- `infarct_territory` looks poor against the development labels only because those labels mixed
  territory with anatomical region in one row; the validation workbook records them separately.

## Next step

Run the frozen extractor over the 200 random validation reports, compute κ per phenotype
against the annotator's labels, and apply B9. The extractor is not touched again.
