"""
Paper 3: POST HOC redundancy analysis. Not in the protocol; declared in PROJECT_LOG.md before it
was run (16 Sep 2026). Explanatory only — it cannot replace or qualify the §10.1 result.

Question: is the primary null because the report-derived imaging features carry no risk-ranking
signal, or because what they carry is already absorbed by what is known at the landmark?

The same imaging block is added to four increasingly rich baselines:
  B1  fixed covariates + img_available
  B2  B1 + filtered state posterior and entropy
  B3  B2 + GCS eye and motor
  B4  B2 + all physiology and treatment  (= M0+A; must reproduce the confirmatory +0.000 pp, protocol v1.4 D1)

Reading rule, fixed before running: a clearly positive increment at B1 that shrinks to ~0 by B4
means the signal exists and is absorbed; an increment already ~0 at B1 means no ranking signal;
shrinkage concentrated at B2 -> B3 points to GCS as the principal absorber.

Uses the positional ranking and bootstrap of the independent reproduction (a fresh copy, so that
script stays independent), with the analysis seed.
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

P3 = _REPO_ROOT + "/08_paper3_multimodal"
SEED = 20260917
REPS = 2000
FEATURES = ["haem_present", "ivh_present", "mls_present", "haem_intraparenchymal",
            "haem_subarachnoid", "infarct_mca", "infarct_cerebellum"]
LABEL = {"haem_present": "Intracranial haemorrhage", "ivh_present": "Intraventricular haemorrhage",
         "mls_present": "Midline shift", "haem_intraparenchymal": "Compartment: intraparenchymal",
         "haem_subarachnoid": "Compartment: subarachnoid", "infarct_mca": "Territory: MCA",
         "infarct_cerebellum": "Region: cerebellum"}

d = pd.read_csv(f"{P3}/landmark_dataset.csv")
d = d[d.note_era].copy()
f = pd.read_csv(f"{P3}/landmark_imaging_features.csv",
                usecols=["stay_id", "landmark_idx", "img_available_locked"] + FEATURES)
n0 = len(d)
d = d.merge(f, on=["stay_id", "landmark_idx"], how="left", validate="one_to_one")
assert len(d) == n0

q = d[[f"p_state{k}" for k in range(4)]].to_numpy().clip(1e-6, 1)
X = pd.DataFrame(index=d.index)
FIXED = ["age", "charlson", "hypertension", "diabetes", "atrial_fibrillation", "heart_failure", "ckd"]
for c in FIXED:
    X[c] = d[c]
X["male"] = (d.gender == "M").astype(float)
X["ich"] = (d.stroke_subtype == "ICH").astype(float)
X["sah"] = (d.stroke_subtype == "SAH").astype(float)
X["lm"] = d.landmark_h / 48.0
X["img_available"] = d.img_available
for k in (0, 2, 3):
    X[f"s{k}"] = np.log(q[:, k] / q[:, 1])
X["entropy"] = d.state_entropy
GCS = ["gcs_eye_z", "gcs_motor_z"]
OTHER = ["heart_rate_z", "sbp_z", "map_z", "resp_rate_z", "spo2_z", "temp_c_z",
         "urine_output_ml_z", "wbc_z", "hemoglobin_z", "platelet_z", "creatinine_z", "bun_z",
         "sodium_z", "potassium_z", "glucose_z", "mech_vent", "crrt", "vasopressor", "sedative"]
for c in GCS + OTHER:
    X[c] = d[c]
IMG = []
for c in FEATURES:
    X[f"{c}+"] = (d[c] == 1).astype(float)
    X[f"{c}?"] = d[c].isna().astype(float)
    IMG += [f"{c}+", f"{c}?"]

B1 = FIXED + ["male", "ich", "sah", "lm", "img_available"]
B2 = B1 + ["s0", "s2", "s3", "entropy"]
B3 = B2 + GCS
B4 = B2 + GCS + OTHER
BASES = {"B1 fixed + acquisition": B1, "B2 + dynamic state": B2,
         "B3 + GCS": B3, "B4 + all physiology (M0+A)": B4}

y = d.composite_event.to_numpy()
val = (d.anchor_year_group == "2017 - 2019").to_numpy()
yv, lmv, stay = y[val], d.landmark_h.to_numpy()[val], d.stay_id.to_numpy()[val]


def fit_predict(cols):
    sc = StandardScaler().fit(X.loc[~val, cols])
    m = LogisticRegression(max_iter=4000, C=1.0).fit(sc.transform(X.loc[~val, cols]), y[~val])
    return m.predict_proba(sc.transform(X.loc[val, cols]))[:, 1]


def capture(pos, score):
    L, s, e = lmv[pos], score[pos], yv[pos]
    order = np.lexsort((-s, L))
    L, e = L[order], e[order]
    starts = np.r_[0, np.flatnonzero(np.diff(L)) + 1]
    sizes = np.diff(np.r_[starts, len(L)])
    rank = np.arange(len(L)) - np.repeat(starts, sizes)
    chosen = rank < np.repeat(np.maximum(1, np.round(sizes * 0.10)).astype(int), sizes)
    return 100 * e[chosen].sum() / e.sum()


patients, inverse = np.unique(stay, return_inverse=True)
members = [np.flatnonzero(inverse == i) for i in range(len(patients))]
allpos = np.arange(len(yv))

print("POST HOC — declared in PROJECT_LOG.md before running; explanatory only\n")
print(f"validation {len(yv)} landmarks, {int(yv.sum())} events; seed {SEED}, {REPS} replicates\n")
print(f"{'base':28s} {'AUROC base':>10} {'+img':>7} {'ΔAUROC [95% CI]':>24} "
      f"{'capture base':>12} {'+img':>6} {'ΔCapture pp [95% CI]':>26}")
rows = []
rng = np.random.default_rng(SEED)
for name, cols in BASES.items():
    p0, p1 = fit_predict(cols), fit_predict(cols + IMG)
    c0, c1 = capture(allpos, p0), capture(allpos, p1)
    a0, a1 = roc_auc_score(yv, p0), roc_auc_score(yv, p1)
    dc, da = [], []
    for _ in range(REPS):
        pos = np.concatenate([members[i] for i in rng.integers(0, len(patients), len(patients))])
        if yv[pos].min() == yv[pos].max():
            continue
        dc.append(capture(pos, p1) - capture(pos, p0))
        da.append(roc_auc_score(yv[pos], p1[pos]) - roc_auc_score(yv[pos], p0[pos]))
    clo, chi = np.percentile(dc, [2.5, 97.5])
    alo, ahi = np.percentile(da, [2.5, 97.5])
    rows.append({"base": name, "n_predictors_base": len(cols), "auroc_base": a0, "auroc_img": a1,
                 "d_auroc": a1 - a0, "d_auroc_lo": alo, "d_auroc_hi": ahi,
                 "capture_base": c0, "capture_img": c1, "d_capture": c1 - c0,
                 "d_capture_lo": clo, "d_capture_hi": chi})
    print(f"{name:28s} {a0:>10.3f} {a1:>7.3f} {a1-a0:>+8.3f} [{alo:+.3f}, {ahi:+.3f}] "
          f"{c0:>12.1f} {c1:>6.1f} {c1-c0:>+8.2f} [{clo:+6.2f}, {chi:+6.2f}]")

b4 = rows[-1]["d_capture"]
print(f"\ncheck: B4 reproduces the confirmatory point estimate: {b4:+.3f} pp "
      f"({'OK' if abs(b4 - 0.000) < 0.001 else 'MISMATCH'})")

print("\ncrude association among imaged validation landmarks (descriptive):")
im = d[val & (d.img_available_locked == 1).to_numpy()]
print(f"  {len(im)} landmarks, overall event rate {100*im.composite_event.mean():.1f}%")
print(f"  {'feature':32s} {'n pos':>6} {'rate pos':>9} {'n neg':>6} {'rate neg':>9} {'ratio':>6}")
desc = []
for c in FEATURES:
    pos, neg = im[im[c] == 1], im[im[c] == 0]
    rp, rn = pos.composite_event.mean(), neg.composite_event.mean()
    desc.append({"feature": LABEL[c], "n_pos": len(pos), "rate_pos": rp, "n_neg": len(neg),
                 "rate_neg": rn, "ratio": rp / rn})
    print(f"  {LABEL[c]:32s} {len(pos):>6} {100*rp:>8.1f}% {len(neg):>6} {100*rn:>8.1f}% {rp/rn:>6.2f}")

print("\nGCS motor (z) by feature among imaged validation landmarks — lower is worse:")
for c in FEATURES:
    print(f"  {LABEL[c]:32s} positive {im[im[c] == 1].gcs_motor_z.mean():+.2f}   "
          f"negative {im[im[c] == 0].gcs_motor_z.mean():+.2f}")

pd.DataFrame(rows).to_csv(f"{P3}/redundancy_posthoc.csv", index=False)
pd.DataFrame(desc).to_csv(f"{P3}/redundancy_posthoc_crude.csv", index=False)
print("\nSaved: redundancy_posthoc.csv, redundancy_posthoc_crude.csv")
