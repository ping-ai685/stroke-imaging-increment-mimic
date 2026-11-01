"""
Paper 3: the ten pre-specified sensitivity analyses of §12.1.

Each one re-runs the SAME confirmatory estimand under one varied condition:

    M1-D versus M0+A, temporal validation 2017-2019, pooled over the landmarks,
    ranked within each landmark, top 10% of predicted risk,
    ΔCapture(10%) with a patient-level clustered bootstrap 95% CI.

Nothing here can replace the confirmatory result of §10.1 (§10.2, §10.7). These analyses answer
one question only: is the primary null stable, or does it depend on a choice made along the way?
They were specified in the frozen protocol before any of them was run, and the list is not
extended here.

  1  discordant landmarks excluded (filtered state != full-sequence state at the landmark)
  2  12-hour prediction horizon
  3  treatment-inclusive outcome state (Paper 1 canonical state 1, the respiratory-support
     state, in place of the treatment-free adverse state)
  4  deterioration alone, death as a competing event rather than part of the composite
  5  M0-full without mechanical ventilation, CRRT, vasopressors and sedation
  6  hard filtered state label in place of the posterior
  7a imaging with native missing-value handling (gradient boosting, raw 1/0/NaN)
  7b imaging features set to reference where unknown, img_available retained
  8  alternative imaging update rules (no floor / -24 h floor / 72 h age cap)
  9  alternative availability model and weight truncation (M1-I estimand)
  10 pooled analysis with the 6-hour landmark excluded

Two further pre-specified sensitivity analyses sit outside the §12.1 list, and were missed when
the list was first run (added 16 Sep 2026, before either was run):

  11 §8.1 — Uncertain counted as positive. The protocol words this as counting "probable/likely"
     statements as positive; the four-level scale cannot separate those from weaker hedges
     ("possible", "cannot exclude"), so this variant is BROADER than the protocol's wording.
     Not assessable stays unknown.
  12 B9 — the extended feature set: the seven primary features plus the four primary phenotypes
     that failed κ >= 0.60 and were designated for sensitivity analysis only (acute infarction
     0.58, cerebral oedema 0.56, mass effect 0.54, chronic ischaemic change 0.45). The first three
     are evolving (most recent report), chronic ischaemic change is static (ever-positive).

Shared definitions are imported from 47_m1_models.py so the two scripts cannot drift apart.

Usage
  python 48_sensitivity_analyses.py                 1000 replicates per analysis
  python 48_sensitivity_analyses.py --reps 200      quick structural check
  python 48_sensitivity_analyses.py --only 2 4      run selected analyses
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import argparse
import importlib.util
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = _REPO_ROOT
DEST = f"{ROOT}/08_paper3_multimodal"
SEED = 20260917
TARGET_TF = 0          # treatment-free adverse state
TARGET_P1 = 1          # canonical state 1, respiratory support (the labels are canonical; v1.5 D2 corrected 2 -> 1)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


M1 = _load("m1", f"{DEST}/47_m1_models.py")
MERGE = _load("merge", f"{DEST}/46_merge_imaging_features.py")
IMG, FIXED, STATE, PHYS = M1.IMG, M1.FIXED, M1.STATE, M1.PHYS
IMGCOLS = [f"{c}__pos" for c in IMG] + [f"{c}__unk" for c in IMG]


def fit_pair(dev, val, base_cols, img_cols, outcome="composite_event", est=None):
    """Fit M0+A and M1-D on one variant and return the validation frame with both columns."""
    val = val.copy()
    for name, cols in (("M0+A", base_cols), ("M1-D", base_cols + img_cols)):
        m = (make_pipeline(StandardScaler(), LogisticRegression(max_iter=4000, C=1.0))
             if est is None else est())
        m.fit(dev[cols], dev[outcome])
        val[name] = m.predict_proba(val[cols])[:, 1]
    return val


def delta(val, outcome, reps, rng, w=None):
    """ΔCapture(10%) for M1-D over M0+A, with a patient-level clustered bootstrap."""
    if outcome != "composite_event":
        v = val.drop(columns=["composite_event"]).rename(columns={outcome: "composite_event"})
    else:
        v = val
    obs = M1.topk_capture(v, "M1-D", 0.10, w)[0] - M1.topk_capture(v, "M0+A", 0.10, w)[0]
    pat = v.stay_id.unique()
    byp = {p: g for p, g in v.groupby("stay_id")}
    out = []
    for _ in range(reps):
        b = pd.concat([byp[p] for p in rng.choice(pat, len(pat), replace=True)])
        if b.composite_event.nunique() < 2:
            continue
        out.append(M1.topk_capture(b, "M1-D", 0.10, w)[0] - M1.topk_capture(b, "M0+A", 0.10, w)[0])
    return obs, np.percentile(out, 2.5), np.percentile(out, 97.5), len(v), int(v.composite_event.sum())


def base_frames(features=None, extra=()):
    d = pd.read_csv(f"{DEST}/landmark_dataset.csv")
    d = d[d.note_era].copy()
    f = pd.read_csv(f"{DEST}/landmark_imaging_features.csv") if features is None else features
    f = f[["stay_id", "landmark_idx", "img_available_locked"] + IMG + list(extra)]
    n0 = len(d)
    d = d.merge(f, on=["stay_id", "landmark_idx"], how="left", validate="one_to_one")
    assert len(d) == n0
    return (M1.derive(d[d.anchor_year_group != "2017 - 2019"].copy()),
            M1.derive(d[d.anchor_year_group == "2017 - 2019"].copy()))


def rederived_outcomes():
    """Outcomes for sensitivity 2 and 3, rebuilt from the state sequences and the cohort.

    Same construction as 35_build_landmark_dataset.py: the landmark sits at the end of window L,
    at T = 6(L+1); the horizon spans windows L+1..L+H; death counts inside [T, T+6H); an alive
    ICU discharge inside the horizon is a non-event. Eligibility is NOT changed — it stays on the
    filtered treatment-free state, so no future information enters who is predicted for.
    """
    coh = pd.read_csv(f"{ROOT}/04_outputs/tables/patient_level_cohort.csv",
                      parse_dates=["intime", "outtime", "deathtime"])
    dh = (coh.deathtime - coh.intime).dt.total_seconds() / 3600
    coh["death_h"] = np.where(coh.deathtime.notna(), dh, np.inf)
    coh["icu_end_h"] = (coh.outtime - coh.intime).dt.total_seconds() / 3600
    base = coh.set_index("stay_id")[["death_h", "icu_end_h"]]

    tf = pd.read_csv(f"{DEST}/tf_state_assignments_all.csv")
    TF = dict(zip(zip(tf.stay_id, tf.window_idx), tf.tf_state))
    p1 = pd.read_csv(f"{DEST}/p1_state_assignments_truncated.csv")   # protocol v1.4 D1 (script 31)
    P1 = dict(zip(zip(p1.stay_id, p1.window_idx), p1.state_k4))

    lm = pd.read_csv(f"{DEST}/landmark_dataset.csv", usecols=["stay_id", "landmark_idx", "landmark_h"])
    rows = []
    for r in lm.itertuples():
        L, T = r.landmark_idx, r.landmark_h
        b = base.loc[r.stay_id]
        rec = {"stay_id": r.stay_id, "landmark_idx": L}
        for tag, H, states, target in (("12h", 2, TF, TARGET_TF), ("ti", 4, P1, TARGET_P1)):
            fut = [states.get((r.stay_id, k)) for k in range(L + 1, L + 1 + H)]
            adverse = target in [s for s in fut if s is not None]
            died = bool(T <= b.death_h < T + 6 * H)
            rec[f"event_{tag}"] = int(adverse or died)
            rec[f"adverse_{tag}"] = int(adverse)
        rows.append(rec)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--only", type=str, nargs="*", default=None)
    args = ap.parse_args()
    want = set(args.only) if args.only else None
    rng = np.random.default_rng(SEED)
    warnings.filterwarnings("ignore")

    dev, val = base_frames()
    BASE = FIXED + STATE + PHYS + ["img_available"]
    results = []

    def record(tag, label, out):
        obs, lo, hi, n, ev = out
        results.append({"analysis": tag, "condition": label, "landmarks": n, "events": ev,
                        "delta_pp": obs, "lo": lo, "hi": hi})
        flag = "excludes 0" if (lo > 0 or hi < 0) else "includes 0"
        print(f"  {tag:4s} {label:46s} {obs:+6.2f} pp [{lo:+6.2f}, {hi:+6.2f}]  "
              f"n={n:5d} ev={ev:4d}  {flag}")

    print(f"sensitivity analyses of §12.1 — {args.reps} bootstrap replicates each")
    print(f"reference: the confirmatory result is +0.00 pp [-2.20, +2.01] (protocol v1.4 D1)\n")

    if want is None or "1" in want:
        m = val.filtered_state != val.adj_state_at_landmark
        dm = dev.filtered_state != dev.adj_state_at_landmark
        print(f"  [1] discordant landmarks: development {100*dm.mean():.1f}%, "
              f"validation {100*m.mean():.1f}%")
        record("1", "discordant landmarks excluded",
               delta(fit_pair(dev[~dm], val[~m], BASE, IMGCOLS), "composite_event", args.reps, rng))

    if want is None or (want & {"2", "3"}):
        alt = rederived_outcomes()
        devA = dev.merge(alt, on=["stay_id", "landmark_idx"], how="left", validate="one_to_one")
        valA = val.merge(alt, on=["stay_id", "landmark_idx"], how="left", validate="one_to_one")
        if want is None or "2" in want:
            print(f"  [2] 12 h horizon event rate: development {100*devA.event_12h.mean():.1f}%, "
                  f"validation {100*valA.event_12h.mean():.1f}% "
                  f"(24 h: {100*dev.composite_event.mean():.1f}% / "
                  f"{100*val.composite_event.mean():.1f}%)")
            record("2", "12-hour prediction horizon",
                   delta(fit_pair(devA, valA, BASE, IMGCOLS, outcome="event_12h"),
                         "event_12h", args.reps, rng))
        if want is None or "3" in want:
            print(f"  [3] treatment-inclusive event rate: development "
                  f"{100*devA.event_ti.mean():.1f}%, validation {100*valA.event_ti.mean():.1f}%")
            record("3", "treatment-inclusive outcome state",
                   delta(fit_pair(devA, valA, BASE, IMGCOLS, outcome="event_ti"),
                         "event_ti", args.reps, rng))

    if want is None or "4" in want:
        # deterioration alone; a death without prior deterioration stays in the risk set as a
        # non-event, which is the competing-risk reading of the endpoint
        print(f"  [4] deterioration-only event rate: development "
              f"{100*dev.future_24h_adverse.mean():.1f}%, validation "
              f"{100*val.future_24h_adverse.mean():.1f}%; deaths without deterioration: "
              f"{int(((val.future_24h_death == 1) & (val.future_24h_adverse == 0)).sum())}")
        record("4", "deterioration alone, death competing",
               delta(fit_pair(dev, val, BASE, IMGCOLS, outcome="future_24h_adverse"),
                     "future_24h_adverse", args.reps, rng))

    if want is None or "5" in want:
        notreat = [c for c in BASE if c not in ("mech_vent", "crrt", "vasopressor", "sedative")]
        record("5", "no ventilation / CRRT / vasopressor / sedation",
               delta(fit_pair(dev, val, notreat, IMGCOLS), "composite_event", args.reps, rng))

    if want is None or "6" in want:
        for f in (dev, val):
            for k in (0, 2, 3):
                f[f"hard_state{k}"] = (f.filtered_state == k).astype(float)
        hard = [c for c in BASE if c not in STATE] + [f"hard_state{k}" for k in (0, 2, 3)]
        record("6", "hard filtered state label, no posterior",
               delta(fit_pair(dev, val, hard, IMGCOLS), "composite_event", args.reps, rng))

    if want is None or "7" in want:
        gb = lambda: HistGradientBoostingClassifier(max_iter=200, learning_rate=0.06,
                                                    max_leaf_nodes=15, random_state=SEED)
        record("7a", "native missing handling (gradient boosting)",
               delta(fit_pair(dev, val, BASE, IMG, est=gb), "composite_event", args.reps, rng))
        for f in (dev, val):
            for c in IMG:
                f[f"{c}__ref"] = f[c].fillna(0.0)
        record("7b", "unknown imaging set to reference",
               delta(fit_pair(dev, val, BASE, [f"{c}__ref" for c in IMG]),
                     "composite_event", args.reps, rng))

    if want is None or "8" in want:
        for tag, kw in (("no floor", dict(floor_h=-1e9)),
                        ("floor -24 h", dict(floor_h=-24.0)),
                        ("age cap 72 h", dict(floor_h=-1e9, age_cap=72.0))):
            d2, v2 = base_frames(features=MERGE.build(verbose=False, **kw))
            record("8", f"update rule: {tag}",
                   delta(fit_pair(d2, v2, BASE, IMGCOLS), "composite_event", args.reps, rng))

    if want is None or "9" in want:
        # M1-I estimand: availability model and weight truncation varied
        devI0, valI0 = dev[dev.img_available_locked == 1], val[val.img_available_locked == 1]
        for tag, avcols, trunc in (("availability model without physiology", FIXED + STATE, (1, 99)),
                                   ("weight truncation p2.5-p97.5", FIXED + STATE + PHYS, (2.5, 97.5))):
            av = make_pipeline(StandardScaler(), LogisticRegression(max_iter=4000, C=1.0))
            av.fit(dev[avcols], dev.img_available_locked)
            dI, vI = devI0.copy(), valI0.copy()
            for f in (dI, vI):
                f["sw"] = dev.img_available_locked.mean() / \
                    np.clip(av.predict_proba(f[avcols])[:, 1], 1e-4, 1)
            a, b = np.percentile(dI.sw, list(trunc))
            for f in (dI, vI):
                f["sw"] = f.sw.clip(a, b)
            record("9", tag, delta(fit_pair(dI, vI, FIXED + STATE + PHYS, IMGCOLS),
                                   "composite_event", args.reps, rng, w="sw"))

    if want is None or "10" in want:
        record("10", "6-hour landmark excluded",
               delta(fit_pair(dev[dev.landmark_h > 6], val[val.landmark_h > 6], BASE, IMGCOLS),
                     "composite_event", args.reps, rng))

    if want is None or "11" in want:
        d2, v2 = base_frames(features=MERGE.build(verbose=False, uncertain_positive=True))
        record("11", "Uncertain counted as positive (§8.1)",
               delta(fit_pair(d2, v2, BASE, IMGCOLS), "composite_event", args.reps, rng))

    if want is None or "12" in want:
        EXTRA = list(MERGE.EXTENDED_EVOLVING) + list(MERGE.EXTENDED_STATIC)
        d2, v2 = base_frames(features=MERGE.build(verbose=False, extended=True), extra=EXTRA)
        for f in (d2, v2):
            for c in EXTRA:
                f[f"{c}__pos"] = (f[c] == 1).astype(float)
                f[f"{c}__unk"] = f[c].isna().astype(float)
        a = v2[v2.img_available_locked == 1]
        print("  [12] extended features among imaged validation landmarks: " + ", ".join(
            f"{c} {100*(a[c] == 1).mean():.1f}% pos / {100*a[c].isna().mean():.1f}% unk" for c in EXTRA))
        ext = IMGCOLS + [f"{c}__pos" for c in EXTRA] + [f"{c}__unk" for c in EXTRA]
        record("12", "extended set: + 4 B9-failed phenotypes",
               delta(fit_pair(d2, v2, BASE, ext), "composite_event", args.reps, rng))

    out = pd.DataFrame(results)
    path = (f"{DEST}/sensitivity_results.csv" if want is None
            else f"{DEST}/sensitivity_results_{'_'.join(sorted(want))}.csv")
    out.to_csv(path, index=False)
    n_excl = int(((out.lo > 0) | (out.hi < 0)).sum())
    print(f"\n{len(out)} analyses run; {n_excl} have an interval excluding zero.")
    print(f"Saved: {path}")
    print("None of these can replace the confirmatory result (§10.2, §10.7).")


if __name__ == "__main__":
    main()
