"""
Paper 3: merge the extracted imaging features into the landmark dataset.

Implements the update rule locked on 16 September 2026 under §8.2, which reserved it
("the most recent clinically available report before the landmark is used, under update rules
that distinguish static from evolving findings; those rules are locked before modelling").

The rule
  1. Eligibility. A report may be used at a landmark if it belongs to the qualifying admission
     (already true of the analysis population, B3/B4), its storetime is at or before the
     landmark, and its storetime is NOT earlier than 72 h before ICU admission. The floor
     excludes scans from earlier in a long admission, before the stroke: 2.6% of reports are
     stored more than 72 h before ICU admission, the earliest 52 days.
  2. Evolving findings — haemorrhage, intraventricular haemorrhage, midline shift, and the
     haemorrhage compartments — are read from the MOST RECENT eligible report only. A finding
     absent from the latest scan is absent now.
  3. Static findings — infarct territory and region — are EVER-POSITIVE across eligible
     reports: a lesion's location does not disappear, and follow-up scans often do not restate
     it.
  4. Encoding (§8.1, frozen): Present -> 1, Absent -> 0, Uncertain and Not assessable ->
     unknown (NaN), never 0. List categories are positive when the category is listed; they are
     unknown when their parent assertion is unknown (compartments under intracranial
     haemorrhage, territory and region under acute infarction).
  5. A report whose extraction failed (the quarantine) carries no features and is treated as if
     it were not there, so the landmark falls back to an earlier eligible report or has no
     imaging. Extraction failure is never read as a negative finding.

`img_available_locked` is availability under this rule; the dataset's existing `img_available`
is left untouched so the two can be compared.

Writes landmark_imaging_features.csv. Prints counts only — never report text.
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import json

import numpy as np
import pandas as pd

P3 = _REPO_ROOT + "/08_paper3_multimodal"
FLOOR_H = -72.0

EVOLVING = {"haem_present": "intracranial_haemorrhage",
            "ivh_present": "intraventricular_haemorrhage",
            "mls_present": "midline_shift_present"}
COMPARTMENTS = {"haem_intraparenchymal": "intraparenchymal", "haem_subarachnoid": "subarachnoid"}
STATIC_LISTS = {"infarct_mca": ("infarct_territory", "MCA"),
                "infarct_cerebellum": ("infarct_region", "cerebellum")}
UNKNOWN = ("Uncertain", "Not assessable")

# B9 designated these four primary phenotypes, which failed κ >= 0.60, for sensitivity analysis
# only. They enter nothing but the extended-feature-set variant.
EXTENDED_EVOLVING = {"infarct_acute_present": "acute_infarction",
                     "oedema_present": "cerebral_oedema",
                     "mass_effect_present": "mass_effect"}
EXTENDED_STATIC = {"chronic_isch_present": "chronic_ischaemic_change"}


def code(level, uncertain_positive=False):
    """Present -> 1, Absent -> 0, Uncertain / Not assessable -> unknown (§8.1).

    uncertain_positive is the §8.1 sensitivity analysis: Uncertain -> 1, Not assessable stays
    unknown.
    """
    if level == "Present" or (uncertain_positive and level == "Uncertain"):
        return 1.0
    if level == "Absent":
        return 0.0
    return np.nan


def build(floor_h=FLOOR_H, age_cap=None, verbose=True, uncertain_positive=False, extended=False):
    """Build the landmark imaging feature table under one update rule.

    floor_h   earliest admissible storetime, in hours from ICU admission (the locked rule
              uses -72). age_cap, when given, additionally requires the report to be at most
              that many hours old at the landmark. Sensitivity analysis 8 of §12.1 varies both;
              the locked rule is the default and is what landmark_imaging_features.csv holds.
    uncertain_positive  the §8.1 sensitivity analysis (see code()).
    extended  also build the four B9-failed phenotypes, under the same static / evolving rule.
    Both default to False, and with all defaults the output is the locked feature table.
    """
    unknown_levels = ("Not assessable",) if uncertain_positive else UNKNOWN
    recs = {}
    with open(f"{P3}/extractor/analysis_population_out.jsonl", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                if not r["error"]:
                    recs[r["note_id"]] = r["record"]
    quarantined = set(pd.read_csv(f"{P3}/extractor/analysis_population_failed.csv").note_id)
    if verbose:
        print(f"extracted records {len(recs)} | quarantined {len(quarantined)}")

    idx = pd.read_csv(f"{P3}/analysis_population_index.csv")
    idx = idx[idx.note_id.isin(recs)]                      # quarantined reports carry no features
    idx = idx[idx.hours_from_icu_admission >= floor_h]      # rule 1, the floor
    if verbose:
        print(f"reports eligible after the {floor_h:.0f} h floor: {len(idx)}")

    lm = pd.read_csv(f"{P3}/landmark_dataset.csv",
                     usecols=["stay_id", "landmark_idx", "landmark_h", "note_era", "img_available"])
    lm = lm[lm.note_era].copy()

    pairs = lm.merge(idx[["stay_id", "note_id", "hours_from_icu_admission"]], on="stay_id", how="left")
    pairs = pairs[pairs.hours_from_icu_admission <= pairs.landmark_h]
    if age_cap is not None:
        pairs = pairs[(pairs.landmark_h - pairs.hours_from_icu_admission) <= age_cap]
    pairs = pairs.sort_values("hours_from_icu_admission")

    rows = []
    for (stay, li), g in pairs.groupby(["stay_id", "landmark_idx"], sort=False):
        latest = recs[g.note_id.iloc[-1]]
        out = {"stay_id": stay, "landmark_idx": li,
               "img_available_locked": 1,
               "img_n_reports": len(g),
               "img_report_age_h": float(g.landmark_h.iloc[-1] - g.hours_from_icu_admission.iloc[-1])}

        for name, field in EVOLVING.items():                       # rule 2
            out[name] = code(latest[field], uncertain_positive)
        haem_unknown = latest["intracranial_haemorrhage"] in unknown_levels
        for name, cat in COMPARTMENTS.items():
            out[name] = np.nan if haem_unknown else float(cat in (latest["haemorrhage_compartment"] or []))

        seen = [recs[n] for n in g.note_id]
        for name, (field, cat) in STATIC_LISTS.items():            # rule 3
            ever = any(cat in (r[field] or []) for r in seen)
            unknown = all(r["acute_infarction"] in unknown_levels for r in seen)
            out[name] = np.nan if (unknown and not ever) else float(ever)

        if extended:
            for name, field in EXTENDED_EVOLVING.items():
                out[name] = code(latest[field], uncertain_positive)
            for name, field in EXTENDED_STATIC.items():
                codes = [code(r[field], uncertain_positive) for r in seen]
                out[name] = (1.0 if 1.0 in codes else 0.0 if 0.0 in codes else np.nan)
        rows.append(out)

    feat = pd.DataFrame(rows)
    out = lm.merge(feat, on=["stay_id", "landmark_idx"], how="left")
    out["img_available_locked"] = out.img_available_locked.fillna(0).astype(int)
    return out


def main():
    out = build()
    out.to_csv(f"{P3}/landmark_imaging_features.csv", index=False)

    n = len(out)
    print(f"\nlandmark rows (note era) {n} | stays {out.stay_id.nunique()}")
    print(f"img_available (dataset, no floor) {int(out.img_available.sum()):6d}  {100*out.img_available.mean():5.2f}%")
    print(f"img_available_locked             {int(out.img_available_locked.sum()):6d}  "
          f"{100*out.img_available_locked.mean():5.2f}%")
    a = out[out.img_available_locked == 1]
    print(f"\nreport age at landmark: median {a.img_report_age_h.median():.1f} h | "
          f"p95 {a.img_report_age_h.quantile(.95):.1f} h | max {a.img_report_age_h.max():.1f} h")
    print(f"reports used per landmark: median {a.img_n_reports.median():.0f} | max {a.img_n_reports.max():.0f}")
    print(f"\n{'feature':24s} {'positive':>9} {'negative':>9} {'unknown':>8}  of imaging landmarks")
    for c in list(EVOLVING) + list(COMPARTMENTS) + list(STATIC_LISTS):
        pos = int((a[c] == 1).sum()); neg = int((a[c] == 0).sum()); unk = int(a[c].isna().sum())
        print(f"{c:24s} {pos:9d} {neg:9d} {unk:8d}  {100*pos/len(a):5.2f}% positive")
    print(f"\nwritten: {P3}/landmark_imaging_features.csv")


if __name__ == "__main__":
    main()
