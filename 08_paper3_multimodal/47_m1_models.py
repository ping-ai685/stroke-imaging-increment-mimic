"""
Paper 3: the imaging rungs of the ladder — M1-D and M1-I, and the confirmatory comparison.

M1-D  deployable: M0+A plus imaging content where the update rule supplies it, falling back to
      M0+A where it does not. Fitted on all landmarks. This is the model of the confirmatory
      test (§10.1).
M1-I  information content: imaging content among landmarks where content is available, with
      stabilized inverse probability weights for the selection mechanism (§9.2).

The two answer different questions and need not agree (§7). Imaging content can be strongly
informative among the scanned while the deployed system improves overall capture only modestly,
because many patients are never scanned. That divergence is a finding, not a problem.

THE CONFIRMATORY TEST (§10.1) — there is exactly one, and it is fixed before this script runs:

    M1-D versus M0+A, temporal validation 2017-2019, pooled over all eight landmarks,
    ranked within each landmark, top 10% of predicted risk,
    difference in 24-hour composite event capture, patient-level clustered bootstrap 95% CI.

§10.2: if that interval includes zero the primary conclusion is that no statistically supported
incremental value was observed, and it may NOT be replaced by AUROC, AUPRC, the top 5% or 20%
stratum, a single landmark, or M1-I. Everything else in this script is secondary and is printed
after the confirmatory result, never in place of it. §10.3 fixes +5 pp as an interpretation
scale, not a second threshold.

Imaging encoding. Each of the seven primary features (frozen 12 Sep 2026 under B9) enters as two
columns: known-positive, and unknown — with known-negative as the reference. A landmark with no
usable report has all seven unknown, which is how the model "falls back to M0+A". Unknown covers
both no usable report and an Uncertain / Not assessable assertion; §8.1 forbids reading either as
negative. Alternative missingness handling is sensitivity analysis 7 of §12.1, not this script.

`img_available` is left exactly as M0+A used it — the acquisition decision, §8.3, a final result
— while the §8.2 update rule with its 72 h floor governs which report supplies content. The 182
landmarks whose only report predates the floor therefore keep img_available = 1 and carry no
content. M1-I, which estimates the information in the content, uses img_available_locked.

Usage
  python 47_m1_models.py                 confirmatory run, 2000 bootstrap replicates
  python 47_m1_models.py --reps 200      quick structural check; NOT the reportable result
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import argparse

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

DEST = _REPO_ROOT + "/08_paper3_multimodal"
SEED = 20260917

IMG = ["haem_present", "ivh_present", "mls_present", "haem_intraparenchymal",
       "haem_subarachnoid", "infarct_mca", "infarct_cerebellum"]

FIXED = ["age", "male", "charlson", "hypertension", "diabetes", "atrial_fibrillation",
         "heart_failure", "ckd", "sub_ICH", "sub_SAH", "lm"]
STATE = ["lr_state0", "lr_state2", "lr_state3", "state_entropy"]
PHYS = ["heart_rate_z", "sbp_z", "map_z", "resp_rate_z", "spo2_z", "temp_c_z",
        "gcs_eye_z", "gcs_motor_z", "urine_output_ml_z", "wbc_z", "hemoglobin_z",
        "platelet_z", "creatinine_z", "bun_z", "sodium_z", "potassium_z", "glucose_z",
        "mech_vent", "crrt", "vasopressor", "sedative"]


def derive(f):
    """The same derived predictors as 36_m0_baseline_models.py, so the ladder is comparable."""
    q = f[[f"p_state{k}" for k in range(4)]].values.clip(1e-6, 1)
    for k in [0, 2, 3]:
        f[f"lr_state{k}"] = np.log(q[:, k] / q[:, 1])       # state 1 = reference
    f["male"] = (f.gender == "M").astype(int)
    for s in ["ICH", "SAH"]:
        f[f"sub_{s}"] = (f.stroke_subtype == s).astype(int)
    f["lm"] = f.landmark_h / 48.0
    for c in IMG:                                           # positive / unknown, negative is ref
        f[f"{c}__pos"] = (f[c] == 1).astype(float)
        f[f"{c}__unk"] = f[c].isna().astype(float)
    return f


def topk_capture(df, col, k=0.10, w=None):
    """Rank within each landmark, take the top k%, return capture / PPV / lift.

    Pooling before ranking would answer a different question: the clinical one is 'among the
    patients in the unit right now, which ones'. Weights, when given, make these the weighted
    estimands used for M1-I.
    """
    df = df.reset_index(drop=True)      # a bootstrap frame repeats index labels; .loc on a
                                        # duplicated label returns every matching row, which
                                        # would silently select far more than the top k%
    weight = df[w] if w else pd.Series(1.0, index=df.index)
    sel = []
    for _, g in df.groupby("landmark_h", sort=False):
        n = max(1, int(round(len(g) * k)))
        sel.append(g.nlargest(n, col).index)
    sel = np.concatenate(sel)
    ev, wt = df.composite_event, weight
    num = (ev.loc[sel] * wt.loc[sel]).sum()
    return (100 * num / (ev * wt).sum(),
            100 * num / wt.loc[sel].sum(),
            (num / wt.loc[sel].sum()) / ((ev * wt).sum() / wt.sum()))


def calibration(y, p):
    """Calibration intercept and slope (§10.5).

    Intercept: a in logit P(y) = a + logit(p), i.e. logistic regression with the predicted logit
    as an offset, solved directly. (Corrected 16 Sep 2026: the first version returned
    logit(mean y) - mean(logit p), which Jensen's inequality biases — it gave +0.53 where the
    offset intercept is -0.16, the wrong sign.) Slope: the coefficient on logit(p) with a free
    intercept.
    """
    z = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    slope = LogisticRegression(max_iter=2000, C=1e6).fit(z.reshape(-1, 1), y).coef_[0, 0]
    icpt = brentq(lambda a: (y - 1 / (1 + np.exp(-(a + z)))).sum(), -10, 10)
    return icpt, slope


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=2000)
    args = ap.parse_args()
    rng = np.random.default_rng(SEED)

    d = pd.read_csv(f"{DEST}/landmark_dataset.csv")
    d = d[d.note_era].copy()
    img = pd.read_csv(f"{DEST}/landmark_imaging_features.csv",
                      usecols=["stay_id", "landmark_idx", "img_available_locked",
                               "img_report_age_h"] + IMG)
    n0 = len(d)
    d = d.merge(img, on=["stay_id", "landmark_idx"], how="left", validate="one_to_one")
    assert len(d) == n0, "the imaging merge changed the number of landmark rows"

    dev = derive(d[d.anchor_year_group != "2017 - 2019"].copy())
    val = derive(d[d.anchor_year_group == "2017 - 2019"].copy())
    print(f"development  {len(dev):6d} landmarks / {dev.stay_id.nunique():4d} patients / "
          f"{dev.composite_event.sum():4d} events ({100*dev.composite_event.mean():.1f}%)")
    print(f"temporal val {len(val):6d} landmarks / {val.stay_id.nunique():4d} patients / "
          f"{val.composite_event.sum():4d} events ({100*val.composite_event.mean():.1f}%)")
    print(f"content available: development {100*dev.img_available_locked.mean():.1f}%, "
          f"validation {100*val.img_available_locked.mean():.1f}%")

    IMGCOLS = [f"{c}__pos" for c in IMG] + [f"{c}__unk" for c in IMG]
    LADDER = {"M0+A": FIXED + STATE + PHYS + ["img_available"],
              "M1-D": FIXED + STATE + PHYS + ["img_available"] + IMGCOLS}

    for name, cols in LADDER.items():
        m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=4000, C=1.0))
        m.fit(dev[cols], dev.composite_event)
        val[name] = m.predict_proba(val[cols])[:, 1]

    # ---------------------------------------------------------------- confirmatory test, §10.1
    obs = topk_capture(val, "M1-D")[0] - topk_capture(val, "M0+A")[0]
    pat = val.stay_id.unique()
    byp = {p: g for p, g in val.groupby("stay_id")}
    diffs = []
    for _ in range(args.reps):
        b = pd.concat([byp[p] for p in rng.choice(pat, len(pat), replace=True)])
        if b.composite_event.nunique() < 2:
            continue
        diffs.append(topk_capture(b, "M1-D")[0] - topk_capture(b, "M0+A")[0])
    lo, hi = np.percentile(diffs, [2.5, 97.5])

    print("\n" + "=" * 72)
    print("CONFIRMATORY COMPARISON (§10.1) — M1-D versus M0+A")
    print("temporal validation 2017-2019, pooled over eight landmarks, ranked within landmark,")
    print("top 10% of predicted risk, patient-level clustered bootstrap")
    print("=" * 72)
    print(f"  ΔCapture(10%) = {obs:+.2f} pp   95% CI [{lo:+.2f}, {hi:+.2f}]   "
          f"({len(diffs)} replicates)")
    if lo > 0:
        print("  → interval excludes zero: statistically supported incremental value (§10.2)")
    else:
        print("  → interval includes zero: NO statistically supported incremental value (§10.2).")
        print("    This conclusion may not be replaced by any secondary result below.")
    print(f"  interpretation scale (§10.3): benchmark +5.00 pp, point estimate {obs:+.2f} pp")

    # ------------------------------------------------------------------- secondary, §10.4-10.5
    print("\n--- secondary: risk stratification, temporal validation (§10.4) ---")
    print(f"{'model':8s} {'flagged':>8} {'capture%':>9} {'PPV%':>7} {'lift':>6}")
    for name in LADDER:
        for k in (0.05, 0.10, 0.20):
            c, ppv, lift = topk_capture(val, name, k)
            print(f"{name:8s} {int(k*100):>7}% {c:>9.1f} {ppv:>7.1f} {lift:>6.2f}")
    print("\n--- secondary: standard performance (§10.5) ---")
    print(f"{'model':8s} {'AUROC':>7} {'AUPRC':>7} {'Brier':>8} {'cal icpt':>9} {'cal slope':>10}")
    for name in LADDER:
        i, s = calibration(val.composite_event.values, val[name].values)
        print(f"{name:8s} {roc_auc_score(val.composite_event, val[name]):>7.3f} "
              f"{average_precision_score(val.composite_event, val[name]):>7.3f} "
              f"{brier_score_loss(val.composite_event, val[name]):>8.4f} {i:>9.3f} {s:>10.3f}")
    print("\n--- secondary: the 24 h presentation point (§10.3) ---")
    v24 = val[val.landmark_h == 24]
    print(f"  {len(v24)} at risk, {v24.composite_event.sum()} events "
          f"({100*v24.composite_event.mean():.1f}%), top 10% flags {max(1, round(len(v24)*0.1))}")
    for name in LADDER:
        c, ppv, lift = topk_capture(v24, name, 0.10)
        print(f"  {name:8s} capture {c:5.1f}%  PPV {ppv:5.1f}%  lift {lift:.2f}")

    # ----------------------------------------------------------------------------- M1-I, §9.2
    print("\n" + "=" * 72)
    print("M1-I — information content among landmarks with usable imaging content (§9.2)")
    print("=" * 72)
    AV = FIXED + STATE + PHYS
    av = make_pipeline(StandardScaler(), LogisticRegression(max_iter=4000, C=1.0))
    av.fit(dev[AV], dev.img_available_locked)
    for f in (dev, val):
        f["ps"] = av.predict_proba(f[AV])[:, 1]
        f["sw"] = f.img_available_locked.mean() / f.ps.clip(1e-4, 1)

    print(f"  availability model AUROC (validation) "
          f"{roc_auc_score(val.img_available_locked, val.ps):.3f}")
    for lab, f in (("development", dev), ("validation", val)):
        a, u = f[f.img_available_locked == 1], f[f.img_available_locked == 0]
        print(f"  propensity {lab:11s} imaged {a.ps.min():.3f}-{a.ps.max():.3f} "
              f"(median {a.ps.median():.3f}) | not imaged {u.ps.min():.3f}-{u.ps.max():.3f} "
              f"(median {u.ps.median():.3f})")
    print("  landmark-specific positivity (imaged share, and propensity range among imaged):")
    for h, g in val.groupby("landmark_h"):
        a = g[g.img_available_locked == 1]
        print(f"    {int(h):2d} h  imaged {100*g.img_available_locked.mean():5.1f}%  "
              f"n={len(g):5d}  propensity {a.ps.min():.3f}-{a.ps.max():.3f}")

    devI = dev[dev.img_available_locked == 1].copy()
    valI = val[val.img_available_locked == 1].copy()
    for name, (loq, hiq) in (("primary", (1, 99)), ("sensitivity", (2.5, 97.5))):
        col = f"sw_{name}"
        for f in (devI, valI):
            a, b = np.percentile(devI.sw, [loq, hiq])
            f[col] = f.sw.clip(a, b)
        ess = devI[col].sum() ** 2 / (devI[col] ** 2).sum()
        print(f"  weights {name:11s} truncated at p{loq}-p{hiq} "
              f"[{devI[col].min():.3f}, {devI[col].max():.3f}] mean {devI[col].mean():.3f} | "
              f"development ESS {ess:.0f} of {len(devI)} landmarks "
              f"({100*ess/len(devI):.1f}%)")

    IMGONLY = [f"{c}__pos" for c in IMG] + [f"{c}__unk" for c in IMG]
    M1I = {"M0-full (imaged, weighted)": FIXED + STATE + PHYS,
           "M1-I (imaged, weighted)": FIXED + STATE + PHYS + IMGONLY}
    for name, cols in M1I.items():
        m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=4000, C=1.0))
        m.fit(devI[cols], devI.composite_event,
              logisticregression__sample_weight=devI.sw_primary)
        valI[name] = m.predict_proba(valI[cols])[:, 1]
    print(f"\n  {len(valI)} imaged validation landmarks, "
          f"{valI.composite_event.sum()} events ({100*valI.composite_event.mean():.1f}%)")
    print(f"  {'model':28s} {'AUROC':>7} {'wCapture10%':>12} {'wPPV%':>7} {'wLift':>6}")
    for name in M1I:
        c, ppv, lift = topk_capture(valI, name, 0.10, w="sw_primary")
        print(f"  {name:28s} "
              f"{roc_auc_score(valI.composite_event, valI[name], sample_weight=valI.sw_primary):>7.3f} "
              f"{c:>12.1f} {ppv:>7.1f} {lift:>6.2f}")

    diffs_i = []
    patI = valI.stay_id.unique()
    byI = {p: g for p, g in valI.groupby("stay_id")}
    for _ in range(args.reps):
        b = pd.concat([byI[p] for p in rng.choice(patI, len(patI), replace=True)])
        if b.composite_event.nunique() < 2:
            continue
        diffs_i.append(topk_capture(b, "M1-I (imaged, weighted)", 0.10, w="sw_primary")[0] -
                       topk_capture(b, "M0-full (imaged, weighted)", 0.10, w="sw_primary")[0])
    lo_i, hi_i = np.percentile(diffs_i, [2.5, 97.5])
    obs_i = (topk_capture(valI, "M1-I (imaged, weighted)", 0.10, w="sw_primary")[0] -
             topk_capture(valI, "M0-full (imaged, weighted)", 0.10, w="sw_primary")[0])
    print(f"  weighted ΔCapture(10%), M1-I vs M0-full among the imaged: "
          f"{obs_i:+.2f} pp  95% CI [{lo_i:+.2f}, {hi_i:+.2f}]")
    print("  This is the information-content estimand (§7), NOT the confirmatory test.")

    out = val[["stay_id", "landmark_h", "landmark_idx", "composite_event",
               "img_available", "img_available_locked", "ps", "sw"] + list(LADDER)]
    out.to_csv(f"{DEST}/m1_validation_predictions.csv", index=False)
    valI[["stay_id", "landmark_h", "composite_event", "sw_primary", "sw_sensitivity"]
         + list(M1I)].to_csv(f"{DEST}/m1i_validation_predictions.csv", index=False)
    print(f"\nSaved: m1_validation_predictions.csv, m1i_validation_predictions.csv")


if __name__ == "__main__":
    main()
