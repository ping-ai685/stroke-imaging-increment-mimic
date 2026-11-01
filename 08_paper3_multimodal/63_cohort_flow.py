"""
Paper 3: cohort flow counts for Figure 1, from the source files.

Needs the MIMIC-IV drive (patients.csv.gz carries the anchor year group for every patient in the source
cohort, including those who never reach a landmark). Writes cohort_flow_paper3.csv so that 53 and the
figure can be rebuilt without the drive.
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import pandas as pd

ROOT = _REPO_ROOT
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import project_paths  # noqa: E402  数据位置在项目根目录的 data_paths.cfg 里设置
BASE = project_paths.MIMIC_IV
P3 = f"{ROOT}/08_paper3_multimodal"

coh = pd.read_csv(f"{ROOT}/04_outputs/tables/patient_level_cohort.csv", usecols=["stay_id", "subject_id"])
assert coh.stay_id.is_unique and coh.subject_id.is_unique, "source cohort is one ICU stay per patient"
yr = pd.read_csv(f"{BASE}/hosp/patients.csv.gz", usecols=["subject_id", "anchor_year_group"])
coh = coh.merge(yr, on="subject_id", how="left", validate="one_to_one")
assert coh.anchor_year_group.notna().all()
late = coh.anchor_year_group == "2020 - 2022"

lm = pd.read_csv(f"{P3}/landmark_dataset.csv", usecols=["stay_id", "note_era", "anchor_year_group"])
eligible = set(lm[lm.note_era].stay_id)
era = coh[~late]
rows = [
    ("source_cohort", len(coh)),
    ("excluded_2020_2022", int(late.sum())),
    ("note_era_patients", len(era)),
    ("excluded_no_eligible_landmark", int((~era.stay_id.isin(eligible)).sum())),
    ("analysis_patients", int(era.stay_id.isin(eligible).sum())),
]
out = pd.DataFrame(rows, columns=["stage", "n"])
assert out.set_index("stage").n["analysis_patients"] == lm[lm.note_era].stay_id.nunique()
assert out.n[0] == out.n[1] + out.n[2] and out.n[2] == out.n[3] + out.n[4]
out.to_csv(f"{P3}/cohort_flow_paper3.csv", index=False)
print(out.to_string(index=False))
