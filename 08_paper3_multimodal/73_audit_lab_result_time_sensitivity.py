"""
Paper 3 audit sensitivity analysis B2: laboratory values by RESULT time (declared in PROJECT_LOG before running).

Paper 1 assigned each laboratory value to the 6-h window of its specimen time (charttime). Audit B found that
17.4% of the values used at a landmark were resulted after it. Here the eight laboratory variables are rebuilt
with the window of their result time (storetime), so nothing resulted after a landmark is used at it.

Everything downstream is Paper 1's rule, unchanged and with Paper 1's fitted quantities:
  tier-1 impossible-value bounds (02b) -> forward fill, limit 2 windows (03) -> Paper 1 training medians (03)
  -> Paper 1 z-score parameters (04) -> frozen treatment-free HMM forward pass (34).
Outcome, eligibility (same landmark rows), imaging features, models, split and bootstrap are the primary
analysis's. Only the predictor side changes: the eight laboratory predictors and the filtered state.

Before rebuilding, the script reproduces Paper 1's own charttime values and the modelling table's laboratory
z-scores from the same code path, and stops if it cannot: a sensitivity analysis built on a pipeline that does
not reproduce the original would compare two different things.

Needs the MIMIC drive and the project .venv (frozen HMM):  ../.venv/bin/python 73_audit_lab_result_time_sensitivity.py
Writes aggregate output only: audit_lab_result_time_sensitivity.csv
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import importlib.util
import sys
import warnings

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import roc_auc_score

ROOT = _REPO_ROOT
sys.path.insert(0, f"{ROOT}/03_code")
from variable_itemid_map import WBC, HEMOGLOBIN, PLATELET, CREATININE, BUN, SODIUM, POTASSIUM, GLUCOSE  # noqa

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import project_paths  # noqa: E402  数据位置在项目根目录的 data_paths.cfg 里设置
BASE = project_paths.MIMIC_IV
T = f"{ROOT}/04_outputs/tables"
P3 = f"{ROOT}/08_paper3_multimodal"
FROZEN = f"{ROOT}/07_paper2_eicu/frozen_params_treatment_free"
REPS, SEED = 2000, 20260917
N_WINDOWS, WH = 12, 6

LABS = {"wbc": WBC, "hemoglobin": HEMOGLOBIN, "platelet": PLATELET, "creatinine": CREATININE, "bun": BUN,
        "sodium": SODIUM, "potassium": POTASSIUM, "glucose": GLUCOSE}
BOUNDS = {"wbc": (0, 100), "hemoglobin": (2, 20), "platelet": (0, 2000), "creatinine": (0, 20),
          "bun": (0, 200), "sodium": (100, 200), "potassium": (1, 10), "glucose": (0, 1500)}   # 02b tier 1
FFILL = 2                                                                                     # 03, labs
item2lab = {i: k for k, ids in LABS.items() for i in ids}
LZ = [f"{v}_z" for v in LABS]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


S48 = _load("s48", f"{P3}/48_sensitivity_analyses.py")
M1 = S48.M1

# ------------------------------------------------------------------ Paper 1 quantities
raw = pd.read_csv(f"{T}/timewindow_level_raw.csv").sort_values(["stay_id", "window_idx"])
mod = pd.read_csv(f"{T}/timewindow_level_modeling.csv").sort_values(["stay_id", "window_idx"])
split = pd.read_csv(f"{T}/patient_train_test_split.csv")
coh = pd.read_csv(f"{T}/patient_level_cohort.csv", usecols=["stay_id", "subject_id", "hadm_id", "intime"],
                  parse_dates=["intime"])
zp = pd.read_csv(f"{T}/standardization_params.csv", index_col=0)
raw = raw.merge(coh[["stay_id", "subject_id"]], on="stay_id").merge(split[["subject_id", "split"]], on="subject_id")


def impute_scale(w, medians=None):
    """03 (forward fill, then training median) and 04 (z-score) for the eight labs; returns z columns."""
    w = w.sort_values(["stay_id", "window_idx"]).copy()
    med = {} if medians is None else medians
    for v in LABS:
        w[v] = w.groupby("stay_id")[v].ffill(limit=FFILL)
        if medians is None:
            med[v] = w.loc[w.split == "train", v].median()
        w[v] = w[v].fillna(med[v])
        w[f"{v}_z"] = (w[v] - zp.loc[v, "mean"]) / zp.loc[v, "std"]
    return w, med


# check 1: Paper 1's imputation and scaling reproduce the modelling table
rep, MED = impute_scale(raw)
chk = rep[["stay_id", "window_idx"] + LZ].merge(mod[["stay_id", "window_idx"] + LZ], on=["stay_id", "window_idx"],
                                                suffixes=("", "_orig"))
d1 = max(float((chk[c] - chk[f"{c}_orig"]).abs().max()) for c in LZ)
print(f"[check 1] Paper 1 impute+scale reproduces the modelling table: max |Δz| = {d1:.2e} over {len(chk)} windows")
assert len(chk) == len(mod) and d1 < 1e-6

# ------------------------------------------------------------------ analysis stays, labevents
lmd = pd.read_csv(f"{P3}/landmark_dataset.csv")
stays = set(lmd[lmd.note_era].stay_id)
c = coh[coh.stay_id.isin(stays)]
intime, stay_of = c.set_index("hadm_id").intime, c.set_index("hadm_id").stay_id
parts = []
for ch in pd.read_csv(f"{BASE}/hosp/labevents.csv.gz", usecols=["hadm_id", "itemid", "charttime", "storetime", "valuenum"],
                      chunksize=3_000_000):
    ch = ch[ch.hadm_id.isin(intime.index) & ch.itemid.isin(item2lab)]
    if len(ch):
        parts.append(ch)
lab = pd.concat(parts, ignore_index=True)
lab["charttime"] = pd.to_datetime(lab.charttime)
lab["storetime"] = pd.to_datetime(lab.storetime)
lab["stay_id"] = lab.hadm_id.map(stay_of)
lab["lab"] = lab.itemid.map(item2lab)
it = lab.hadm_id.map(intime)


def win(t):
    w = ((t - it).dt.total_seconds() // (WH * 3600))
    return w.where((w >= 0) & (w < N_WINDOWS))


lab["w_chart"] = win(lab.charttime)
lab["w_store"] = win(lab.storetime)
lab = lab[lab.w_chart.notna() & lab.valuenum.notna()]          # 02: the specimen set is unchanged
print(f"laboratory values in the analysis stays' windows: {len(lab):,}; storetime missing: {int(lab.storetime.isna().sum())}")


def to_wide(wcol, sortcol):
    x = lab[lab[wcol].notna()].sort_values(sortcol)
    x = x.groupby(["stay_id", wcol, "lab"]).valuenum.last().unstack("lab").reset_index()
    x = x.rename(columns={wcol: "window_idx"})
    x["window_idx"] = x.window_idx.astype(int)
    for v, (lo, hi) in BOUNDS.items():                           # 02b tier 1
        x.loc[~x[v].between(lo, hi), v] = np.nan
    return x


# check 2: the charttime rule reproduces Paper 1's raw laboratory values for these stays
base = raw[raw.stay_id.isin(stays)][["stay_id", "window_idx", "subject_id", "split"]]
old = base.merge(to_wide("w_chart", "charttime"), on=["stay_id", "window_idx"], how="left")
ref = raw[raw.stay_id.isin(stays)][["stay_id", "window_idx"] + list(LABS)]
cmp_ = old.merge(ref, on=["stay_id", "window_idx"], suffixes=("", "_p1"))
agree = np.mean([((cmp_[v] - cmp_[f"{v}_p1"]).abs().lt(1e-9) | (cmp_[v].isna() & cmp_[f"{v}_p1"].isna())).mean()
                 for v in LABS])
print(f"[check 2] charttime rule reproduces Paper 1's raw lab cells: {100 * agree:.3f}% of {len(cmp_) * len(LABS):,}")
assert agree > 0.999

# ------------------------------------------------------------------ rebuild by result time
new = base.merge(to_wide("w_store", "storetime"), on=["stay_id", "window_idx"], how="left")
moved = np.mean([(new[v].fillna(-1) != old[v].fillna(-1)).mean() for v in LABS])
print(f"window-level lab cells that change under the result-time rule: {100 * moved:.1f}%")
new, _ = impute_scale(new, MED)

FEAT = pd.read_csv(f"{FROZEN}/feature_order.csv").sort_values("position").feature.tolist()
model = torch.load(f"{FROZEN}/.model_k4_treatment_free.pt", weights_only=False)
emis = mod[mod.stay_id.isin(stays)].drop(columns=LZ).merge(new[["stay_id", "window_idx"] + LZ],
                                                           on=["stay_id", "window_idx"], how="left")
assert emis[FEAT].notna().all().all()
rows = []
for sid, g in emis.sort_values(["stay_id", "window_idx"]).groupby("stay_id", sort=False):
    X = torch.tensor(g[FEAT].values, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        a = model.forward(X)[0].numpy()
    p = np.exp(a - a.max(axis=1, keepdims=True))
    p /= p.sum(axis=1, keepdims=True)
    rows.append(pd.DataFrame({"stay_id": sid, "landmark_idx": g.window_idx.values, "filtered_state": p.argmax(1),
                              **{f"p_state{k}": p[:, k] for k in range(4)}}))
filt = pd.concat(rows, ignore_index=True)
q = filt[[f"p_state{k}" for k in range(4)]].values.clip(1e-12, 1)
filt["state_entropy"] = -(q * np.log(q)).sum(axis=1)                       # as 35

# check 3: the same forward pass on the unmodified emissions reproduces the stored filtered posteriors
orig = pd.read_csv(f"{P3}/tf_filtered_states.csv")
g0 = mod[mod.stay_id == sorted(stays)[0]].sort_values("window_idx")
with torch.no_grad():
    a0 = model.forward(torch.tensor(g0[FEAT].values, dtype=torch.float32).unsqueeze(0))[0].numpy()
p0 = np.exp(a0 - a0.max(1, keepdims=True)); p0 /= p0.sum(1, keepdims=True)
o0 = orig[orig.stay_id == g0.stay_id.iloc[0]].sort_values("window_idx")[[f"p_state{k}" for k in range(4)]].values
print(f"[check 3] forward pass reproduces stored filtered posteriors: max |Δp| = {np.abs(p0 - o0).max():.1e}")
assert np.abs(p0 - o0).max() < 1e-5

# ------------------------------------------------------------------ same landmarks, new predictors
dev0, val0 = S48.base_frames()
swap = filt.merge(new[["stay_id", "window_idx"] + LZ].rename(columns={"window_idx": "landmark_idx"}),
                  on=["stay_id", "landmark_idx"])
SW = [f"p_state{k}" for k in range(4)] + ["state_entropy", "filtered_state"] + LZ


def swapped(f):
    g = f.drop(columns=SW).merge(swap, on=["stay_id", "landmark_idx"], how="left", validate="one_to_one")
    assert len(g) == len(f) and g[SW].notna().all().all()
    return M1.derive(g)


dev1, val1 = swapped(dev0), swapped(val0)
ch_state = (val1.set_index(["stay_id", "landmark_idx"]).filtered_state
            != val0.set_index(["stay_id", "landmark_idx"]).filtered_state).mean()
print(f"validation landmarks whose filtered state changes: {100 * ch_state:.1f}%")

warnings.filterwarnings("ignore")
BASECOLS = S48.FIXED + S48.STATE + S48.PHYS + ["img_available"]
out = []
for tag, dv, vl in [("as analysed (specimen time)", dev0, val0), ("laboratory values by result time", dev1, val1)]:
    rng = np.random.default_rng(SEED)
    v = S48.fit_pair(dv, vl, BASECOLS, S48.IMGCOLS)
    obs, lo, hi, n, ev = S48.delta(v, "composite_event", REPS, rng)
    out.append({"condition": tag, "landmarks": n, "events": ev,
                "auroc_M0A": roc_auc_score(v.composite_event, v["M0+A"]),
                "auroc_M1D": roc_auc_score(v.composite_event, v["M1-D"]),
                "capture_M0A": M1.topk_capture(v, "M0+A", 0.10)[0],
                "capture_M1D": M1.topk_capture(v, "M1-D", 0.10)[0],
                "delta_pp": obs, "lo": lo, "hi": hi})
res = pd.DataFrame(out)
res.to_csv(f"{P3}/audit_lab_result_time_sensitivity.csv", index=False)
print()
print(res.round(3).to_string(index=False))
print(f"\nreading rule: upper limit {res.hi.iloc[1]:.2f} {'<' if res.hi.iloc[1] < 5 else '>='} 5 pp")
