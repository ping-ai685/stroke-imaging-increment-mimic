"""
Paper 3: audit of the claims the design rests on that 49 and 58–61 do not already test. Runs without the
MIMIC drive. Each check is a statement from the Methods restated as something that can fail.

  C1  the real-time (filtered) state uses no future data: changing every window after L leaves the
      posterior at L unchanged (perturbation test on the frozen treatment-free model)
  C2  the state posterior entering the landmark dataset is the filtered one, at window L
  C3  predictors at landmark L are window L's values (no off-by-one into the future)
  C4  the outcome is recomputed independently from the full-sequence states and death times, row by row
  C5  every imaging report used at a landmark was stored before it and after the 72-h floor
  C6  nothing shareable (manuscript, supplement, figures, notebooks) contains radiology report text, and no
      output table outside the extractor carries a free-text column
  C7  preprocessing inside the models is fitted on the development cohort only; no hyper-parameter search
Writes audit_pipeline.txt.
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(_REPO_ROOT)
P3 = ROOT / "08_paper3_multimodal"
FROZEN = ROOT / "07_paper2_eicu" / "frozen_params_treatment_free"
LOG = []


def check(name, ok, detail=""):
    LOG.append(f"{'OK ' if ok else 'BAD'}  {name}" + (f"\n       {detail}" if detail else ""))
    print(LOG[-1])


wide = pd.read_csv(ROOT / "04_outputs/tables/timewindow_level_modeling.csv").sort_values(["stay_id", "window_idx"])
FEATURES = pd.read_csv(FROZEN / "feature_order.csv").sort_values("position").feature.tolist()
model = torch.load(FROZEN / ".model_k4_treatment_free.pt", weights_only=False)


def posterior(X):
    with torch.no_grad():
        a = model.forward(torch.tensor(X, dtype=torch.float32).unsqueeze(0))[0].numpy()
    p = np.exp(a - a.max(axis=1, keepdims=True))
    return p / p.sum(axis=1, keepdims=True)


# ---------------------------------------------------------------- C1 perturbation test
rng = np.random.default_rng(20260918)
groups = {s: g[FEATURES].to_numpy() for s, g in wide.groupby("stay_id") if len(g) >= 10}
sample = rng.choice(list(groups), 300, replace=False)
donors = list(groups)
worst, tests = 0.0, 0
for s in sample:
    X = groups[s]
    base = posterior(X)
    for L in range(0, 8):
        Xp = X.copy()
        donor = groups[donors[rng.integers(len(donors))]]
        n = len(X) - (L + 1)
        Xp[L + 1:] = donor[:n] if len(donor) >= n else rng.normal(0, 3, size=(n, X.shape[1]))
        worst = max(worst, float(np.abs(posterior(Xp)[L] - base[L]).max())); tests += 1
check("C1 filtered posterior at L is unchanged when all windows after L are replaced",
      worst < 1e-6, f"{tests} perturbations on 300 stays; largest change {worst:.2e}")
# and the full-sequence decoding is NOT causal (so the test can detect leakage when it exists)
changed = 0
for s in sample[:100]:
    X = groups[s]
    base = model.predict(torch.tensor(X, dtype=torch.float32).unsqueeze(0))[0].numpy()
    Xp = X.copy(); Xp[3:] = rng.normal(0, 3, size=(len(X) - 3, X.shape[1]))
    alt = model.predict(torch.tensor(Xp, dtype=torch.float32).unsqueeze(0))[0].numpy()
    changed += int(alt[2] != base[2])
check("C1b the same test does detect future dependence in full-sequence decoding (positive control)",
      changed > 0, f"state at window 2 changed in {changed} of 100 stays when windows 3+ were replaced")

# ---------------------------------------------------------------- C2 / C3 alignment
lm = pd.read_csv(P3 / "landmark_dataset.csv")
filt = pd.read_csv(P3 / "tf_filtered_states.csv")
m = lm.merge(filt, left_on=["stay_id", "landmark_idx"], right_on=["stay_id", "window_idx"], suffixes=("", "_f"),
             validate="one_to_one")
diff = max(float((m[f"p_state{k}"] - m[f"p_state{k}_f"]).abs().max()) for k in range(4))
check("C2 landmark state posteriors equal the filtered posteriors at window L", diff < 1e-9 and len(m) == len(lm),
      f"{len(m)} rows, max difference {diff:.1e}")
check("C2b landmark time is the end of window L (6(L+1) h)", (lm.landmark_h == 6 * (lm.landmark_idx + 1)).all())
W = wide.set_index(["stay_id", "window_idx"])
zc = [c for c in lm.columns if c.endswith("_z")] + ["mech_vent", "crrt", "vasopressor", "sedative"]
w_at = W.loc[list(zip(lm.stay_id, lm.landmark_idx)), zc].to_numpy()
w_next = W.reindex(list(zip(lm.stay_id, lm.landmark_idx + 1)))[zc].to_numpy()
same_L = np.allclose(lm[zc].to_numpy(), w_at, equal_nan=True)
frac_next = float(np.nanmean(np.all(np.isclose(lm[zc].to_numpy(), w_next, equal_nan=True), axis=1)))
check("C3 all 21 physiology/treatment predictors at landmark L are window L's values", same_L,
      f"{len(zc)} columns × {len(lm)} rows; identical to window L+1 in {100*frac_next:.1f}% of rows (should be ~0)")

# ---------------------------------------------------------------- C4 outcome recomputation
coh = pd.read_csv(ROOT / "04_outputs/tables/patient_level_cohort.csv", parse_dates=["intime", "outtime", "deathtime"])
coh["death_h"] = (coh.deathtime - coh.intime).dt.total_seconds() / 3600
coh["end_h"] = (coh.outtime - coh.intime).dt.total_seconds() / 3600
C = coh.set_index("stay_id")
tf = pd.read_csv(P3 / "tf_state_assignments_all.csv")
S = dict(zip(zip(tf.stay_id, tf.window_idx), tf.tf_state))
adv, died, left = [], [], []
for r in lm.itertuples():
    T = r.landmark_h
    a = any(S.get((r.stay_id, k)) == 0 for k in range(r.landmark_idx + 1, r.landmark_idx + 5))
    dh = C.at[r.stay_id, "death_h"]
    d = bool(pd.notna(dh) and T <= dh < T + 24)
    adv.append(a); died.append(d); left.append(bool(C.at[r.stay_id, "end_h"] < T + 24 and not d))
adv, died, left = np.array(adv), np.array(died), np.array(left)
check("C4 24-h deterioration recomputed from full-sequence states matches the dataset",
      (adv == lm.future_24h_adverse.astype(bool)).all(), f"mismatches {int((adv != lm.future_24h_adverse.astype(bool)).sum())}")
check("C4b death within 24 h recomputed matches", (died == lm.future_24h_death.astype(bool)).all())
check("C4c composite = deterioration or death", ((adv | died) == lm.composite_event.astype(bool)).all())
check("C4d alive ICU discharge within 24 h without deterioration is never an event",
      not (left & ~adv & ~died & lm.composite_event.astype(bool)).any())

# ---------------------------------------------------------------- C5 report timing
idx = pd.read_csv(P3 / "analysis_population_index.csv")
feat = pd.read_csv(P3 / "landmark_imaging_features.csv")
a = feat[feat.img_available_locked == 1]
check("C5 every report used at a landmark was stored before the landmark (age ≥ 0)",
      (a.img_report_age_h >= 0).all(), f"min age {a.img_report_age_h.min():.2f} h over {len(a)} landmarks")
lm_n = lm[lm.note_era].merge(feat[["stay_id", "landmark_idx", "img_report_age_h"]], on=["stay_id", "landmark_idx"])
stored = lm_n.landmark_h - lm_n.img_report_age_h
check("C5b no report stored more than 72 h before ICU admission was used", (stored.dropna() >= -72 - 1e-9).all(),
      f"earliest storetime used {stored.min():.1f} h from ICU admission")

# ---------------------------------------------------------------- C6 no report text anywhere shareable
HEAD = re.compile(r"\b(FINDINGS|IMPRESSION|EXAMINATION|INDICATION|TECHNIQUE|COMPARISON|HISTORY)\s*:", re.I)
share = [p for d in ["manuscript", "figures", "notebooks"] for p in (P3 / d).rglob("*")
         if p.is_file() and p.suffix in {".md", ".json", ".csv", ".txt", ".ipynb", ".html"}]
share += sorted(P3.glob("AUDIT_REPORT*.md"))
hits = []
for p in share:
    t = p.read_text(encoding="utf-8", errors="ignore")
    if HEAD.search(t):
        hits.append(str(p.relative_to(P3)))
import zipfile
for p in [q for dd in ["manuscript", "notebooks"] for q in (P3 / dd).rglob("*.docx")]:
    t = zipfile.ZipFile(p).read("word/document.xml").decode("utf-8", "ignore")
    if HEAD.search(re.sub(r"<[^>]+>", " ", t)):
        hits.append(str(p.relative_to(P3)))
check("C6 no report section headers in manuscript, supplement, figures or notebooks", not hits,
      f"{len(share)} text files and the .docx files scanned; hits: {hits}")
long_text = []
for p in P3.glob("*.csv"):
    if p.name in {"analysis_population_input.csv"}:          # the extraction input: report text by design, local only
        continue
    df = pd.read_csv(p, nrows=500)
    for c in df.select_dtypes("object"):
        if df[c].astype(str).str.len().max() > 200:
            long_text.append(f"{p.name}:{c}")
check("C6b no analysis output table carries a free-text column (report text stays in the extraction input)",
      not long_text, long_text)

# ---------------------------------------------------------------- C7 fitting discipline
s47 = (P3 / "47_m1_models.py").read_text(); s36 = (P3 / "36_m0_baseline_models.py").read_text()
check("C7 model pipelines are fitted on the development cohort only",
      "m.fit(dev[cols], dev.composite_event)" in s47 and "m.fit(dev[cols], dev.composite_event)" in s36)
check("C7b no hyper-parameter search: one fixed penalty (C = 1.0), no CV/grid search in 36/47",
      not re.search(r"GridSearch|RandomizedSearch|cross_val|LogisticRegressionCV", s36 + s47))

# ---------------------------------------------------------------- C8 alive at the landmark (protocol v1.4, D1)
def after_death(frame):
    m_ = frame.merge(coh[["stay_id", "death_h"]], on="stay_id", how="left")
    return int((m_.death_h.notna() & (m_.death_h <= m_.landmark_h)).sum())


check("C8 no landmark lies at or after the patient's recorded death (protocol v1.4, D1)",
      after_death(lm) == 0, f"{after_death(lm)} of {len(lm)} landmarks at or after death")
_pre = Path.home() / "Desktop" / "migration_m5" / "paper3_backup_before_D1_2026-10-04" / "08_paper3_multimodal" / "landmark_dataset.csv"
if _pre.exists():
    _n = after_death(pd.read_csv(_pre, usecols=["stay_id", "landmark_h"]))
    check("C8b the same test does detect landmarks after death in the uncorrected dataset (positive control)",
          _n > 0, f"{_n} landmarks at or after death before the correction")
else:
    check("C8b positive control: uncorrected dataset not found at the backup location", False, str(_pre))
_tf = pd.read_csv(P3 / "tf_state_assignments_all.csv").merge(coh[["stay_id", "death_h"]], on="stay_id")
_tf = _tf[_tf.death_h.notna() & (_tf.death_h < 72)]
check("C8c no window after the one containing a death within 72 h enters the outcome decoding (D1)",
      not (_tf.window_idx > (_tf.death_h // 6)).any())

bad = sum(l.startswith("BAD") for l in LOG)
(P3 / "audit_pipeline.txt").write_text("\n".join(LOG) + f"\n\n{len(LOG)} checks, {bad} failed\n", encoding="utf-8")
print(f"\n{len(LOG)} checks, {bad} failed")
