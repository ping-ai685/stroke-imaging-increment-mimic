"""
Paper 3: independent reproduction of the confirmatory result.

Written without importing 46_merge_imaging_features.py, 47_m1_models.py or
48_sensitivity_analyses.py, and using a different algorithm at each step where one exists, so that
an error in the analysis code cannot be reproduced here by construction:

  features   pandas merge_asof (most recent report at or before the landmark) and cumulative
             maxima for the static findings — not a per-landmark loop
  ranking    numpy lexsort on positions — not DataFrame.nlargest and label lookups
  bootstrap  positional indices, and a DIFFERENT seed from the analysis, so the interval is also
             checked for sensitivity to the random draw

It re-implements the specification — protocol §8.1, §8.2 and the rule locked 16 Sep 2026, §10.1 —
from the text, not from the analysis scripts. Both implementations use scikit-learn's logistic
regression; the library is shared, the code is not.

Reproduced: the locked feature table cell by cell; M0+A and M1-D AUROC; the confirmatory point
estimate; its patient-level clustered bootstrap interval.
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

P3 = _REPO_ROOT + "/08_paper3_multimodal"
SEED = 7                    # deliberately not the analysis seed (20260917)
REPS = 2000
FLOOR = -72.0

ASSERT = {"haem_present": "intracranial_haemorrhage",
          "ivh_present": "intraventricular_haemorrhage",
          "mls_present": "midline_shift_present"}
FEATURES = ["haem_present", "ivh_present", "mls_present", "haem_intraparenchymal",
            "haem_subarachnoid", "infarct_mca", "infarct_cerebellum"]


# ------------------------------------------------------------------------------ 1. features
def level(v):
    return {"Present": 1.0, "Absent": 0.0}.get(v, np.nan)


rows = []
with open(f"{P3}/extractor/analysis_population_out.jsonl", encoding="utf-8") as fh:
    for line in fh:
        if not line.strip():
            continue
        r = json.loads(line)
        if r["error"]:
            continue
        x = r["record"]
        comp = x["haemorrhage_compartment"] or []
        haem_unk = x["intracranial_haemorrhage"] not in ("Present", "Absent")
        rows.append({
            "note_id": r["note_id"],
            **{k: level(x[v]) for k, v in ASSERT.items()},
            "haem_intraparenchymal": np.nan if haem_unk else float("intraparenchymal" in comp),
            "haem_subarachnoid": np.nan if haem_unk else float("subarachnoid" in comp),
            "mca_listed": float("MCA" in (x["infarct_territory"] or [])),
            "cerebellum_listed": float("cerebellum" in (x["infarct_region"] or [])),
            "infarct_unknown": float(x["acute_infarction"] not in ("Present", "Absent")),
        })
rep = pd.DataFrame(rows)
idx = pd.read_csv(f"{P3}/analysis_population_index.csv")
rep = rep.merge(idx[["note_id", "stay_id", "hours_from_icu_admission"]], on="note_id",
                validate="one_to_one")
rep = rep[rep.hours_from_icu_admission >= FLOOR].sort_values(["stay_id", "hours_from_icu_admission"])

# static findings: ever listed up to and including this report; unknown only if every report so
# far had an unknown infarct assertion and none listed the category
g = rep.groupby("stay_id")
for name, col in (("infarct_mca", "mca_listed"), ("infarct_cerebellum", "cerebellum_listed")):
    ever = g[col].cummax()
    all_unk = g["infarct_unknown"].cummin()
    rep[name] = np.where(ever == 1, 1.0, np.where(all_unk == 1, np.nan, 0.0))

lm = pd.read_csv(f"{P3}/landmark_dataset.csv")
lm = lm[lm.note_era].copy()
lm["landmark_h"] = lm.landmark_h.astype(float)
rep["hours_from_icu_admission"] = rep.hours_from_icu_admission.astype(float)
asof = pd.merge_asof(lm.sort_values("landmark_h"),
                     rep[["stay_id", "hours_from_icu_admission"] + FEATURES]
                     .sort_values("hours_from_icu_admission"),
                     left_on="landmark_h", right_on="hours_from_icu_admission",
                     by="stay_id", direction="backward")
asof["avail"] = asof.hours_from_icu_admission.notna().astype(int)

locked = pd.read_csv(f"{P3}/landmark_imaging_features.csv",
                     usecols=["stay_id", "landmark_idx", "img_available_locked"] + FEATURES)
cmp = asof.merge(locked, on=["stay_id", "landmark_idx"], suffixes=("", "_locked"),
                 validate="one_to_one")
print("1. FEATURES — independent construction against the locked table")
print(f"   landmark rows {len(cmp)} | availability agrees "
      f"{int((cmp.avail == cmp.img_available_locked).sum())}/{len(cmp)}")
bad = 0
for c in FEATURES:
    a, b = cmp[c], cmp[f"{c}_locked"]
    same = ((a == b) | (a.isna() & b.isna())).sum()
    bad += len(cmp) - same
    print(f"   {c:24s} cells agree {same}/{len(cmp)}")
print(f"   → {'IDENTICAL' if bad == 0 and (cmp.avail == cmp.img_available_locked).all() else 'DIFFERENT'}")

# ------------------------------------------------------------------------------- 2. models
d = asof
q = d[[f"p_state{k}" for k in range(4)]].to_numpy().clip(1e-6, 1)
X = pd.DataFrame({
    "age": d.age, "male": (d.gender == "M").astype(float), "charlson": d.charlson,
    "hypertension": d.hypertension, "diabetes": d.diabetes, "af": d.atrial_fibrillation,
    "hf": d.heart_failure, "ckd": d.ckd,
    "ich": (d.stroke_subtype == "ICH").astype(float), "sah": (d.stroke_subtype == "SAH").astype(float),
    "lm": d.landmark_h / 48.0,
    "s0": np.log(q[:, 0] / q[:, 1]), "s2": np.log(q[:, 2] / q[:, 1]), "s3": np.log(q[:, 3] / q[:, 1]),
    "entropy": d.state_entropy,
})
for c in ["heart_rate_z", "sbp_z", "map_z", "resp_rate_z", "spo2_z", "temp_c_z", "gcs_eye_z",
          "gcs_motor_z", "urine_output_ml_z", "wbc_z", "hemoglobin_z", "platelet_z",
          "creatinine_z", "bun_z", "sodium_z", "potassium_z", "glucose_z",
          "mech_vent", "crrt", "vasopressor", "sedative", "img_available"]:
    X[c] = d[c]
base_cols = list(X.columns)
for c in FEATURES:
    X[f"{c}+"] = (d[c] == 1).astype(float)
    X[f"{c}?"] = d[c].isna().astype(float)
img_cols = [c for c in X.columns if c not in base_cols]

y = d.composite_event.to_numpy()
is_val = (d.anchor_year_group == "2017 - 2019").to_numpy()


def fit_predict(cols):
    sc = StandardScaler().fit(X.loc[~is_val, cols])
    m = LogisticRegression(max_iter=4000, C=1.0).fit(sc.transform(X.loc[~is_val, cols]), y[~is_val])
    return m.predict_proba(sc.transform(X.loc[is_val, cols]))[:, 1]


p0 = fit_predict(base_cols)
p1 = fit_predict(base_cols + img_cols)
yv = y[is_val]
lmv = d.landmark_h.to_numpy()[is_val]
stay = d.stay_id.to_numpy()[is_val]
print(f"\n2. MODELS — validation {is_val.sum()} landmarks, {int(yv.sum())} events, "
      f"{base_cols.__len__()} + {len(img_cols)} predictors")
print(f"   AUROC M0+A {roc_auc_score(yv, p0):.3f}   M1-D {roc_auc_score(yv, p1):.3f}   "
      f"(analysis: 0.850 / 0.855)")


# ------------------------------------------------------------------ 3. confirmatory estimand
def capture(pos, score):
    """Top 10% within each landmark, by position; capture = selected events / all events."""
    L, s, e = lmv[pos], score[pos], yv[pos]
    order = np.lexsort((-s, L))                    # by landmark, then descending score
    L, e = L[order], e[order]
    starts = np.r_[0, np.flatnonzero(np.diff(L)) + 1]
    sizes = np.diff(np.r_[starts, len(L)])
    rank = np.arange(len(L)) - np.repeat(starts, sizes)
    k = np.maximum(1, np.round(sizes * 0.10)).astype(int)
    chosen = rank < np.repeat(k, sizes)
    return 100 * e[chosen].sum() / e.sum()


allpos = np.arange(len(yv))
obs = capture(allpos, p1) - capture(allpos, p0)

rng = np.random.default_rng(SEED)
patients, inverse = np.unique(stay, return_inverse=True)
members = [np.flatnonzero(inverse == i) for i in range(len(patients))]
diffs = []
for _ in range(REPS):
    pos = np.concatenate([members[i] for i in rng.integers(0, len(patients), len(patients))])
    if yv[pos].min() == yv[pos].max():
        continue
    diffs.append(capture(pos, p1) - capture(pos, p0))
lo, hi = np.percentile(diffs, [2.5, 97.5])

print(f"\n3. CONFIRMATORY — ΔCapture(10%), M1-D vs M0+A, seed {SEED}, {len(diffs)} replicates")
print(f"   point estimate {obs:+.3f} pp        (analysis: +0.000, protocol v1.4 D1)")
print(f"   95% CI [{lo:+.2f}, {hi:+.2f}]        (analysis: [-2.20, +2.01], seed 20260917)")
print(f"   interval {'includes' if lo <= 0 <= hi else 'EXCLUDES'} zero; "
      f"upper bound {'below' if hi < 5 else 'AT OR ABOVE'} the +5 pp benchmark")
