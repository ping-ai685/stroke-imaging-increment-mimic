"""
Paper 3, C1.5 — the confirmatory comparison repeated with the second extractor (protocol v1.3).

Nothing in the locked pipeline is edited or overwritten. This script

  1. loads 46_merge_imaging_features.py with only its two input paths pointed at a chosen
     extractor output (the update rule, encoding and code are the locked ones), and
  2. imports derive() and topk_capture() from 47_m1_models.py and repeats its confirmatory block
     line for line — same predictors, same models, same seed, same bootstrap — writing nothing
     into the project.

Step 0 is a self-check: run with the FROZEN extractor's output, the feature table must equal
landmark_imaging_features.csv and the comparison must reproduce the primary result, +0.00 pp,
95% CI -2.20 to +2.01 (protocol v1.4 D1; was +0.15, -2.31 to +1.91). Only then are C1-a and C1-b run.

  C1-a  the seven primary features, values from the second extractor
  C1-b  the set re-derived under B9 from the second extractor's validation (logged 2 Oct 2026):
        the seven + cerebral oedema (evolving, latest report) + infarct region occipital
        (static, ever-positive) — each handled by the locked rule for its kind

Also: agreement between the two extractors over all reports, and the share of validation
landmarks whose feature value differs. Prints aggregates only.

Usage  python c1_analysis.py [--reps 2000]
"""
import argparse
import importlib.util
import json
import types
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import cohen_kappa_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
P3 = HERE.parent
FROZEN_OUT = None                      # None: 46 reads its own (frozen-extractor) inputs, untouched
C1_OUT = (f"{HERE}/analysis_population_c1_out.jsonl", f"{HERE}/analysis_population_c1_failed.csv")
SEVEN = ["haem_present", "ivh_present", "mls_present", "haem_intraparenchymal",
         "haem_subarachnoid", "infarct_mca", "infarct_cerebellum"]
NINE = SEVEN + ["oedema_present", "infarct_occipital"]


def load_46(paths):
    src = (P3 / "46_merge_imaging_features.py").read_text(encoding="utf-8")
    a, b = 'f"{P3}/extractor/analysis_population_out.jsonl"', 'f"{P3}/extractor/analysis_population_failed.csv"'
    assert src.count(a) == 1 and src.count(b) == 1, "46 has changed — stop"
    if paths is not None:
        src = src.replace(a, repr(paths[0])).replace(b, repr(paths[1]))
    m = types.ModuleType("merge46")
    exec(compile(src, "46_merge_imaging_features.py", "exec"), m.__dict__)
    return m


