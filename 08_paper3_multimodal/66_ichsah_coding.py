"""
Paper 3: the primary comparison under the two codings of the 16 patients with both ICH and SAH.

36/47 coded stroke subtype as sub_ICH = (subtype == "ICH"), sub_SAH = (subtype == "SAH"), which places
ICH+SAH in the reference category with AIS. The study lead decided (16 Sep 2026) not to re-run the
pipeline and to report the corrected coding in the supplement. This script is that supplementary result,
made reproducible: the positional implementation of 49, same seed and replicates as the analysis.
Writes ichsah_coding_sensitivity.csv.
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

P3 = _REPO_ROOT + "/08_paper3_multimodal"
SEED, REPS = 20260917, 2000
FEAT = ["haem_present", "ivh_present", "mls_present", "haem_intraparenchymal", "haem_subarachnoid",
        "infarct_mca", "infarct_cerebellum"]

d = pd.read_csv(f"{P3}/landmark_dataset.csv"); d = d[d.note_era].copy()
d = d.merge(pd.read_csv(f"{P3}/landmark_imaging_features.csv", usecols=["stay_id", "landmark_idx"] + FEAT),
            on=["stay_id", "landmark_idx"], how="left", validate="one_to_one")
q = d[[f"p_state{k}" for k in range(4)]].to_numpy().clip(1e-6, 1)
val = (d.anchor_year_group == "2017 - 2019").to_numpy(); y = d.composite_event.to_numpy()
yv, lmv, st = y[val], d.landmark_h.to_numpy()[val], d.stay_id.to_numpy()[val]


def cap(pos, s):
    L, sc, e = lmv[pos], s[pos], yv[pos]; o = np.lexsort((-sc, L)); L, e = L[o], e[o]
    starts = np.r_[0, np.flatnonzero(np.diff(L)) + 1]; sz = np.diff(np.r_[starts, len(L)])
    r = np.arange(len(L)) - np.repeat(starts, sz)
    return 100 * e[r < np.repeat(np.maximum(1, np.round(sz * .1)).astype(int), sz)].sum() / e.sum()


pats, inv = np.unique(st, return_inverse=True); mem = [np.flatnonzero(inv == i) for i in range(len(pats))]
rows = []
s = d.stroke_subtype
for label, ich, sah in [("as analysed: ICH+SAH in the reference category", (s == "ICH"), (s == "SAH")),
                        ("corrected: ICH+SAH coded as both ICH and SAH", s.str.contains("ICH"), s.str.contains("SAH"))]:
    X = pd.DataFrame({c: d[c] for c in ["age", "charlson", "hypertension", "diabetes", "atrial_fibrillation", "heart_failure", "ckd"]})
    X["male"] = (d.gender == "M").astype(float); X["ich"] = ich.astype(float); X["sah"] = sah.astype(float)
    X["lm"] = d.landmark_h / 48
    for k in (0, 2, 3):
        X[f"s{k}"] = np.log(q[:, k] / q[:, 1])
    X["ent"] = d.state_entropy
    for c in ["heart_rate_z", "sbp_z", "map_z", "resp_rate_z", "spo2_z", "temp_c_z", "gcs_eye_z", "gcs_motor_z",
              "urine_output_ml_z", "wbc_z", "hemoglobin_z", "platelet_z", "creatinine_z", "bun_z", "sodium_z",
              "potassium_z", "glucose_z", "mech_vent", "crrt", "vasopressor", "sedative", "img_available"]:
        X[c] = d[c]
    base = list(X.columns); img = []
    for c in FEAT:
        X[c + "+"] = (d[c] == 1).astype(float); X[c + "?"] = d[c].isna().astype(float); img += [c + "+", c + "?"]

    def fp(cols):
        sc = StandardScaler().fit(X.loc[~val, cols])
        m = LogisticRegression(max_iter=4000, C=1.0).fit(sc.transform(X.loc[~val, cols]), y[~val])
        return m.predict_proba(sc.transform(X.loc[val, cols]))[:, 1]
    p0, p1 = fp(base), fp(base + img); a = np.arange(len(yv))
    rng = np.random.default_rng(SEED); ds = []
    for _ in range(REPS):
        pos = np.concatenate([mem[i] for i in rng.integers(0, len(pats), len(pats))]); ds.append(cap(pos, p1) - cap(pos, p0))
    rows.append({"coding": label, "auroc_M0A": roc_auc_score(yv, p0), "auroc_M1D": roc_auc_score(yv, p1),
                 "capture_M0A": cap(a, p0), "capture_M1D": cap(a, p1), "delta": cap(a, p1) - cap(a, p0),
                 "lo": np.percentile(ds, 2.5), "hi": np.percentile(ds, 97.5)})
out = pd.DataFrame(rows)
assert abs(out.delta[0] - 0.000) < 0.001 and round(out.lo[0], 2) == -2.20 and round(out.hi[0], 2) == 2.01   # protocol v1.4 D1, out.iloc[0]
out.to_csv(f"{P3}/ichsah_coding_sensitivity.csv", index=False)
print(out.round(4).to_string(index=False))
