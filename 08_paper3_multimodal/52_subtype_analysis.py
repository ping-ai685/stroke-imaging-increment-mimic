"""
Paper 3: stroke subtype analysis (§12). Secondary; not a primary conclusion.

Rules declared in PROJECT_LOG.md before running (16 Sep 2026):
  * the pooled M0+A and M1-D, as fitted, evaluated inside each subtype, ranked within landmark
    within subtype; ΔCapture(10%) with a patient-level clustered bootstrap, plus AUROC;
  * the subtype x imaging interaction (28 parameters) is fitted only if every subtype has >= 280
    development events; otherwise reported as not examined.

Models are refitted here with the same specification as 47_m1_models.py so this script stands
alone; the pooled confirmatory point estimate (+0.000 pp after protocol v1.4 D1) is recomputed as a check.
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
MIN_EVENTS = 280
SUBTYPES = ["AIS", "ICH", "SAH"]
OVERLAP = "ICH+SAH"     # 16 patients, 0 validation events: descriptives only, as in Paper 1
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
assert set(d.stroke_subtype.unique()) <= set(SUBTYPES + [OVERLAP]), d.stroke_subtype.unique()

q = d[[f"p_state{k}" for k in range(4)]].to_numpy().clip(1e-6, 1)
X = pd.DataFrame(index=d.index)
for c in ["age", "charlson", "hypertension", "diabetes", "atrial_fibrillation", "heart_failure", "ckd"]:
    X[c] = d[c]
X["male"] = (d.gender == "M").astype(float)
# coded exactly as in 36/47 (ICH+SAH falls in the reference category), so the check below can
# reproduce the reported confirmatory estimate; the corrected coding changes no reported number
X["ich"] = (d.stroke_subtype == "ICH").astype(float)
X["sah"] = (d.stroke_subtype == "SAH").astype(float)
X["lm"] = d.landmark_h / 48.0
for k in (0, 2, 3):
    X[f"s{k}"] = np.log(q[:, k] / q[:, 1])
X["entropy"] = d.state_entropy
for c in ["heart_rate_z", "sbp_z", "map_z", "resp_rate_z", "spo2_z", "temp_c_z", "gcs_eye_z",
          "gcs_motor_z", "urine_output_ml_z", "wbc_z", "hemoglobin_z", "platelet_z",
          "creatinine_z", "bun_z", "sodium_z", "potassium_z", "glucose_z",
          "mech_vent", "crrt", "vasopressor", "sedative", "img_available"]:
    X[c] = d[c]
BASE = list(X.columns)
IMG = []
for c in FEATURES:
    X[f"{c}+"] = (d[c] == 1).astype(float)
    X[f"{c}?"] = d[c].isna().astype(float)
    IMG += [f"{c}+", f"{c}?"]
INTER = []
for c in IMG:
    for s in ("ich", "sah"):
        X[f"{c}*{s}"] = X[c] * X[s]
        INTER.append(f"{c}*{s}")

y = d.composite_event.to_numpy()
val = (d.anchor_year_group == "2017 - 2019").to_numpy()
sub = d.stroke_subtype.to_numpy()


def fit_predict(cols):
    sc = StandardScaler().fit(X.loc[~val, cols])
    m = LogisticRegression(max_iter=6000, C=1.0).fit(sc.transform(X.loc[~val, cols]), y[~val])
    return m.predict_proba(sc.transform(X.loc[val, cols]))[:, 1]


def capture(pos, score, yy, lm):
    L, s, e = lm[pos], score[pos], yy[pos]
    order = np.lexsort((-s, L))
    L, e = L[order], e[order]
    starts = np.r_[0, np.flatnonzero(np.diff(L)) + 1]
    sizes = np.diff(np.r_[starts, len(L)])
    rank = np.arange(len(L)) - np.repeat(starts, sizes)
    chosen = rank < np.repeat(np.maximum(1, np.round(sizes * 0.10)).astype(int), sizes)
    return 100 * e[chosen].sum() / e.sum()


def delta_ci(mask, p0, p1, rng):
    yy, lm, st = y[val][mask], d.landmark_h.to_numpy()[val][mask], d.stay_id.to_numpy()[val][mask]
    a, b = p0[mask], p1[mask]
    allpos = np.arange(len(yy))
    obs = capture(allpos, b, yy, lm) - capture(allpos, a, yy, lm)
    pats, inv = np.unique(st, return_inverse=True)
    members = [np.flatnonzero(inv == i) for i in range(len(pats))]
    out = []
    for _ in range(REPS):
        pos = np.concatenate([members[i] for i in rng.integers(0, len(pats), len(pats))])
        if yy[pos].min() == yy[pos].max():
            continue
        out.append(capture(pos, b, yy, lm) - capture(pos, a, yy, lm))
    lo, hi = np.percentile(out, [2.5, 97.5])
    return (obs, lo, hi, capture(allpos, a, yy, lm), capture(allpos, b, yy, lm),
            roc_auc_score(yy, a), roc_auc_score(yy, b))


# ---------------------------------------------------------------------------- 1. descriptives
print("1. DESCRIPTIVES\n")
print(f"{'':6s} {'cohort':12s} {'patients':>9} {'landmarks':>10} {'events':>7} {'rate':>6} {'imaging':>8}")
desc = []
for s in SUBTYPES + [OVERLAP]:
    for lab, m in (("development", ~val), ("validation", val)):
        g = d[(sub == s) & m]
        desc.append({"subtype": s, "cohort": lab, "patients": g.stay_id.nunique(), "landmarks": len(g),
                     "events": int(g.composite_event.sum()), "event_rate": g.composite_event.mean(),
                     "imaging": g.img_available_locked.mean()})
        print(f"{s:6s} {lab:12s} {g.stay_id.nunique():>9} {len(g):>10} {int(g.composite_event.sum()):>7} "
              f"{100*g.composite_event.mean():>5.1f}% {100*g.img_available_locked.mean():>7.1f}%")
pd.DataFrame(desc).to_csv(f"{P3}/subtype_descriptives.csv", index=False)

print("\nphenotype prevalence among imaged landmarks, both cohorts (positive / known)")
print(f"{'feature':32s} " + " ".join(f"{s:>8s}" for s in SUBTYPES + [OVERLAP]))
prev = []
for c in FEATURES:
    cells = []
    for s in SUBTYPES + [OVERLAP]:
        g = d[(sub == s) & (d.img_available_locked == 1)]
        known = g[c].notna()
        r = (g.loc[known, c] == 1).mean()
        prev.append({"feature": LABEL[c], "subtype": s, "prevalence": r, "unknown": 1 - known.mean()})
        cells.append(f"{100*r:>7.1f}%")
    print(f"{LABEL[c]:32s} " + " ".join(cells))
pd.DataFrame(prev).to_csv(f"{P3}/subtype_phenotype_prevalence.csv", index=False)

# ------------------------------------------------------------------------- 2. performance
p0, p1 = fit_predict(BASE), fit_predict(BASE + IMG)
allv = np.ones(val.sum(), dtype=bool)
chk = capture(np.arange(val.sum()), p1, y[val], d.landmark_h.to_numpy()[val]) - \
      capture(np.arange(val.sum()), p0, y[val], d.landmark_h.to_numpy()[val])
print(f"\ncheck: pooled confirmatory point estimate {chk:+.3f} pp "
      f"({'OK' if abs(chk - 0.000) < 0.001 else 'MISMATCH'})")

print("\n2. PERFORMANCE WITHIN SUBTYPE — temporal validation, ranked within landmark within subtype")
print(f"   ({OVERLAP}: {int(y[val][sub[val] == OVERLAP].sum())} validation events — not estimable, not shown)")
print(f"{'':6s} {'events':>7} {'AUROC M0+A':>11} {'M1-D':>6} {'capture M0+A':>13} {'M1-D':>6} "
      f"{'ΔCapture pp [95% CI]':>28}")
rng = np.random.default_rng(SEED)
perf = []
sv = sub[val]
for s in SUBTYPES:
    mask = sv == s
    obs, lo, hi, c0, c1, a0, a1 = delta_ci(mask, p0, p1, rng)
    ev = int(y[val][mask].sum())
    perf.append({"subtype": s, "events": ev, "auroc_M0A": a0, "auroc_M1D": a1, "capture_M0A": c0,
                 "capture_M1D": c1, "delta": obs, "lo": lo, "hi": hi})
    print(f"{s:6s} {ev:>7} {a0:>11.3f} {a1:>6.3f} {c0:>13.1f} {c1:>6.1f} "
          f"{obs:>+9.2f} [{lo:+6.2f}, {hi:+6.2f}]")
pd.DataFrame(perf).to_csv(f"{P3}/subtype_performance.csv", index=False)

# ------------------------------------------------------------------------- 3. interaction
print(f"\n3. SUBTYPE × IMAGING INTERACTION — rule: every subtype >= {MIN_EVENTS} development events")
dev_events = {s: int(y[~val][sub[~val] == s].sum()) for s in SUBTYPES}
print("   development events: " + ", ".join(f"{s} {n}" for s, n in dev_events.items()))
if min(dev_events.values()) >= MIN_EVENTS:
    p2 = fit_predict(BASE + IMG + INTER)
    obs, lo, hi, c0, c1, a0, a1 = delta_ci(allv, p1, p2, rng)
    print(f"   rule met → fitted ({len(INTER)} interaction terms)")
    print(f"   pooled, interaction model vs M1-D: AUROC {a0:.3f} → {a1:.3f}; "
          f"ΔCapture(10%) {obs:+.2f} pp [{lo:+.2f}, {hi:+.2f}]")
    with open(f"{P3}/subtype_interaction.txt", "w") as fh:
        fh.write(f"examined; dev events {dev_events}; auroc {a0:.4f}->{a1:.4f}; "
                 f"delta {obs:+.3f} [{lo:+.3f}, {hi:+.3f}]\n")
else:
    short = [s for s, n in dev_events.items() if n < MIN_EVENTS]
    print(f"   rule NOT met ({', '.join(short)} below {MIN_EVENTS}) → event supply insufficient; not examined")
    with open(f"{P3}/subtype_interaction.txt", "w") as fh:
        fh.write(f"not examined; dev events {dev_events}; threshold {MIN_EVENTS}\n")