def load_47():
    spec = importlib.util.spec_from_file_location("m47", P3 / "47_m1_models.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def features(paths, nine=False):
    m = load_46(paths)
    if nine:
        m.STATIC_LISTS = dict(m.STATIC_LISTS, infarct_occipital=("infarct_region", "occipital"))
        m.EXTENDED_EVOLVING = {"oedema_present": "cerebral_oedema"}   # the only extended field used
        m.EXTENDED_STATIC = {}
    return m.build(verbose=False, extended=nine)


def confirmatory(feat, img, reps, label):
    """47_m1_models.py §10.1 block, repeated with a given feature table and feature list."""
    m47 = load_47()
    m47.IMG = img
    rng = np.random.default_rng(m47.SEED)
    d = pd.read_csv(P3 / "landmark_dataset.csv")
    d = d[d.note_era].copy()
    n0 = len(d)
    d = d.merge(feat[["stay_id", "landmark_idx", "img_available_locked", "img_report_age_h"] + img],
                on=["stay_id", "landmark_idx"], how="left", validate="one_to_one")
    assert len(d) == n0
    dev = m47.derive(d[d.anchor_year_group != "2017 - 2019"].copy())
    val = m47.derive(d[d.anchor_year_group == "2017 - 2019"].copy())
    IMGCOLS = [f"{c}__pos" for c in img] + [f"{c}__unk" for c in img]
    LADDER = {"M0+A": m47.FIXED + m47.STATE + m47.PHYS + ["img_available"],
              "M1-D": m47.FIXED + m47.STATE + m47.PHYS + ["img_available"] + IMGCOLS}
    for name, cols in LADDER.items():
        mdl = make_pipeline(StandardScaler(), LogisticRegression(max_iter=4000, C=1.0))
        mdl.fit(dev[cols], dev.composite_event)
        val[name] = mdl.predict_proba(val[cols])[:, 1]
    obs = m47.topk_capture(val, "M1-D")[0] - m47.topk_capture(val, "M0+A")[0]
    pat = val.stay_id.unique()
    byp = {p: g for p, g in val.groupby("stay_id")}
    diffs = []
    for _ in range(reps):
        b = pd.concat([byp[p] for p in rng.choice(pat, len(pat), replace=True)])
        if b.composite_event.nunique() < 2:
            continue
        diffs.append(m47.topk_capture(b, "M1-D")[0] - m47.topk_capture(b, "M0+A")[0])
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    au = {n: roc_auc_score(val.composite_event, val[n]) for n in LADDER}
    consistent = (lo <= 0 <= hi) and hi < 5
    tot = int(val.composite_event.sum())
    ev = {n: int(round(m47.topk_capture(val, n)[0] * tot / 100)) for n in LADDER}
    print(f"{label:46s} ΔCapture(10%) {obs:+.2f} pp  95% CI [{lo:+.2f}, {hi:+.2f}]  "
          f"({len(diffs)} reps)  AUROC M0+A {au['M0+A']:.3f} M1-D {au['M1-D']:.3f}  "
          f"content available {100*val.img_available_locked.mean():.1f}%"
          + ("" if label.startswith("0") else f"  → {'CONSISTENT' if consistent else 'NOT CONSISTENT'} (C1.6)"))
    return {"delta": obs, "lo": lo, "hi": hi, "reps": len(diffs), "consistent": bool(consistent),
            "auroc_base": au["M0+A"], "auroc_aug": au["M1-D"], "events_base": ev["M0+A"], "events_aug": ev["M1-D"],
            "events_total": tot, "landmarks": len(val), "content_pct": 100 * val.img_available_locked.mean(),
            "n_features": len(img)}


def records(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            if not r["error"]:
                out[r["note_id"]] = r["record"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=2000)
    a = ap.parse_args()

    # 0 — self-check with the frozen extractor
    f0 = features(FROZEN_OUT)
    locked = pd.read_csv(P3 / "landmark_imaging_features.csv")
    cols = list(locked.columns)
    same = f0[cols].reset_index(drop=True).equals(locked[cols].reset_index(drop=True)) or \
        np.allclose(f0[cols].select_dtypes("number").to_numpy(float),
                    locked[cols].select_dtypes("number").to_numpy(float), equal_nan=True)
    print(f"self-check: feature table rebuilt from the frozen output equals landmark_imaging_features.csv: {same}")
    assert same
    r0c = confirmatory(f0, SEVEN, a.reps, "0  frozen extractor (must be +0.00, -2.20, +2.01)")
    assert (round(r0c["delta"], 2), round(r0c["lo"], 2), round(r0c["hi"], 2)) == (0.0, -2.2, 2.01), "self-check failed — stop"

    # C1-a and C1-b
    fa = features(C1_OUT)
    fb = features(C1_OUT, nine=True)
    print()
    ra = confirmatory(fa, SEVEN, a.reps, "C1-a  second extractor, the same seven features")
    rb = confirmatory(fb, NINE, a.reps, "C1-b  second extractor, B9 re-applied (nine)")

    # agreement between the two extractors
    r0, r1 = records(f"{P3}/extractor/analysis_population_out.jsonl"), records(C1_OUT[0])
    ids = sorted(set(r0) & set(r1))
    OUT = {"selfcheck": r0c, "a": ra, "b": rb, "agreement": {}, "n_both": len(ids)}
    print(f"\nagreement between the extractors over {len(ids)} reports extracted by both (four-level κ, % agreement)")
    for fld in ["intracranial_haemorrhage", "intraventricular_haemorrhage", "midline_shift_present",
                "cerebral_oedema", "acute_infarction", "mass_effect", "chronic_ischaemic_change"]:
        x, y = [r0[i][fld] for i in ids], [r1[i][fld] for i in ids]
        OUT["agreement"][fld] = cohen_kappa_score(x, y)
        print(f"  {fld:30s} κ {cohen_kappa_score(x, y):.2f}  {100*np.mean([p == q for p, q in zip(x, y)]):5.1f}%")
    for fld, cat in [("haemorrhage_compartment", "intraparenchymal"), ("haemorrhage_compartment", "subarachnoid"),
                     ("infarct_territory", "MCA"), ("infarct_region", "cerebellum"), ("infarct_region", "occipital")]:
        x = [int(cat in (r0[i][fld] or [])) for i in ids]
        y = [int(cat in (r1[i][fld] or [])) for i in ids]
        OUT["agreement"][cat] = cohen_kappa_score(x, y)
        print(f"  {fld + ':' + cat:30s} κ {cohen_kappa_score(x, y):.2f}  {100*np.mean([p == q for p, q in zip(x, y)]):5.1f}%")

    v0 = f0.merge(fa, on=["stay_id", "landmark_idx"], suffixes=("_0", "_1"))
    v0 = v0.merge(pd.read_csv(P3 / "landmark_dataset.csv", usecols=["stay_id", "landmark_idx", "anchor_year_group"]),
                  on=["stay_id", "landmark_idx"])
    v0 = v0[(v0.anchor_year_group == "2017 - 2019") & ((v0.img_available_locked_0 == 1) | (v0.img_available_locked_1 == 1))]
    print(f"\nvalidation landmarks with imaging content under either extractor: {len(v0)}")
    for c in SEVEN:
        x, y = v0[f"{c}_0"], v0[f"{c}_1"]
        diff = ~((x == y) | (x.isna() & y.isna()))
        print(f"  {c:24s} value differs at {100*diff.mean():5.1f}% of them")

    # validation of the second extractor (four-level κ, same rule as extractor/evaluate_validation.py)
    import sys as _s
    _s.path.insert(0, str(HERE))
    from evaluate_binary import annotator
    from evaluate_validation import LEVELS, PRIMARY, SECONDARY
    ann, rv = annotator(), records(HERE / "validation200_c1_out.jsonl")
    common = sorted(set(ann) & set(rv))
    OUT["validation"] = {"scored": len(common), "failed": sum(1 for l in open(HERE / "validation200_c1_out.jsonl")
                                                             if l.strip() and json.loads(l)["error"])}
    for ph in PRIMARY + SECONDARY:
        pairs = [(ann[n].get(ph), rv[n].get(ph)) for n in common]
        pairs = [(x, y) for x, y in pairs if x in LEVELS and y in LEVELS]
        x, y = zip(*pairs)
        OUT["validation"][ph] = cohen_kappa_score(x, y, labels=LEVELS)
    lk = pd.read_csv(HERE / "list_field_kappa_c1.csv")
    for r in lk.itertuples():
        if r.kappa == r.kappa:
            OUT["validation"]["list." + r.category] = r.kappa
    fails = pd.read_csv(HERE / "analysis_population_c1_failed.csv")
    OUT["full_run"] = {"reports": 6994, "extracted": len(r1), "quarantined": len(fails),
                       "quarantined_in_frozen_quarantine": len(set(fails.note_id) & set(
                           pd.read_csv(P3 / "extractor" / "analysis_population_failed.csv").note_id)),
                       "frozen_quarantined": len(pd.read_csv(P3 / "extractor" / "analysis_population_failed.csv")),
                       "all_errors_json": bool((fails.error == "JSONDecodeError").all())}
    freeze = (HERE / "EXTRACTOR_FREEZE_C1.md").read_text(encoding="utf-8")
    import re as _re
    OUT["model"] = {"tag": "qwen3.8:27b", "params_b": 27,
                    "ollama": _re.search(r"Ollama (\d+\.\d+\.\d+)", freeze).group(1),
                    "prompt_version": _re.search(r"\*\*([0-9a-f]{12})\*\*", freeze).group(1)}
    json.dump(OUT, open(HERE / "c1_results.json", "w"), indent=1)
    print("\nwritten: c1_results.json")


if __name__ == "__main__":
    main()
