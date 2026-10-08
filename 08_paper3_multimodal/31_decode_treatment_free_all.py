"""
Paper 3, Phase 1: decode the FULL cohort into treatment-free states.

Paper 1's treatment-free model (11_sensitivity_no_treatment_vars.py) was only ever
fit and labelled on the training split -- 4457 of the 6368 stays. Paper 3 makes the
treatment-free state the PRIMARY endpoint, so every patient needs a label, not just
the ones the model was fit on.

The frozen parameters in 07_paper2_eicu/frozen_params_treatment_free/ reproduce the
published train labels exactly (reproduction_check.csv: exact agreement 1.0 over
43,261 windows), so the held-out patients can be decoded with them without leakage,
exactly as 09_decode_test_set.py does for the primary model.

Protocol v1.4, D1 (4 Oct 2026). Windows run to ICU discharge, and for some deaths the recorded
discharge is later than the recorded death, so windows exist after death; their values are mostly
imputed. Full-sequence decoding uses later windows, so they could change the state assigned to
windows before the death, and hence the outcome. The OUTPUT labels are therefore decoded on
sequences truncated after the window containing a death within 72 h (windows with index >
floor(death hours / 6) removed) — the rule adopted in the revision of the earlier study. The
reproduction check against the published labels is still run on the untruncated sequences, since
that is what it verifies.

The same truncation is applied to the earlier study's primary (21-variable) model, which supplies
the outcome of sensitivity analysis 3; its labels are re-decoded here from the frozen .model_k4.pt
and must reproduce hmm_state_assignments_all.csv exactly on the untruncated sequences.

Writes: 08_paper3_multimodal/tf_state_assignments_all.csv
        08_paper3_multimodal/p1_state_assignments_truncated.csv
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import sys

import numpy as np
import pandas as pd
import torch

ROOT = _REPO_ROOT
OUT = f"{ROOT}/04_outputs/tables"
FROZEN = f"{ROOT}/07_paper2_eicu/frozen_params_treatment_free"
DEST = f"{ROOT}/08_paper3_multimodal"

order = pd.read_csv(f"{FROZEN}/feature_order.csv").sort_values("position")
FEATURES = order.feature.tolist()
print(f"{len(FEATURES)} continuous features, frozen order: {FEATURES[:3]} ... {FEATURES[-1]}")

model = torch.load(f"{FROZEN}/.model_k4_treatment_free.pt", weights_only=False)
wide = pd.read_csv(f"{OUT}/timewindow_level_modeling.csv").sort_values(["stay_id", "window_idx"])

def one_window(m, seq):
    """D1: a death in the first window leaves one window, which pomegranate's predict() cannot
    take. With a single observation the smoothed posterior equals the filtered one, so the label
    is the argmax of the forward pass (the earlier study's correction does the same)."""
    with torch.no_grad():
        return m.forward(seq.unsqueeze(0))[0].numpy().argmax(axis=1)


def decode(df):
    out = []
    for stay_id, g in df.groupby("stay_id", sort=False):
        seq = torch.tensor(g[FEATURES].values, dtype=torch.float32)
        lab = one_window(model, seq) if len(g) == 1 else model.predict(seq.unsqueeze(0))[0].numpy()
        out.append(pd.DataFrame({"stay_id": stay_id, "window_idx": g.window_idx.values,
                                 "tf_state": lab, "split": g.split.iloc[0]}))
    return pd.concat(out, ignore_index=True)

# ---------------------------------------------------------------- D1: windows after death
coh = pd.read_csv(f"{OUT}/patient_level_cohort.csv", parse_dates=["intime", "deathtime"])
_dh = (coh.deathtime - coh.intime).dt.total_seconds() / 3600
_ev = (_dh < 72).fillna(False).values      # protocol v1.4 D1.3: any recorded death within 72 h. (The earlier
                                            # study's rule also required icu_mortality == 1; 2 stays have a death
                                            # 26 h before ICU discharge but icu_mortality 0, and neither has a landmark.)
LAST = pd.Series((_dh // 6).values[_ev], index=coh.stay_id.values[_ev])     # last window to keep


def truncate(df):
    return df[~(df.window_idx > df.stay_id.map(LAST).fillna(99))]


full = decode(wide)                                       # for the reproduction check only
allassign = decode(truncate(wide))
print(f"D1: {len(wide) - len(truncate(wide))} windows after death removed from "
      f"{wide[wide.window_idx > wide.stay_id.map(LAST).fillna(99)].stay_id.nunique()} stays before decoding")

# --- verification: the re-decoded TRAIN labels must match the published ones exactly
pub = pd.read_csv(f"{OUT}/sensitivity_notreat_state_assignments.csv")
chk = full.merge(pub, on=["stay_id", "window_idx"])
agree = (chk.tf_state == chk.state_no_treatment).mean()
print(f"\nreproduction check on the published train split: {len(chk)} windows, "
      f"exact agreement {agree:.4f}")
assert agree == 1.0, "frozen model does not reproduce the published train labels -- stop"

_m = full.merge(allassign, on=["stay_id", "window_idx"], suffixes=("_full", "_trunc"))
_t = _m.stay_id.isin(set(LAST.index))
assert (_m[~_t].tf_state_full == _m[~_t].tf_state_trunc).all(), "truncation changed an untruncated stay — stop"
print(f"D1: windows relabelled by truncation within truncated stays: "
      f"{int((_m[_t].tf_state_full != _m[_t].tf_state_trunc).sum())} of {int(_t.sum())}")
allassign.to_csv(f"{DEST}/tf_state_assignments_all.csv", index=False)

# ---------------------------------------------------------------- D1: earlier study's primary model
sys.path.insert(0, f"{ROOT}/03_code")
import feature_spec  # noqa: E402
p1model = torch.load(f"{ROOT}/.model_k4.pt", weights_only=False)
_cz, _nc, _ = feature_spec.features(wide.columns, include_treatment=False)
P1F = _cz + ["mech_vent", "crrt", "vasopressor", "sedative"]


# the model returns raw fit indices; the published file holds canonical labels (05c_canonical_state_labels.py)
RAW2CANON = pd.read_csv(f"{OUT}/state_label_mapping.csv").set_index("raw_state").canonical_state.to_dict()


def decode_p1(df):
    out = []
    for stay_id, g in df.groupby("stay_id", sort=False):
        seq = torch.tensor(g[P1F].values, dtype=torch.float32)
        lab = one_window(p1model, seq) if len(g) == 1 else p1model.predict(seq.unsqueeze(0))[0].numpy()
        out.append(pd.DataFrame({"stay_id": stay_id, "window_idx": g.window_idx.values,
                                 "state_k4": [RAW2CANON[int(x)] for x in lab]}))
    return pd.concat(out, ignore_index=True)


p1pub = pd.read_csv(f"{OUT}/hmm_state_assignments_all.csv")
p1full = decode_p1(wide).merge(p1pub, on=["stay_id", "window_idx"], suffixes=("", "_pub"))
p1agree = (p1full.state_k4 == p1full.state_k4_pub).mean()
print(f"primary model, reproduction of hmm_state_assignments_all.csv on untruncated sequences: "
      f"{len(p1full)} windows, exact agreement {p1agree:.4f}")
assert p1agree == 1.0, "frozen primary model does not reproduce the published labels -- stop"
p1trunc = decode_p1(truncate(wide))
p1trunc.to_csv(f"{DEST}/p1_state_assignments_truncated.csv", index=False)      # canonical labels
print(f"Saved: {DEST}/p1_state_assignments_truncated.csv ({len(p1trunc)} windows)")
names = pd.read_csv(f"{FROZEN}/state_label_mapping.csv").set_index("tf_state").name.to_dict()
print(f"\nDecoded {allassign.stay_id.nunique()} stays, {len(allassign)} windows "
      f"(was {pub.stay_id.nunique()} stays before)")
print("\nwindow-level state distribution, train vs newly decoded test:")
d = pd.crosstab(allassign.tf_state.map(names), allassign.split, normalize="columns") * 100
print(d.round(1).to_string())
print(f"\nSaved: {DEST}/tf_state_assignments_all.csv")
