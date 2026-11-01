"""
Paper 3: how many radiology reports does the analysis actually need?

M1 uses, at each eligible patient-landmark, the most recent head CT/MRI report that was
clinically available (storetime <= landmark) within the qualifying hospital admission.
Protocol v1.1 §15 step 8f runs the extractor over all 20,947 tier-A reports, which at
~35-40 s/report on this machine is 8-9 days. This counts the reports M1 can ever touch,
so that a restriction (a v1.2 change) can be decided on numbers.

Prints counts only. Writes no report text.
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
NOTE = project_paths.MIMIC_NOTE
P3 = f"{ROOT}/08_paper3_multimodal"
SEC = 39.3                                    # measured mean s/report, extractor v0

lm = pd.read_csv(f"{P3}/landmark_dataset.csv")
lm = lm[lm.note_era]
coh = pd.read_csv(f"{ROOT}/04_outputs/tables/patient_level_cohort.csv",
                  parse_dates=["intime", "admittime"])[["stay_id", "subject_id", "hadm_id", "intime"]]
lm = lm.merge(coh[["stay_id", "hadm_id", "intime"]], on="stay_id")

det = pd.read_csv(f"{NOTE}/radiology_detail.csv.gz", usecols=["note_id", "field_name", "field_value"])
TIER_A = re.compile(r"^(CT HEAD|PORTABLE HEAD CT|MR HEAD|STROKE PROTOCOL \(BRAIN)", re.I)
ex = det[det.field_name == "exam_name"]
tier_a = set(ex[ex.field_value.astype(str).str.match(TIER_A)].note_id)

subs = set(lm.subject_id)
parts = []
for ch in pd.read_csv(f"{NOTE}/radiology.csv.gz",
                      usecols=["note_id", "subject_id", "hadm_id", "storetime"], chunksize=500_000):
    parts.append(ch[ch.note_id.isin(tier_a) & ch.subject_id.isin(subs)])
rad = pd.concat(parts)
rad["storetime"] = pd.to_datetime(rad.storetime)
print(f"tier-A reports of landmark-cohort patients: {len(rad)} "
      f"({rad.hadm_id.isna().mean()*100:.1f}% without hadm_id)")

adm = rad.merge(coh[["hadm_id", "intime", "stay_id"]], on="hadm_id")     # qualifying admission only
adm["h"] = (adm.storetime - adm.intime).dt.total_seconds() / 3600
print(f"  of which in the qualifying admission: {len(adm)}")
upto48 = adm[adm.h <= 48]
print(f"  available by the 48 h landmark (storetime <= ICU admission + 48 h): {len(upto48)}")

# the report actually used at each eligible landmark: most recent available one
used = set()
for (sid, T), _ in lm.groupby(["stay_id", "landmark_h"]):
    c = adm[(adm.stay_id == sid) & (adm.h <= T)]
    if len(c):
        used.add(c.loc[c.storetime.idxmax(), "note_id"])
print(f"  actually used by M1 (most recent available at an eligible landmark): {len(used)}")

val = pd.read_csv(f"{P3}/annotation_validation/random200_index.csv")
dev = pd.read_csv(f"{P3}/annotation_session/session_packet_index.csv")
v_in = val.note_id.isin(set(upto48.note_id)).sum()
print(f"\nrandom-200 reports that fall inside the <=48 h qualifying-admission set: {v_in}/200")
print(f"development-50 reports inside it: {dev.note_id.isin(set(upto48.note_id)).sum()}/50")

for lab, n in [("all 20,947 tier-A reports (protocol v1.1)", 20947),
               ("<=48 h qualifying-admission set", len(upto48)),
               ("reports M1 actually uses", len(used))]:
    print(f"runtime, {lab:42s}: {n:6d} reports ≈ {n*SEC/3600:6.1f} h ≈ {n*SEC/86400:4.1f} days")
