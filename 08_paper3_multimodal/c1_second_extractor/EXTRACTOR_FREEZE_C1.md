# Second extractor — freeze record (protocol v1.3, C1.3)

**FROZEN 2 October 2026**, before the second extractor processed any MIMIC report.

From this point the second extractor is not changed, whatever the validation set shows
(C1.6 rule 6). No third model is tried (C1.6 rule 5).

## What is frozen

| | |
|---|---|
| `prompt_version` | **14f1b65dabff** |
| Model | `qwen3.8:27b-q4_K_M` — 27.3 billion parameters, Q4_K_M, 17.7 GB, family `qwen35` as reported by the runtime |
| Model digest | `25b843619e944cd0ae6069f94ff4e5e26a16e109ccbc0a66a0f05979ed70098e` |
| Runtime | Ollama 0.35.0 (Homebrew), started with `ollama serve`, default settings, `OLLAMA_HOST=127.0.0.1:11434`; runs entirely on the GPU |
| Hardware | Apple M5 Pro, 48 GB memory, macOS 26.6 |
| Generation | `temperature 0`, `seed 0`, `num_ctx 6144`, output constrained by the JSON schema — as the frozen extractor |
| Technical adaptation | `think: false` is sent. The model reports a thinking capability (values `false`, `low`, `medium`, `xhigh`; default `medium`) and accepts `false`: a test request returned no reasoning trace |
| Code | `extract_c1.py`, a wrapper that imports the frozen `extractor/extract_v12.py` and replaces the model name and the request function only |
| Prompt template, rules, schema, guards | The frozen module's own objects. `extract_v12.py` SHA-256 begins `80fa5036af76`, `rules_v1.2.md` begins `32e818a16d0d`; neither was edited, and the frozen module still reports prompt_version 0347237dd3f5 |

The wrapper's version formula is the frozen module's, with the think setting appended. Checked:
with the frozen model name and no think field it returns 0347237dd3f5.

## Model selection (C1.3)

Candidates were to be tested in the fixed order qwen3.8:27b-q4_K_M, qwen3.6:35b, qwen3.5:35b,
qwen2.5:32b-instruct-q4_K_M. **The first candidate passed both technical criteria, so no other
candidate was downloaded or run.**

Test on the four fictional reports (`extractor/fictional_test_reports.json`, no MIMIC text),
after one warm-up request that loaded the model:

| Report | Result | Attempts | Seconds | Prompt tokens | Output tokens |
|---|---|---|---|---|---|
| F1 | schema-valid | 1 | 20.3 | 2,372 | 208 |
| F2 | schema-valid | 1 | 14.7 | 2,280 | 183 |
| F3 | schema-valid | 1 | 18.4 | 2,316 | 240 |
| F4 | schema-valid | 1 | 13.7 | 2,273 | 164 |

- Criterion 1 — schema-valid output for all four, no timeout: **met** (4 of 4, first attempt).
- Criterion 2 — at most 61 s per report: **met** (mean 16.8 s).

The model's answers on the fictional reports were **not compared with the expected answers**.
Agreement plays no part in the selection (C1.3), and it was not looked at.

## Expected run time

Real reports are longer than the fictional ones. With the frozen extractor the mean time was
19.6 s on the fictional reports and 26.3 s on the analysis population, a ratio of 1.34. Applying
that ratio gives about 22.5 s per report here: roughly **1.3 hours for the 200 validation reports
and 44 hours for the 6,994 reports**. This is an estimate.

## Next step

Run the second extractor on the 200 random validation reports and score it with the scripts used
for the frozen extractor (C1.4).
