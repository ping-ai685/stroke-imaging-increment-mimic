"""
Paper 3: filtered (forward-only) state decoding for the PREDICTOR side.

A landmark prediction may only use what was knowable at the landmark. The state
labels published in Papers 1-2 come from `model.predict()`, which takes at each window
the state with the highest smoothed posterior probability (forward-backward over the
whole sequence; not a Viterbi path; corrected 4 Oct 2026) -- so the state at window L
uses windows after L. Measured
on 400 complete stays, 15.2% of stays have at least one landmark whose state
changes once future windows are hidden. Small, but it is future information, and
the current state is exactly what the M0 baseline rests on.

This script produces the predictor-side state:

    filtered posterior  P(state_L | observations 0..L)  = normalise(alpha_L)

from a single forward pass per stay. The argmax is the filtered state; the full
posterior vector is kept as well, since a four-dimensional belief carries more
than a hard label and is the more natural thing to feed a risk model.

The OUTCOME side deliberately keeps the full-sequence labels
(`tf_state_assignments_all.csv`): outcomes are adjudicated retrospectively, the
way any outcome is. That asymmetry is intentional and must be stated in Methods.

Writes: 08_paper3_multimodal/tf_filtered_states.csv
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import numpy as np
import pandas as pd
import torch

ROOT = _REPO_ROOT
FROZEN = f"{ROOT}/07_paper2_eicu/frozen_params_treatment_free"
DEST = f"{ROOT}/08_paper3_multimodal"

FEATURES = pd.read_csv(f"{FROZEN}/feature_order.csv").sort_values("position").feature.tolist()
model = torch.load(f"{FROZEN}/.model_k4_treatment_free.pt", weights_only=False)
wide = pd.read_csv(f"{ROOT}/04_outputs/tables/timewindow_level_modeling.csv") \
         .sort_values(["stay_id", "window_idx"])

rows = []
for stay_id, g in wide.groupby("stay_id", sort=False):
    X = torch.tensor(g[FEATURES].values, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        alpha = model.forward(X)[0].numpy()          # log alpha, (T, K)
    post = np.exp(alpha - alpha.max(axis=1, keepdims=True))
    post /= post.sum(axis=1, keepdims=True)
    rows.append(pd.DataFrame({
        "stay_id": stay_id,
        "window_idx": g.window_idx.values,
        "filtered_state": post.argmax(axis=1),
        **{f"p_state{k}": post[:, k] for k in range(post.shape[1])},
    }))
filt = pd.concat(rows, ignore_index=True)
filt.to_csv(f"{DEST}/tf_filtered_states.csv", index=False)
print(f"filtered states for {filt.stay_id.nunique()} stays, {len(filt)} windows")

# --- how much does hiding the future change the state, and where?
full = pd.read_csv(f"{DEST}/tf_state_assignments_all.csv")
m = filt.merge(full, on=["stay_id", "window_idx"])
m["same"] = m.filtered_state == m.tf_state
print(f"\noverall agreement with the full-sequence (outcome-side) state: "
      f"{m.same.mean()*100:.1f}%")
byw = m.groupby("window_idx").same.agg(["mean", "size"])
byw["disagree_%"] = (1 - byw["mean"]) * 100
print("\ndisagreement by window (this is the leakage, and it should shrink with time):")
print(byw[["size", "disagree_%"]].round(1).to_string())

names = pd.read_csv(f"{FROZEN}/state_label_mapping.csv").set_index("tf_state").name.to_dict()
print("\nstate distribution, filtered (predictor) vs full-sequence (outcome):")
cmp = pd.DataFrame({
    "filtered_%": filt.filtered_state.value_counts(normalize=True).mul(100),
    "full_seq_%": full.tf_state.value_counts(normalize=True).mul(100),
}).rename(index=names)
print(cmp.round(1).to_string())
print(f"\nmean posterior confidence of the filtered state: "
      f"{m[[f'p_state{k}' for k in range(4)]].max(axis=1).mean():.3f}")
print(f"\nSaved: {DEST}/tf_filtered_states.csv")
