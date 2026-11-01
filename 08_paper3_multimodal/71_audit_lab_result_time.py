"""
Paper 3 audit B: laboratory values were assigned to 6-h windows by charttime (specimen time), as in
Paper 1's 02_extract_timewindow_variables.py. At landmark L the last value of window L is used. How often
was that value not yet resulted (storetime after the end of window L, i.e. after the landmark)?

Reproduces 02's rule exactly (window = floor((charttime - ICU intime) / 6 h), last value by charttime per
window) for the eight laboratory predictors used in Paper 3, restricted to the analysis patients and to
the landmark windows 0–7. Needs the MIMIC drive. Aggregate output only. Declared in PROJECT_LOG before run.
Writes audit_lab_result_time.csv.
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import sys
import numpy as np
import pandas as pd

ROOT = _REPO_ROOT
sys.path.insert(0, f"{ROOT}/03_code")
from variable_itemid_map import WBC, HEMOGLOBIN, PLATELET, CREATININE, BUN, SODIUM, POTASSIUM, GLUCOSE  # noqa

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import project_paths  # noqa: E402  数据位置在项目根目录的 data_paths.cfg 里设置
BASE = project_paths.MIMIC_IV
P3 = f"{ROOT}/08_paper3_multimodal"
LABS = {"wbc": WBC, "hemoglobin": HEMOGLOBIN, "platelet": PLATELET, "creatinine": CREATININE, "bun": BUN,
        "sodium": SODIUM, "potassium": POTASSIUM, "glucose": GLUCOSE}
item2lab = {i: k for k, ids in LABS.items() for i in ids}

coh = pd.read_csv(f"{ROOT}/04_outputs/tables/patient_level_cohort.csv", usecols=["stay_id", "hadm_id", "intime"],
                  parse_dates=["intime"])
lm = pd.read_csv(f"{P3}/landmark_dataset.csv", usecols=["stay_id", "note_era"])
keep = set(lm[lm.note_era].stay_id)
coh = coh[coh.stay_id.isin(keep)]
intime = coh.set_index("hadm_id").intime
stay_of = coh.set_index("hadm_id").stay_id
hadms = set(coh.hadm_id)

parts = []
for ch in pd.read_csv(f"{BASE}/hosp/labevents.csv.gz", usecols=["hadm_id", "itemid", "charttime", "storetime", "valuenum"],
                      chunksize=3_000_000):
    ch = ch[ch.hadm_id.isin(hadms) & ch.itemid.isin(item2lab) & ch.valuenum.notna()]
    if len(ch):
        parts.append(ch)
lab = pd.concat(parts)
lab["charttime"] = pd.to_datetime(lab.charttime); lab["storetime"] = pd.to_datetime(lab.storetime)
lab["intime"] = lab.hadm_id.map(intime)
lab["window_idx"] = ((lab.charttime - lab.intime).dt.total_seconds() // (6 * 3600))
lab = lab[(lab.window_idx >= 0) & (lab.window_idx <= 7)].copy()
lab["window_idx"] = lab.window_idx.astype(int)
lab["stay_id"] = lab.hadm_id.map(stay_of)
lab["lab"] = lab.itemid.map(item2lab)
last = lab.sort_values("charttime").groupby(["stay_id", "window_idx", "lab"]).tail(1).copy()
last["window_end"] = last.intime + pd.to_timedelta(6 * (last.window_idx + 1), unit="h")
last["late_h"] = (last.storetime - last.window_end).dt.total_seconds() / 3600
last["turnaround_h"] = (last.storetime - last.charttime).dt.total_seconds() / 3600
last["late"] = last.late_h > 0

rows = []
for name, g in [("all eight labs", last)] + list(last.groupby("lab")):
    g = g[g.storetime.notna()]
    rows.append({"lab": name, "values_used": len(g), "resulted_after_landmark_pct": 100 * g.late.mean(),
                 "median_turnaround_h": g.turnaround_h.median(),
                 "median_delay_after_landmark_h_if_late": g.loc[g.late, "late_h"].median(),
                 "p90_delay_after_landmark_h_if_late": g.loc[g.late, "late_h"].quantile(.9)})
out = pd.DataFrame(rows)
out.to_csv(f"{P3}/audit_lab_result_time.csv", index=False)
print(f"storetime missing for {int(last.storetime.isna().sum())} of {len(last)} values")
print(out.round(2).to_string(index=False))
