"""
Paper 3, step 8c preparation: draw the random validation sample of ~200 reports.

VERSION 2 (11 Sep 2026), per protocol v1.2 item D. The sample is drawn from the
reports the landmark analysis can actually use: head CT/MRI reports belonging to the
qualifying admission and stored by the 48 h landmark — the last landmark, so a report
stored later can never be a predictor. Version 1 drew from all tier-A reports of
note-era patients; only 81 of its 200 fell in this population, so it validated the
extractor mostly on reports the analysis never touches. Version 1's index is kept in
annotation_validation/superseded/; nobody had read those reports.

"Belongs to the qualifying admission" uses the corrected rule of script 35: hadm_id
matches the stay's admission, or — with no hadm_id — performed on or after admission.

Still, as in version 1:
  - drawn BEFORE the guideline is frozen, written as an index only (no report text);
    nobody opens these reports until the guideline is frozen
  - excludes the 50 development reports and every report of their patients
  - one report per patient; proportional allocation across subtypes (largest
    remainder); 20% dual-read flagged, proportional within subtype
  - seeded; re-running reproduces the same sample

Writes: annotation_validation/random200_index.csv
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import re
import numpy as np
import pandas as pd

ROOT = _REPO_ROOT
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import project_paths  # noqa: E402  数据位置在项目根目录的 data_paths.cfg 里设置
NOTE = project_paths.MIMIC_NOTE
P3 = f"{ROOT}/08_paper3_multimodal"
SEED, N, DUAL, LAST_LANDMARK_H = 20260911, 200, 0.20, 48
TIER_A = re.compile(r"^(CT HEAD|PORTABLE HEAD CT|MR HEAD|STROKE PROTOCOL \(BRAIN)", re.I)

lm = pd.read_csv(f"{P3}/landmark_dataset.csv")
stays = set(lm[lm.note_era].stay_id)
coh = pd.read_csv(f"{ROOT}/04_outputs/tables/patient_level_cohort.csv",
                  parse_dates=["intime", "admittime"])
coh = coh[coh.stay_id.isin(stays)][["stay_id", "subject_id", "hadm_id", "intime",
                                    "admittime", "stroke_subtype"]]
assert coh.subject_id.is_unique            # one qualifying ICU stay per patient

det = pd.read_csv(f"{NOTE}/radiology_detail.csv.gz", usecols=["note_id", "field_name", "field_value"])
ex = det[det.field_name == "exam_name"]
tier_a = set(ex[ex.field_value.astype(str).str.match(TIER_A)].note_id)

parts = []
for ch in pd.read_csv(f"{NOTE}/radiology.csv.gz",
                      usecols=["note_id", "subject_id", "hadm_id", "charttime", "storetime"],
                      chunksize=500_000):
    parts.append(ch[ch.note_id.isin(tier_a) & ch.subject_id.isin(set(coh.subject_id))])
rad = pd.concat(parts)
for c in ("charttime", "storetime"):
    rad[c] = pd.to_datetime(rad[c])

d = rad.merge(coh.rename(columns={"hadm_id": "stay_hadm"}), on="subject_id")
own = (d.hadm_id == d.stay_hadm) | (d.hadm_id.isna() & (d.charttime >= d.admittime))
d = d[own]
d = d[(d.storetime - d.intime).dt.total_seconds() / 3600 <= LAST_LANDMARK_H]
print(f"analysis population (qualifying admission, stored by the {LAST_LANDMARK_H} h landmark): "
      f"{len(d)} reports / {d.subject_id.nunique()} patients")

dev = pd.read_csv(f"{P3}/annotation_session/session_packet_index.csv")
dev_pts = set(dev.subject_id)
d = d[~d.subject_id.isin(dev_pts)]
print(f"after excluding the development reports' {len(dev_pts)} patients: "
      f"{len(d)} reports / {d.subject_id.nunique()} patients")

one = d.sample(frac=1, random_state=SEED).drop_duplicates("subject_id")
share = one.stroke_subtype.value_counts(normalize=True).sort_index()
raw = share * N
alloc = np.floor(raw).astype(int)
for s in (raw - alloc).sort_values(ascending=False).index[: N - alloc.sum()]:
    alloc[s] += 1

picked = []
for s, n in alloc.items():
    g = one[one.stroke_subtype == s].sample(n, random_state=SEED).copy()
    g["dual_read"] = 0
    g.loc[g.sample(int(round(n * DUAL)), random_state=SEED).index, "dual_read"] = 1
    picked.append(g)
samp = pd.concat(picked)[["note_id", "subject_id", "stroke_subtype", "dual_read"]]
samp = samp.sample(frac=1, random_state=SEED).reset_index(drop=True)
samp.insert(0, "order", range(1, len(samp) + 1))

assert not set(samp.note_id) & set(dev.note_id)
assert not set(samp.subject_id) & dev_pts
assert samp.subject_id.is_unique
out = f"{P3}/annotation_validation/random200_index.csv"
samp.to_csv(out, index=False)
print(f"\nsample v2: {len(samp)} reports, {samp.subject_id.nunique()} patients")
print(pd.DataFrame({"allocated": alloc,
                    "dual_read": samp.groupby("stroke_subtype").dual_read.sum()}).to_string())
print(f"dual-read total: {samp.dual_read.sum()}")
old = pd.read_csv(f"{P3}/annotation_validation/superseded/random200_index_v1.csv")
print(f"overlap with the superseded v1 sample: {samp.note_id.isin(set(old.note_id)).sum()} reports")
print(f"written: {out}  (index only — no report text)")
