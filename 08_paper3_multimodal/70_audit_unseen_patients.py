"""
Paper 3 audit A: the state model was fitted on Paper 1's random training split, which includes 915 of the
1,324 temporal-validation patients. Evaluate the unchanged models separately in validation patients the
HMM never saw (Paper 1 test split) and those it did. Declared in PROJECT_LOG before running.
Positional ranking and patient-level bootstrap as in 49; seed 20260917; 2,000 replicates.
Writes audit_unseen_patients.csv.
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

P3 = _REPO_ROOT + "/08_paper3_multimodal"
SEED, REPS = 20260917, 2000
m0 = pd.read_csv(f"{P3}/m0_validation_predictions.csv")
m1 = pd.read_csv(f"{P3}/m1_validation_predictions.csv")
v = m0.merge(m1[["stay_id", "landmark_h", "M1-D"]], on=["stay_id", "landmark_h"], validate="one_to_one")
sp = pd.read_csv(f"{P3}/landmark_dataset.csv", usecols=["stay_id", "split_paper1"]).drop_duplicates("stay_id")
v = v.merge(sp, on="stay_id", validate="many_to_one")


def cap(y, lm, s):
    o = np.lexsort((-s, lm)); L, e = lm[o], y[o]
    st = np.r_[0, np.flatnonzero(np.diff(L)) + 1]; sz = np.diff(np.r_[st, len(L)])
    r = np.arange(len(L)) - np.repeat(st, sz)
    return 100 * e[r < np.repeat(np.maximum(1, np.round(sz * .1)).astype(int), sz)].sum() / e.sum()


rows = []
rng = np.random.default_rng(SEED)
for label, g in [("all validation", v), ("never seen by the HMM (Paper 1 test)", v[v.split_paper1 == "test"]),
                 ("seen by the HMM (Paper 1 train)", v[v.split_paper1 == "train"])]:
    y, lm, st = g.composite_event.to_numpy(), g.landmark_h.to_numpy(), g.stay_id.to_numpy()
    P = {m: g[m].to_numpy() for m in ["M0-state", "M0-full", "M0+A", "M1-D"]}
    obs = cap(y, lm, P["M1-D"]) - cap(y, lm, P["M0+A"])
    pats, inv = np.unique(st, return_inverse=True); mem = [np.flatnonzero(inv == i) for i in range(len(pats))]
    dc, da = [], []
    for _ in range(REPS):
        pos = np.concatenate([mem[i] for i in rng.integers(0, len(pats), len(pats))])
        yy, ll = y[pos], lm[pos]
        dc.append(cap(yy, ll, P["M1-D"][pos]) - cap(yy, ll, P["M0+A"][pos]))
        da.append(roc_auc_score(yy, P["M0-state"][pos]))
    row = {"subset": label, "patients": len(pats), "landmarks": len(y), "events": int(y.sum()),
           "auroc_M0state": roc_auc_score(y, P["M0-state"]), "auroc_M0state_lo": np.percentile(da, 2.5),
           "auroc_M0state_hi": np.percentile(da, 97.5), "auroc_M0full": roc_auc_score(y, P["M0-full"]),
           "auroc_M0A": roc_auc_score(y, P["M0+A"]), "auroc_M1D": roc_auc_score(y, P["M1-D"]),
           "capture_M0A": cap(y, lm, P["M0+A"]), "capture_M1D": cap(y, lm, P["M1-D"]),
           "delta": obs, "lo": np.percentile(dc, 2.5), "hi": np.percentile(dc, 97.5)}
    rows.append(row)
out = pd.DataFrame(rows)
assert abs(out.delta[0] - 0.000) < 0.001          # protocol v1.4 D1 (was 0.149)
out.to_csv(f"{P3}/audit_unseen_patients.csv", index=False)
pd.set_option("display.width", 200)
print(out.round(3).to_string(index=False))
