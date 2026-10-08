"""
Paper 3, Phase 1 + Phase 2 combined: for each landmark, the size of the risk set,
the number of incident transitions in the next 24 h, and what fraction of THOSE
AT-RISK patients actually have each modality available at that moment.

Coverage computed over the risk set, not over the whole cohort: a modality's
usefulness depends on how often it is present for the patients a model is being
asked to make a prediction about.

Availability rules, all "by the landmark, not merely during the stay":
  head CT/MRI  storetime <= landmark   (the report does not exist until written;
                                        storetime - charttime is a median 2.25 h)
  ECG          ecg_time  <= landmark   (machine measurements are automatic)
  echo         measurement_datetime <= landmark
All three additionally require the study to belong to this hospital admission.
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
MOD = project_paths.MIMIC_VMAC
SCR = "/private/tmp/claude-501/-Users-pinglei-de-coach-claude-playground-mini-translator/e0533350-af3c-4a6e-9d51-2ad78c46ba33/scratchpad"
DEST = f"{ROOT}/08_paper3_multimodal"
TARGET = 0

coh = pd.read_csv(f"{ROOT}/04_outputs/tables/patient_level_cohort.csv",
                  parse_dates=["intime", "admittime"])
pat = pd.read_csv(f"{BASE}/hosp/patients.csv.gz", usecols=["subject_id", "anchor_year_group"])
coh = coh.merge(pat, on="subject_id").query("anchor_year_group != '2020 - 2022'")
key = coh[["stay_id", "subject_id", "intime", "admittime"]]

a = pd.read_csv(f"{DEST}/tf_state_assignments_all.csv")
a = a[a.stay_id.isin(set(coh.stay_id))]
S = {sid: dict(zip(g.window_idx, g.tf_state)) for sid, g in a.groupby("stay_id")}

def hours(df, tcol):
    m = df.merge(key, on="subject_id")
    m = m[m[tcol] >= m.admittime]
    m["h"] = (m[tcol] - m.intime).dt.total_seconds() / 3600
    return m[["stay_id", "h"]]

rad = pd.read_csv(f"{SCR}/cohort_radiology_index2.csv", parse_dates=["charttime"])
store = []
A = set(pd.read_csv(f"{SCR}/tierA_notes.csv").note_id)
for ch in pd.read_csv(f"{MOD}/note_unzip/note/radiology.csv.gz",
                      usecols=["note_id", "subject_id", "charttime", "storetime"], chunksize=200_000):
    store.append(ch[ch.note_id.isin(A) & ch.subject_id.isin(set(coh.subject_id))])
rad = pd.concat(store)
rad["storetime"] = pd.to_datetime(rad.storetime); rad["charttime"] = pd.to_datetime(rad.charttime)
img = hours(rad.rename(columns={"charttime": "_c"}), "storetime")

ecg = []
for ch in pd.read_csv(f"{MOD}/mimic-iv-ecg-1.0/machine_measurements.csv",
                      usecols=["subject_id", "ecg_time"], chunksize=200_000, low_memory=False):
    ecg.append(ch[ch.subject_id.isin(set(coh.subject_id))])
ecg = pd.concat(ecg); ecg["ecg_time"] = pd.to_datetime(ecg.ecg_time)
ecg = hours(ecg, "ecg_time")

ech = pd.read_csv(f"{SCR}/echo_events.csv", parse_dates=["measurement_datetime"])
ech = hours(ech[ech.subject_id.isin(set(coh.subject_id))], "measurement_datetime")

rows = []
for L in range(0, 8):
    cut = L * 6
    atrisk = {sid for sid, w in S.items() if w.get(L) is not None and w[L] != TARGET}
    ev = sum(1 for sid in atrisk
             if TARGET in [S[sid][k] for k in range(L + 1, L + 5) if k in S[sid]])
    cov = {}
    for name, d in [("imaging", img), ("ecg", ecg), ("echo", ech)]:
        cov[name] = len(set(d[d.h <= cut].stay_id) & atrisk)
    allthree = len(set(img[img.h <= cut].stay_id) & set(ecg[ecg.h <= cut].stay_id)
                   & set(ech[ech.h <= cut].stay_id) & atrisk)
    n = len(atrisk)
    rows.append((L, cut, n, ev, 100 * ev / n,
                 cov["imaging"], 100 * cov["imaging"] / n,
                 cov["ecg"], 100 * cov["ecg"] / n,
                 cov["echo"], 100 * cov["echo"] / n,
                 allthree, 100 * allthree / n))
t = pd.DataFrame(rows, columns=["LM", "h", "at_risk", "events_24h", "event_%",
                                "imaging_n", "imaging_%", "ecg_n", "ecg_%",
                                "echo_n", "echo_%", "all3_n", "all3_%"])
print(t.to_string(index=False, float_format=lambda x: f"{x:.1f}"))
t.to_csv(f"{DEST}/landmark_feasibility.csv", index=False)
print(f"\nSaved: {DEST}/landmark_feasibility.csv")
