"""
Paper 3: timing index for the analysis-population reports.

Extraction needs only the text (already in analysis_population_input.csv), but assigning each
report to a landmark later needs its timestamps. Building this now means the drive is not needed
again for extraction or modelling.

Writes: 08_paper3_multimodal/analysis_population_index.csv
  note_id, subject_id, stay_id, charttime, storetime, hours_from_icu_admission
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import re
import pandas as pd

ROOT = _REPO_ROOT
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import project_paths  # noqa: E402  数据位置在项目根目录的 data_paths.cfg 里设置
BASE = project_paths.MIMIC_IV
NOTE = project_paths.MIMIC_NOTE
P3 = f"{ROOT}/08_paper3_multimodal"

want = set(pd.read_csv(f"{P3}/analysis_population_input.csv", usecols=["note_id"]).note_id)
coh = pd.read_csv(f"{ROOT}/04_outputs/tables/patient_level_cohort.csv", parse_dates=["intime", "admittime"])
yr = pd.read_csv(f"{BASE}/hosp/patients.csv.gz", usecols=["subject_id", "anchor_year_group"])
coh = coh.merge(yr, on="subject_id").query("anchor_year_group != '2020 - 2022'")

keep = [ch[ch.note_id.isin(want)] for ch in
        pd.read_csv(f"{NOTE}/radiology.csv.gz",
                    usecols=["note_id", "subject_id", "hadm_id", "charttime", "storetime"],
                    chunksize=200_000)]
rad = pd.concat(keep)
for c in ("charttime", "storetime"):
    rad[c] = pd.to_datetime(rad[c])
d = rad.merge(coh[["subject_id", "stay_id", "intime"]], on="subject_id").drop_duplicates("note_id")
d["hours_from_icu_admission"] = (d.storetime - d.intime).dt.total_seconds() / 3600
out = d[["note_id", "subject_id", "stay_id", "charttime", "storetime", "hours_from_icu_admission"]]
out.to_csv(f"{P3}/analysis_population_index.csv", index=False)
assert set(out.note_id) == want, f"{len(want - set(out.note_id))} reports missing timing"
print(f"{len(out)} reports indexed, {out.stay_id.nunique()} stays | storetime relative to ICU admission: "
      f"min {out.hours_from_icu_admission.min():.1f} h, median {out.hours_from_icu_admission.median():.1f} h, "
      f"max {out.hours_from_icu_admission.max():.1f} h")
print(f"available before each landmark: " + ", ".join(
    f"{h}h {(out.hours_from_icu_admission <= h).sum()}" for h in (6, 12, 24, 48)))
