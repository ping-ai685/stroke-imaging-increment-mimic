"""
Paper 3: the landmark analytic dataset. One row = one patient x one landmark.

Time convention (corrected 11 Sep 2026): window w covers [6w, 6w+6) hours from ICU
admission, and the landmark sits at the END of window L, i.e. at 6(L+1) hours. A
24 h horizon therefore spans windows L+1..L+4, which requires L+4 <= 11, so
L = 0..7 and the landmarks are 6, 12, 18, 24, 30, 36, 42 and 48 hours.

Time boundary, applied without exception:
  everything LEFT of the landmark  -> eligibility and predictors
  everything RIGHT of the landmark -> outcome only

Eligibility uses the FILTERED state (Ping's decision, 11 Sep 2026): using the
smoothed state to decide who may enter the risk set would let future windows
determine who the model is allowed to predict for. The outcome is adjudicated
retrospectively from the full-sequence states.

Imaging availability — CORRECTED 11 Sep 2026. A head CT/MRI report belongs to the
qualifying admission if its hadm_id is that admission's hadm_id, or, when the report
carries no hadm_id, if it was performed on or after hospital admission. The first
version required the report timestamp to be >= admittime for every report, which
dropped 1,177 admission-linked reports performed before the admission timestamp —
chiefly the diagnostic scan done in the emergency department. That understated early
imaging availability and fed a faulty img_available into M0+A.

The script no longer depends on intermediate files in a session scratchpad: the
tier-A exam list and the echo events are computed here from the source files.

Writes: 08_paper3_multimodal/landmark_dataset.csv
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
BASE = project_paths.MIMIC_IV
MOD = project_paths.MIMIC_VMAC
TIER_A = re.compile(r"^(CT HEAD|PORTABLE HEAD CT|MR HEAD|STROKE PROTOCOL \(BRAIN)", re.I)
DEST = f"{ROOT}/08_paper3_multimodal"
TARGET = 0          # adverse state: tf_state 0, respiratory-support analogue (pending sign-off)
HORIZON = 4         # windows = 24 h

CONT = ["heart_rate_z", "sbp_z", "map_z", "resp_rate_z", "spo2_z", "temp_c_z",
        "gcs_eye_z", "gcs_motor_z", "urine_output_ml_z", "wbc_z", "hemoglobin_z",
        "platelet_z", "creatinine_z", "bun_z", "sodium_z", "potassium_z", "glucose_z"]
TREAT = ["mech_vent", "crrt", "vasopressor", "sedative"]

# ---------------------------------------------------------------- cohort & timing
coh = pd.read_csv(f"{ROOT}/04_outputs/tables/patient_level_cohort.csv",
                  parse_dates=["intime", "outtime", "admittime", "deathtime"])
yr = pd.read_csv(f"{BASE}/hosp/patients.csv.gz", usecols=["subject_id", "anchor_year_group"])
coh = coh.merge(yr, on="subject_id", how="left")
coh["note_era"] = coh.anchor_year_group != "2020 - 2022"
coh["icu_end_h"] = (coh.outtime - coh.intime).dt.total_seconds() / 3600
death = (coh.deathtime - coh.intime).dt.total_seconds() / 3600
coh["death_h"] = np.where(coh.deathtime.notna(), death,
                          np.where(coh.icu_mortality == 1, coh.icu_end_h, np.nan))

# ---------------------------------------------------------------- states
filt = pd.read_csv(f"{DEST}/tf_filtered_states.csv")
adj = pd.read_csv(f"{DEST}/tf_state_assignments_all.csv")[["stay_id", "window_idx", "tf_state"]]
P = [f"p_state{k}" for k in range(4)]
p = filt[P].values.clip(1e-12, 1)
filt["state_entropy"] = -(p * np.log(p)).sum(axis=1)
ADJ = {(r.stay_id, r.window_idx): r.tf_state for r in adj.itertuples()}

wide = pd.read_csv(f"{ROOT}/04_outputs/tables/timewindow_level_modeling.csv")
W = wide.set_index(["stay_id", "window_idx"])

# ---------------------------------------------------------------- modality timing
def first_times(df, tcol, subs):
    d = df[df.subject_id.isin(subs)].merge(
        coh[["subject_id", "stay_id", "intime", "admittime"]], on="subject_id")
    d = d[d[tcol] >= d.admittime]
    d["h"] = (d[tcol] - d.intime).dt.total_seconds() / 3600
    return d.groupby("stay_id").h.min()

def imaging_times(rad):
    """Earliest storetime of a head CT/MRI report belonging to the qualifying
    admission, in hours from ICU admission (negative = before ICU admission)."""
    d = rad.merge(coh[["subject_id", "stay_id", "hadm_id", "intime", "admittime"]]
                  .rename(columns={"hadm_id": "stay_hadm"}), on="subject_id")
    keep = (d.hadm_id == d.stay_hadm) | (d.hadm_id.isna() & (d.charttime >= d.admittime))
    d = d[keep]
    d["h"] = (d.storetime - d.intime).dt.total_seconds() / 3600
    return d.groupby("stay_id").h.min()

subs = set(coh.subject_id)
det = pd.read_csv(f"{MOD}/note_unzip/note/radiology_detail.csv.gz",
                  usecols=["note_id", "field_name", "field_value"])
ex = det[det.field_name == "exam_name"]
A = set(ex[ex.field_value.astype(str).str.match(TIER_A)].note_id)
rad = []
for ch in pd.read_csv(f"{MOD}/note_unzip/note/radiology.csv.gz",
                      usecols=["note_id", "subject_id", "hadm_id", "charttime", "storetime"],
                      chunksize=500_000):
    rad.append(ch[ch.note_id.isin(A) & ch.subject_id.isin(subs)])
rad = pd.concat(rad)
for c in ("charttime", "storetime"):
    rad[c] = pd.to_datetime(rad[c])
img_h = imaging_times(rad)
ne = set(coh[coh.note_era].stay_id)
print(f"note-era stays with a head CT/MRI report available by ICU admission: "
      f"{(img_h[img_h.index.isin(ne)] <= 0).sum()} / {len(ne)}")

ecg = []
for ch in pd.read_csv(f"{MOD}/mimic-iv-ecg-1.0/machine_measurements.csv",
                      usecols=["subject_id", "ecg_time"], chunksize=200_000, low_memory=False):
    ecg.append(ch[ch.subject_id.isin(subs)])
ecg = pd.concat(ecg); ecg["ecg_time"] = pd.to_datetime(ecg.ecg_time)
ecg_h = first_times(ecg, "ecg_time", subs)

ech = pd.concat(ch.drop_duplicates() for ch in pd.read_csv(
    f"{MOD}/structured-measurement.csv.gz",
    usecols=["subject_id", "measurement_id", "measurement_datetime"], chunksize=2_000_000))
ech = ech.drop_duplicates()
ech["measurement_datetime"] = pd.to_datetime(ech.measurement_datetime)
ech_h = first_times(ech, "measurement_datetime", subs)

# ---------------------------------------------------------------- assemble
base = coh.set_index("stay_id")
rows = []
n_dead = 0                                                # landmarks excluded under D1
for r in filt.itertuples():
    L = r.window_idx
    if L > 11 - HORIZON:                                  # horizon must fit in 72 h
        continue
    if r.filtered_state == TARGET:                        # eligibility: filtered state
        continue
    b = base.loc[r.stay_id]
    T = 6 * (L + 1)
    if pd.notna(b.death_h) and b.death_h <= T:             # protocol v1.4 D1: alive at the landmark
        n_dead += 1
        continue
    fut = [ADJ.get((r.stay_id, k)) for k in range(L + 1, L + 1 + HORIZON)]
    adverse = TARGET in [s for s in fut if s is not None]
    dh = b.death_h
    died = bool(pd.notna(dh) and T <= dh < T + 24)
    left = bool(b.icu_end_h < T + 24 and not died)
    try:
        w = W.loc[(r.stay_id, L)]
    except KeyError:
        continue
    row = {"stay_id": r.stay_id, "subject_id": b.subject_id, "landmark_idx": L,
           "landmark_h": T, "note_era": b.note_era, "anchor_year_group": b.anchor_year_group,
           "split_paper1": w.split, "stroke_subtype": b.stroke_subtype,
           "age": b.age_at_adm_capped, "gender": b.gender, "charlson": b.charlson_index,
           "hypertension": b.hypertension, "diabetes": b.diabetes,
           "atrial_fibrillation": b.atrial_fibrillation, "heart_failure": b.heart_failure,
           "ckd": b.ckd,
           "filtered_state": r.filtered_state, "state_entropy": r.state_entropy,
           "adj_state_at_landmark": ADJ.get((r.stay_id, L)),
           "future_24h_adverse": int(adverse),
           "future_24h_death": int(died),
           "composite_event": int(adverse or died),
           "icu_discharge_before_24h": int(left),
           "img_available": int(img_h.get(r.stay_id, np.inf) <= T),
           "ecg_available": int(ecg_h.get(r.stay_id, np.inf) <= T),
           "echo_available": int(ech_h.get(r.stay_id, np.inf) <= T)}
    for k in range(4):
        row[f"p_state{k}"] = getattr(r, f"p_state{k}")
    for c in CONT + TREAT:
        row[c] = w[c]
    rows.append(row)

d = pd.DataFrame(rows)
print(f"D1: {n_dead} candidate landmarks excluded because the patient had died at or before the landmark")
d.to_csv(f"{DEST}/landmark_dataset.csv", index=False)
print(f"landmark dataset: {len(d)} rows, {d.stay_id.nunique()} stays")
ne = d[d.note_era]
print(f"note era (2008-2019): {len(ne)} rows, {ne.stay_id.nunique()} stays\n")
g = ne.groupby("landmark_h").agg(
    at_risk=("stay_id", "size"), adverse=("future_24h_adverse", "sum"),
    death=("future_24h_death", "sum"), composite=("composite_event", "sum"),
    left_icu=("icu_discharge_before_24h", "sum"),
    img=("img_available", "mean"), ecg=("ecg_available", "mean"), echo=("echo_available", "mean"))
g["composite_%"] = 100 * g.composite / g.at_risk
for c in ["img", "ecg", "echo"]:
    g[c] = (100 * g[c]).round(1)
print(g.round(1).to_string())
print(f"\nunique patients with >=1 composite event: "
      f"{ne[ne.composite_event == 1].stay_id.nunique()}")
print(f"pooled composite event rate: {100*ne.composite_event.mean():.1f}%")
print(f"\nSaved: {DEST}/landmark_dataset.csv")
