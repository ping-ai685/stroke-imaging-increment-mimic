# Local neuroimaging-report extractor

Runs `qwen2.5:7b` through Ollama **on this machine only**. Report text never leaves the
machine (protocol v1.2 §8.4); both extractors assert that the model endpoint is localhost.

**Current version: v1.2 — FROZEN 12 September 2026, prompt_version 0347237dd3f5**
(see `EXTRACTOR_FREEZE_v1.2.md`).

It implements the frozen ontology and annotation guideline v1.2, was developed on the 50
development reports only, and was frozen — model, prompt, settings and prompt_version recorded
(protocol v1.2 §15 step 8e, B6) — **before** being run on the random validation set. It is not
changed again; a change would produce a new prompt_version and invalidate the validation.

## Files

| File | Report text? | |
|---|---|---|
| `extract_v12.py` | no (code) | **the frozen extractor.** Compact JSON-schema output, deterministic post-processing (sentence-scoped Not-assessable guard, LVO guard, change cleanup, derived fields), every rule application flagged, resumable |
| `EXTRACTOR_FREEZE_v1.2.md` | no | the freeze record: version, settings, guards, development performance, known weaknesses |
| `rules_v1.2.md` | no | the rules the model sees: a condensation of guideline v1.2 with its worked examples and clarifications C1/C2. **Frozen — do not edit; its text is hashed into prompt_version.** The guideline remains normative |
| `evaluate_v12.py` | no (code) | compares v1.2 output with manual labels; counts and label-level disagreements only |
| `fictional_test_reports.json` | **no — fictional** | four reports written for pipeline testing; safe to share |
| `fictional_v12_out.jsonl` | no | v1.2 output on the fictional set |
| `dev50_v12_out.jsonl` | no — labels only | v1.2 output on the 50 development reports; MIMIC-derived identifiers, credentialed team only |
| `extract.py`, `evaluate.py` | no (code) | **v0**, v1.1 schema. Kept only to reproduce the v0 development evaluation |
| `fictional_out.jsonl`, `dev50_out.jsonl` | no | v0 outputs (prompt_version 3cc89ca9bc39) |

The **input** for a real run is a local CSV of `note_id, text` — for the development set,
`annotation_session/session_packet_REPORT_TEXT.csv` (DUA data; stays on this machine).

## Versioning

Every output record carries a `prompt_version` hash of the template, the rules, the schema
**and the post-processing source**, so changing any guard changes the version. On resume,
records from another version are dropped and re-run; results from different versions are never
mixed.

## Rules that must not be broken

- The 50 development reports may be used to develop the extractor, **never to validate it**.
- The random validation set is touched only after the extractor is frozen, and the extractor
  is never re-tuned on it (protocol v1.2 B9).
- Acceptance threshold per primary-M1 phenotype on the random set: κ ≥ 0.60 against the
  primary annotator and ≥ 10 annotator positives (B9).

## Run

```bash
python3 extract_v12.py --fictional
```

```bash
caffeinate -i python3 extract_v12.py --input ../annotation_session/session_packet_REPORT_TEXT.csv --output dev50_v12_out.jsonl
```

```bash
python3 evaluate_v12.py --output dev50_v12_out.jsonl --labels ../annotation_session/draft_labels_no_text_v2.csv
```

When the machine is idle, unload the model to free memory:

```bash
ollama stop qwen2.5:7b
```
