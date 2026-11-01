"""
Paper 3: the baseline rungs of the model ladder — M0-state, M0-full, M0+A.

M0-state  fixed baseline covariates + the filtered state posterior
M0-full   M0-state + the structured ICU physiology available at the landmark
M0+A      M0-full + whether neuroimaging was clinically available by the landmark

The question this pair answers, before imaging is touched at all: how much of the
routine ICU signal has the frozen four-state representation already absorbed? If
M0-state is close to M0-full, the low-dimensional externally validated state is
carrying most of it. If not, M0-full is the honest strong baseline that imaging
must beat.

The state posterior sums to one, so it is entered as three log-ratios against the
preserved-low-support state (the reference), plus the posterior entropy as a
pre-specified secondary predictor.

Development 2008-2016, temporal validation 2017-2019. Patients never cross the
split. Risk is ranked WITHIN each landmark, because the clinical question is
"among the patients in the unit right now, which ones".

M0+A is the comparator for the confirmatory test (protocol §10.1). It is fitted
here rather than with M1 so that the acquisition effect — what the decision to
image carries, separately from what the scan shows — is estimated before any
imaging content exists in the pipeline and cannot be shaded by it.

Adverse state tf_state 0 confirmed 11 Sep 2026; these results are final, not
provisional.
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

DEST = _REPO_ROOT + "/08_paper3_multimodal"
rng = np.random.default_rng(20260911)

d = pd.read_csv(f"{DEST}/landmark_dataset.csv")
d = d[d.note_era].copy()
dev = d[d.anchor_year_group != "2017 - 2019"].copy()
val = d[d.anchor_year_group == "2017 - 2019"].copy()
print(f"development  {len(dev):6d} landmarks / {dev.stay_id.nunique()} patients / "
      f"{dev.composite_event.sum()} events ({100*dev.composite_event.mean():.1f}%)")
print(f"temporal val {len(val):6d} landmarks / {val.stay_id.nunique()} patients / "
      f"{val.composite_event.sum()} events ({100*val.composite_event.mean():.1f}%)")

P = [f"p_state{k}" for k in range(4)]
REF = 1                                    # preserved-low-support = reference
for f in (dev, val):
    q = f[P].values.clip(1e-6, 1)
    for k in [0, 2, 3]:
        f[f"lr_state{k}"] = np.log(q[:, k] / q[:, REF])
    f["male"] = (f.gender == "M").astype(int)
    for s in ["ICH", "SAH"]:
        f[f"sub_{s}"] = (f.stroke_subtype == s).astype(int)
    f["lm"] = f.landmark_h / 48.0

FIXED = ["age", "male", "charlson", "hypertension", "diabetes", "atrial_fibrillation",
         "heart_failure", "ckd", "sub_ICH", "sub_SAH", "lm"]
STATE = ["lr_state0", "lr_state2", "lr_state3", "state_entropy"]
PHYS = ["heart_rate_z", "sbp_z", "map_z", "resp_rate_z", "spo2_z", "temp_c_z",
        "gcs_eye_z", "gcs_motor_z", "urine_output_ml_z", "wbc_z", "hemoglobin_z",
        "platelet_z", "creatinine_z", "bun_z", "sodium_z", "potassium_z", "glucose_z",
        "mech_vent", "crrt", "vasopressor", "sedative"]
MODELS = {"M0-state": FIXED + STATE,
          "M0-full": FIXED + STATE + PHYS,
          "M0+A": FIXED + STATE + PHYS + ["img_available"]}

def topk(df, col, k):
    """rank within each landmark, take the top k%, pool the flagged rows"""
    parts = []
    for _, g in df.groupby("landmark_h"):
        n = max(1, int(round(len(g) * k)))
        parts.append(g.nlargest(n, col))
    f = pd.concat(parts)
    return (100 * f.composite_event.sum() / df.composite_event.sum(),      # capture
            100 * f.composite_event.mean(),                                # PPV
            f.composite_event.mean() / df.composite_event.mean())          # lift

pred = {}
for name, cols in MODELS.items():
    m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0))
    m.fit(dev[cols], dev.composite_event)
    val[name] = m.predict_proba(val[cols])[:, 1]
    pred[name] = val[name].values
    print(f"\n=== {name}  ({len(cols)} predictors) ===")
    print(f"  AUROC {roc_auc_score(val.composite_event, val[name]):.3f}   "
          f"AUPRC {average_precision_score(val.composite_event, val[name]):.3f}   "
          f"Brier {brier_score_loss(val.composite_event, val[name]):.4f}")
    print(f"  {'flagged':>8} {'capture%':>9} {'PPV%':>7} {'lift':>6}")
    for k in (0.05, 0.10, 0.20):
        c, ppv, lift = topk(val, name, k)
        print(f"  {int(k*100):>7}% {c:>9.1f} {ppv:>7.1f} {lift:>6.2f}")

print("\n=== at the 24 h landmark only (the primary clinical display point) ===")
v24 = val[val.landmark_h == 24]
print(f"  {len(v24)} patients at risk, {v24.composite_event.sum()} events "
      f"({100*v24.composite_event.mean():.1f}%)")
for name in MODELS:
    c, ppv, lift = topk(v24, name, 0.10)
    print(f"  {name:9s} top 10%: capture {c:.1f}%  PPV {ppv:.1f}%  lift {lift:.2f}   "
          f"AUROC {roc_auc_score(v24.composite_event, v24[name]):.3f}")

# patient-level clustered bootstrap on the two ladder steps
pat = val.stay_id.unique()
idx = {p: g for p, g in val.groupby("stay_id")}
steps = {"M0-full vs M0-state": ("M0-state", "M0-full"),
         "M0+A vs M0-full": ("M0-full", "M0+A")}
boot = {k: {"auroc": [], "capture10": []} for k in steps}
for _ in range(400):
    smp = rng.choice(pat, len(pat), replace=True)
    b = pd.concat([idx[p] for p in smp])
    if b.composite_event.nunique() < 2:
        continue
    for lab, (lo, hi) in steps.items():
        boot[lab]["auroc"].append(roc_auc_score(b.composite_event, b[hi]) -
                                  roc_auc_score(b.composite_event, b[lo]))
        boot[lab]["capture10"].append(topk(b, hi, 0.10)[0] - topk(b, lo, 0.10)[0])
print("\n=== ladder steps, patient-level clustered bootstrap (400 reps) ===")
for lab, dd in boot.items():
    print(f"  {lab}")
    for k, v in dd.items():
        v = np.array(v)
        unit = "pp" if k == "capture10" else "  "
        print(f"    {k:10s} {v.mean():+.3f} {unit} 95% CI "
              f"[{np.percentile(v,2.5):+.3f}, {np.percentile(v,97.5):+.3f}]")

val[["stay_id", "landmark_h", "composite_event"] + list(MODELS)] \
    .to_csv(f"{DEST}/m0_validation_predictions.csv", index=False)
print(f"\nSaved: {DEST}/m0_validation_predictions.csv")
