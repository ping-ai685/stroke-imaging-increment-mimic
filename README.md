# Report-derived neuroimaging phenotypes and dynamic ICU risk after acute stroke

Analysis code for:

> Lei P, Xu Y, Zhang Y, Ray N. Dynamic risk stratification for short-term deterioration after acute stroke:
> incremental value of radiology-report-derived neuroimaging phenotypes beyond dynamic ICU states — a
> retrospective cohort study with temporal validation. *Submitted.*

The repository contains code, the analysis protocol in every version, and the prompt, rules and ontology used
to extract imaging findings from radiology reports. **It contains no data**: no patient-level tables, no
radiology report text, no note or patient identifiers, and no model fitted to MIMIC data.

## Data

MIMIC-IV v3.1 and MIMIC-IV-Note v2.2 are distributed by PhysioNet under credentialed access and may not be
redistributed. Obtain them yourself (https://physionet.org/content/mimiciv/3.1/,
https://physionet.org/content/mimic-iv-note/2.2/), then set the paths in `data_paths.cfg`
(copy `data_paths.cfg.example`). Under the PhysioNet data use agreement, report text must not be sent to
external services; the extraction here runs entirely on a local model.

## What is needed upstream

This study builds on the dynamic clinical states of an earlier study, whose code is public at
https://github.com/ping-ai685/stroke-states-mimic. Running its preprocessing (`03_code/01`–`04`, `08`) produces
the window-level tables in `04_outputs/tables/`, and its treatment-free model provides the frozen state model
in `07_paper2_eicu/frozen_params_treatment_free/`. Both are derived from MIMIC data and are therefore not
included here; place them at those paths.

## Layout

| Path | Contents |
|---|---|
| `08_paper3_multimodal/31`–`36` | State decoding (31, with the correction for time after death), real-time (filtered) states (34), landmark dataset (35), baseline models (36) |
| `08_paper3_multimodal/37`–`45` | Annotation materials, validation sample, extraction input and run |
| `08_paper3_multimodal/46`–`52` | Imaging features, primary comparison (47), sensitivity analyses (48), independent reproduction (49), redundancy (50), decision curves and calibration (51), subtypes (52) |
| `08_paper3_multimodal/53`–`68` | Manuscript number manifest and checks (58–61), figures, supplement, Word builds, TRIPOD+AI checklist |
| `08_paper3_multimodal/70`–`73` | Audit of the preprocessing inherited from the earlier study and the pipeline audit (72) |
| `08_paper3_multimodal/extractor/` | The fixed extractor (`extract_v12.py`, `rules_v1.2.md`; prompt_version 0347237dd3f5), its freeze record and evaluation scripts; four fictional test reports |
| `08_paper3_multimodal/c1_second_extractor/` | Repeated extraction with a larger model (protocol v1.3, C1): wrapper, full run, analysis, freeze record (prompt_version 14f1b65dabff) |
| `08_paper3_multimodal/protocol/` | Protocol versions 1.0–1.5 with amendment and clarification logs, ontology and annotation guideline |

## Running

Python 3.9.6; package versions in `requirements.txt`. Extraction uses Ollama on the local machine
(`qwen2.5:7b` for the primary analysis; `qwen3.8:27b-q4_K_M` for C1). The order of the full re-run is given in
protocol v1.4, Appendix D (D1.4). Script 48 must be run twice — once without arguments and once with
`--only 11 12` — to reproduce the published intervals of sensitivity analyses 11 and 12.

Notes on this public copy:

- The project path and a contact e-mail in HTTP user-agent strings were replaced: scripts locate the
  repository root from their own position, and the e-mail is a placeholder.
- Scripts 33 and 37 read intermediate files from a temporary folder that no longer exists; neither produces a
  number reported in the paper.
- Check C8b of the pipeline audit (72) compares against a pre-correction backup that is not distributed; it
  reports a failure when that backup is absent.

## Licence

MIT (see `LICENSE`).
