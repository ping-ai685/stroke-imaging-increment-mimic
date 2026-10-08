"""
Paper 3: every number the manuscript uses, computed from source files, in one manifest.

The manuscript takes its numbers from manuscript/numbers.json and nowhere else; a later check
script reverses the direction (text -> manifest). Where a value is recomputed here that an
earlier script also produced, the two are asserted equal, so a stale CSV cannot slip through.

Aggregate statistics only. No report text, no row-level data.
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import json
import re
import subprocess

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from sklearn.preprocessing import StandardScaler

P3 = _REPO_ROOT + "/08_paper3_multimodal"
SEED, REPS = 20260917, 2000
N = {}


def put(key, value):
    if isinstance(value, (np.floating, float)):
        value = float(value)
    elif isinstance(value, (np.integer,)):
        value = int(value)
    N[key] = value


# ------------------------------------------------------------------------------ cohort
d = pd.read_csv(f"{P3}/landmark_dataset.csv")
d = d[d.note_era].copy()
f = pd.read_csv(f"{P3}/landmark_imaging_features.csv",
                usecols=["stay_id", "landmark_idx", "img_available_locked", "img_report_age_h"])
d = d.merge(f, on=["stay_id", "landmark_idx"], how="left", validate="one_to_one")
val = d.anchor_year_group == "2017 - 2019"
for lab, g in (("all", d), ("dev", d[~val]), ("val", d[val])):
    put(f"cohort.{lab}.patients", g.stay_id.nunique())
    put(f"cohort.{lab}.landmarks", len(g))
    put(f"cohort.{lab}.events", g.composite_event.sum())
    put(f"cohort.{lab}.event_rate_pct", 100 * g.composite_event.mean())
    put(f"cohort.{lab}.event_patients", g[g.composite_event == 1].stay_id.nunique())
    put(f"cohort.{lab}.adverse", g.future_24h_adverse.sum())
    put(f"cohort.{lab}.deaths", g.future_24h_death.sum())
    put(f"cohort.{lab}.icu_discharge", g.icu_discharge_before_24h.sum())
    put(f"cohort.{lab}.imaging_pct", 100 * g.img_available_locked.mean())

# Table 1: one row per patient, first eligible landmark
first = d.sort_values("landmark_h").groupby("stay_id").head(1)
fv = first.anchor_year_group == "2017 - 2019"
for lab, g in (("all", first), ("dev", first[~fv]), ("val", first[fv])):
    put(f"t1.{lab}.n", len(g))
    q = g.age.quantile([.25, .5, .75]).to_list()
    put(f"t1.{lab}.age_median", q[1]); put(f"t1.{lab}.age_q1", q[0]); put(f"t1.{lab}.age_q3", q[2])
    put(f"t1.{lab}.male_n", (g.gender == "M").sum()); put(f"t1.{lab}.male_pct", 100 * (g.gender == "M").mean())
    for s in ["AIS", "ICH", "SAH", "ICH+SAH"]:
        put(f"t1.{lab}.sub_{s}_n", (g.stroke_subtype == s).sum())
        put(f"t1.{lab}.sub_{s}_pct", 100 * (g.stroke_subtype == s).mean())
    c = g.charlson.quantile([.25, .5, .75]).to_list()
    put(f"t1.{lab}.charlson_median", c[1]); put(f"t1.{lab}.charlson_q1", c[0]); put(f"t1.{lab}.charlson_q3", c[2])
    for v in ["hypertension", "diabetes", "atrial_fibrillation", "heart_failure", "ckd"]:
        put(f"t1.{lab}.{v}_n", g[v].sum()); put(f"t1.{lab}.{v}_pct", 100 * g[v].mean())
    put(f"t1.{lab}.first_landmark_imaging_pct", 100 * g.img_available_locked.mean())
    put(f"t1.{lab}.first_landmark_imaging_n", int(g.img_available_locked.sum()))

for h, g in d.groupby("landmark_h"):
    gv = g[g.anchor_year_group == "2017 - 2019"]
    put(f"landmark.{int(h)}.at_risk", len(g)); put(f"landmark.{int(h)}.events", g.composite_event.sum())
    put(f"landmark.{int(h)}.event_rate_pct", 100 * g.composite_event.mean())
    put(f"landmark.{int(h)}.imaging_pct", 100 * g.img_available_locked.mean())
    put(f"landmark.{int(h)}.val_at_risk", len(gv)); put(f"landmark.{int(h)}.val_events", gv.composite_event.sum())
a = d[d.img_available_locked == 1].img_report_age_h
put("imaging.report_age_median_h", a.median()); put("imaging.report_age_p95_h", a.quantile(.95))
put("imaging.report_age_max_h", a.max())

# cohort flow (63, from patients.csv.gz on the MIMIC drive; stored so this script runs without it)
for r in pd.read_csv(f"{P3}/cohort_flow_paper3.csv").itertuples():
    put(f"flow.{r.stage}", r.n)
assert N["flow.analysis_patients"] == N["cohort.all.patients"]

# ------------------------------------------------------------------------------ reports
idx = pd.read_csv(f"{P3}/analysis_population_index.csv")
put("reports.analysis_population", len(idx)); put("reports.stays", idx.stay_id.nunique())
recs = [json.loads(l) for l in open(f"{P3}/extractor/analysis_population_out.jsonl", encoding="utf-8") if l.strip()]
assert all(r["prompt_version"] == "0347237dd3f5" for r in recs)
ok = {r["note_id"] for r in recs if not r["error"]}
quar = set(pd.read_csv(f"{P3}/extractor/analysis_population_failed.csv").note_id)
put("reports.extracted", len(ok)); put("reports.quarantined", len(quar))
assert len(ok) + len(quar) == len(idx)
e = idx[idx.note_id.isin(ok)]
put("reports.floor_excluded", (e.hours_from_icu_admission < -72).sum())
put("reports.eligible_after_floor", (e.hours_from_icu_admission >= -72).sum())
put("reports.pre_icu_pct", 100 * (idx.hours_from_icu_admission < 0).mean())
put("reports.pre_icu_72h_pct", 100 * (idx.hours_from_icu_admission < -72).mean())
put("reports.earliest_days", -idx.hours_from_icu_admission.min() / 24)
put("extraction.output_tokens_median", float(np.median([r["eval_count"] for r in recs if not r["error"]])))

# ------------------------------------------------------------------------------ reliability
out = subprocess.run(["python3", "evaluate_validation.py", "--output", "validation200_v12_out.jsonl",
                      "--labels", "../annotation_validation/validation_labels_v1.2.csv"],
                     cwd=f"{P3}/extractor", capture_output=True, text=True, check=True).stdout
for m in re.finditer(r"^(\w+)\s+(-?\d\.\d\d)\s+(\d+\.\d)%\s+(\d+)", out, re.M):
    put(f"kappa.{m.group(1)}", float(m.group(2)))
    put(f"kappa.{m.group(1)}.agree_pct", float(m.group(3)))
    put(f"kappa.{m.group(1)}.pos", int(m.group(4)))
lk = pd.read_csv(f"{P3}/extractor/list_field_kappa.csv")
for r in lk.itertuples():
    put(f"kappa.list.{r.category}", None if pd.isna(r.kappa) else r.kappa)
    put(f"kappa.list.{r.category}.pos", r.annotator_pos)
for k, v in {"kappa.midline_shift_present": 0.80, "kappa.intraventricular_haemorrhage": 0.68,
             "kappa.intracranial_haemorrhage": 0.64, "kappa.list.MCA": 0.78,
             "kappa.list.cerebellum": 0.66, "kappa.list.intraparenchymal": 0.75,
             "kappa.list.subarachnoid": 0.73}.items():
    assert round(N[k], 2) == v, (k, N[k], v)

# ------------------------------------------------------------------------------ models
m0 = pd.read_csv(f"{P3}/m0_validation_predictions.csv")
m1 = pd.read_csv(f"{P3}/m1_validation_predictions.csv")
v = m0.merge(m1[["stay_id", "landmark_h", "M0+A", "M1-D"]], on=["stay_id", "landmark_h"],
             suffixes=("_m0file", ""), validate="one_to_one")
assert np.allclose(v["M0+A_m0file"], v["M0+A"], atol=1e-9), "M0+A differs between prediction files"
y, lmv, stay = v.composite_event.to_numpy(), v.landmark_h.to_numpy(), v.stay_id.to_numpy()


def capture(pos, s, k=0.10, yy=None, lm=None, w=None):
    yy = y if yy is None else yy
    lm = lmv if lm is None else lm
    L, sc, ev = lm[pos], s[pos], yy[pos]
    ww = np.ones(len(pos)) if w is None else w[pos]
    o = np.lexsort((-sc, L)); L, ev, ww = L[o], ev[o], ww[o]
    st = np.r_[0, np.flatnonzero(np.diff(L)) + 1]; sz = np.diff(np.r_[st, len(L)])
    rank = np.arange(len(L)) - np.repeat(st, sz)
    ch = rank < np.repeat(np.maximum(1, np.round(sz * k)).astype(int), sz)
    num = (ev[ch] * ww[ch]).sum()
    return 100 * num / (ev * ww).sum(), 100 * num / ww[ch].sum(), (num / ww[ch].sum()) / ((ev * ww).sum() / ww.sum())


def calib(yy, p):
    z = logit(np.clip(p, 1e-6, 1 - 1e-6))
    return (brentq(lambda a_: (yy - expit(a_ + z)).sum(), -10, 10),
            LogisticRegression(max_iter=2000, C=1e6).fit(z.reshape(-1, 1), yy).coef_[0, 0])


allpos = np.arange(len(y))
for m in ["M0-state", "M0-full", "M0+A", "M1-D"]:
    p = v[m].to_numpy()
    put(f"model.{m}.auroc", roc_auc_score(y, p)); put(f"model.{m}.auprc", average_precision_score(y, p))
    put(f"model.{m}.brier", brier_score_loss(y, p))
    i, s = calib(y, p); put(f"model.{m}.cal_intercept", i); put(f"model.{m}.cal_slope", s)
    for k in (0.05, 0.10, 0.20):
        c, ppv, lift = capture(allpos, p, k)
        put(f"model.{m}.top{int(k*100)}.capture", c); put(f"model.{m}.top{int(k*100)}.ppv", ppv)
        put(f"model.{m}.top{int(k*100)}.lift", lift)
    put(f"model.{m}.top10.events_captured", round(capture(allpos, p, 0.10)[0] * y.sum() / 100))
    assert abs(capture(allpos, p, 0.10)[0] * y.sum() / 100 - N[f"model.{m}.top10.events_captured"]) < 1e-6
    at24 = np.flatnonzero(lmv == 24)
    c, ppv, lift = capture(at24, p)
    put(f"model.{m}.lm24.capture", c); put(f"model.{m}.lm24.ppv", ppv); put(f"model.{m}.lm24.lift", lift)
put("lm24.val_at_risk", int((lmv == 24).sum())); put("lm24.val_events", int(y[lmv == 24].sum()))
put("lm24.flagged", int(max(1, round((lmv == 24).sum() * 0.10))))

pats, inv = np.unique(stay, return_inverse=True)
mem = [np.flatnonzero(inv == i) for i in range(len(pats))]
rng = np.random.default_rng(SEED)
for lo_m, hi_m, key in (("M0+A", "M1-D", "confirmatory"), ("M0-state", "M0-full", "ladder.full_vs_state"),
                        ("M0-full", "M0+A", "ladder.A_vs_full")):
    p0, p1 = v[lo_m].to_numpy(), v[hi_m].to_numpy()
    put(f"{key}.delta_capture", capture(allpos, p1)[0] - capture(allpos, p0)[0])
    put(f"{key}.delta_auroc", roc_auc_score(y, p1) - roc_auc_score(y, p0))
    dc, da = [], []
    for _ in range(REPS):
        pos = np.concatenate([mem[i] for i in rng.integers(0, len(pats), len(pats))])
        dc.append(capture(pos, p1)[0] - capture(pos, p0)[0])
        da.append(roc_auc_score(y[pos], p1[pos]) - roc_auc_score(y[pos], p0[pos]))
    put(f"{key}.delta_capture_lo", np.percentile(dc, 2.5)); put(f"{key}.delta_capture_hi", np.percentile(dc, 97.5))
    put(f"{key}.delta_auroc_lo", np.percentile(da, 2.5)); put(f"{key}.delta_auroc_hi", np.percentile(da, 97.5))
assert abs(N["confirmatory.delta_capture"] - 0.000) < 0.001          # protocol v1.4 D1 (was 0.149)

# time design, read from the code and data that define it
_m46 = open(f"{P3}/46_merge_imaging_features.py").read()
put("design.report_floor_h", -float(re.search(r"^FLOOR_H = (-?[\d.]+)", _m46, re.M).group(1)))
_lmh = sorted(d.landmark_h.unique())
put("design.window_h", int(_lmh[1] - _lmh[0])); put("design.first_landmark_h", int(_lmh[0]))
put("design.last_landmark_h", int(_lmh[-1])); put("design.n_landmarks", len(_lmh))
put("design.horizon_h", int(re.search(r"future_(\d+)h_adverse", ",".join(d.columns)).group(1)))

# extraction validation design, counted from the files rather than typed
put("extraction.dev_reports", sum(1 for l in open(f"{P3}/extractor/dev50_v12_out.jsonl") if l.strip()))
put("extraction.val_reports", sum(1 for l in open(f"{P3}/extractor/validation200_v12_out.jsonl") if l.strip()))
_ev = open(f"{P3}/extractor/evaluate_validation.py").read()
put("extraction.kappa_threshold", float(re.search(r"k >= ([\d.]+)", _ev).group(1)))
put("extraction.min_positives", int(re.search(r"pos >= (\d+)", _ev).group(1)))
_ph = ["midline_shift_present", "intraventricular_haemorrhage", "intracranial_haemorrhage", "acute_infarction",
       "cerebral_oedema", "mass_effect", "chronic_ischaemic_change"]
put("extraction.phenotypes_candidate", len(_ph))
put("extraction.phenotypes_passing", sum(N[f"kappa.{k}"] >= N["extraction.kappa_threshold"]
                                         and N[f"kappa.{k}.pos"] >= N["extraction.min_positives"] for k in _ph))
put("extraction.locations_passing", sum(1 for k in list(N) if k.startswith("kappa.list.") and not k.endswith(".pos")
                                        and N[k] is not None and N[k] >= N["extraction.kappa_threshold"]
                                        and N[k + ".pos"] >= N["extraction.min_positives"]))

# M1-I
vi = pd.read_csv(f"{P3}/m1i_validation_predictions.csv")
yi, li, si, wi = vi.composite_event.to_numpy(), vi.landmark_h.to_numpy(), vi.stay_id.to_numpy(), vi.sw_primary.to_numpy()
A, B = vi["M0-full (imaged, weighted)"].to_numpy(), vi["M1-I (imaged, weighted)"].to_numpy()
ap = np.arange(len(yi))
put("m1i.landmarks", len(yi)); put("m1i.events", int(yi.sum())); put("m1i.event_rate_pct", 100 * yi.mean())
put("m1i.auroc_M0full", roc_auc_score(yi, A, sample_weight=wi)); put("m1i.auroc_M1I", roc_auc_score(yi, B, sample_weight=wi))
put("m1i.capture_M0full", capture(ap, A, yy=yi, lm=li, w=wi)[0]); put("m1i.capture_M1I", capture(ap, B, yy=yi, lm=li, w=wi)[0])
put("m1i.delta_capture", N["m1i.capture_M1I"] - N["m1i.capture_M0full"])
put("m1i.delta_auroc", N["m1i.auroc_M1I"] - N["m1i.auroc_M0full"])
pi_, ii = np.unique(si, return_inverse=True); mi = [np.flatnonzero(ii == i) for i in range(len(pi_))]
ds = []
for _ in range(REPS):
    pos = np.concatenate([mi[i] for i in rng.integers(0, len(pi_), len(pi_))])
    ds.append(capture(pos, B, yy=yi, lm=li, w=wi)[0] - capture(pos, A, yy=yi, lm=li, w=wi)[0])
put("m1i.delta_capture_lo", np.percentile(ds, 2.5)); put("m1i.delta_capture_hi", np.percentile(ds, 97.5))
assert abs(N["m1i.delta_capture"] - (-0.69)) < 0.01              # protocol v1.4 D1 (was -1.89)

# IPW diagnostics, refitted exactly as in 47 (same predictors, same pipeline), then checked against
# the propensity scores 47 saved for the validation set
import importlib.util
spec = importlib.util.spec_from_file_location("m1", f"{P3}/47_m1_models.py")
M1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(M1)
full = pd.read_csv(f"{P3}/landmark_dataset.csv"); full = full[full.note_era].copy()
full = full.merge(pd.read_csv(f"{P3}/landmark_imaging_features.csv", usecols=["stay_id", "landmark_idx", "img_available_locked"] + M1.IMG),
                  on=["stay_id", "landmark_idx"], validate="one_to_one")
dv = M1.derive(full[full.anchor_year_group != "2017 - 2019"].copy())
vv = M1.derive(full[full.anchor_year_group == "2017 - 2019"].copy())
AV = M1.FIXED + M1.STATE + M1.PHYS
from sklearn.pipeline import make_pipeline
av = make_pipeline(StandardScaler(), LogisticRegression(max_iter=4000, C=1.0)).fit(dv[AV], dv.img_available_locked)
ps_d, ps_v = av.predict_proba(dv[AV])[:, 1], av.predict_proba(vv[AV])[:, 1]
saved = pd.read_csv(f"{P3}/m1_validation_predictions.csv")
assert np.allclose(np.sort(ps_v), np.sort(saved.ps.to_numpy()), atol=1e-8), "propensity refit differs from 47"
put("ipw.ps_auroc_val", roc_auc_score(vv.img_available_locked, ps_v))
# common support, as reported: share of imaged validation landmarks whose propensity lies within the
# range of non-imaged landmarks at the same landmark time
_v = saved
_share = [(((g[g.img_available_locked == 1].ps >= g[g.img_available_locked == 0].ps.min())
            & (g[g.img_available_locked == 1].ps <= g[g.img_available_locked == 0].ps.max())).mean())
          for _, g in _v.groupby("landmark_h")]
put("ipw.support_share_min_pct", 100 * min(_share)); put("ipw.support_share_max_pct", 100 * max(_share))
imaged = dv.img_available_locked.to_numpy() == 1
sw = dv.img_available_locked.mean() / np.clip(ps_d, 1e-4, 1)
swi = sw[imaged]
lo_, hi_ = np.percentile(swi, [1, 99]); t = np.clip(swi, lo_, hi_)
put("ipw.weight_min", t.min()); put("ipw.weight_max", t.max()); put("ipw.weight_mean", t.mean())
put("ipw.ess", t.sum() ** 2 / (t ** 2).sum()); put("ipw.n_imaged_dev", int(imaged.sum()))
put("ipw.ess_rounded", int(round(N["ipw.ess"])))           # effective sample size is reported as a whole number
put("ipw.ess_pct", 100 * N["ipw.ess"] / imaged.sum())
put("ipw.ps_imaged_min", ps_d[imaged].min()); put("ipw.ps_imaged_max", ps_d[imaged].max())
put("ipw.ps_notimaged_min", ps_d[~imaged].min()); put("ipw.ps_notimaged_max", ps_d[~imaged].max())

# ------------------------------------------------------------------------------ secondary files
for r in pd.read_csv(f"{P3}/sensitivity_results.csv").itertuples():
    k = f"sens.{r.analysis}.{re.sub(r'[^a-z0-9]+', '_', r.condition.lower()).strip('_')}"
    put(k + ".delta", r.delta_pp); put(k + ".lo", r.lo); put(k + ".hi", r.hi); put(k + ".events", r.events)
for r in pd.read_csv(f"{P3}/sensitivity_results_11_12.csv").itertuples():
    k = f"sens.{r.analysis}"
    put(k + ".delta", r.delta_pp); put(k + ".lo", r.lo); put(k + ".hi", r.hi)
for i, r in enumerate(pd.read_csv(f"{P3}/redundancy_posthoc.csv").itertuples(), 1):
    for c in ["auroc_base", "auroc_img", "d_auroc", "d_auroc_lo", "d_auroc_hi", "capture_base",
              "capture_img", "d_capture", "d_capture_lo", "d_capture_hi"]:
        put(f"redund.B{i}.{c}", getattr(r, c))
for r in pd.read_csv(f"{P3}/redundancy_posthoc_crude.csv").itertuples():
    k = "crude." + re.sub(r"[^a-z0-9]+", "_", r.feature.lower()).strip("_")
    put(k + ".rate_pos", 100 * r.rate_pos); put(k + ".rate_neg", 100 * r.rate_neg); put(k + ".ratio", r.ratio)
for r in pd.read_csv(f"{P3}/dca_delta_net_benefit.csv").itertuples():
    k = f"dca.pt{int(round(r.threshold*100))}"
    for c in ["nb_M0A", "nb_M1D", "delta", "lo", "hi"]:
        put(f"{k}.{c}", 100 * getattr(r, c))
for r in pd.read_csv(f"{P3}/subtype_performance.csv").itertuples():
    for c in ["events", "auroc_M0A", "auroc_M1D", "capture_M0A", "capture_M1D", "delta", "lo", "hi"]:
        put(f"subtype.{r.subtype}.{c}", getattr(r, c))
inter = open(f"{P3}/subtype_interaction.txt").read()
m = re.search(r"delta ([+-][\d.]+) \[([+-][\d.]+), ([+-][\d.]+)\]", inter)
put("subtype.interaction.delta", float(m.group(1))); put("subtype.interaction.lo", float(m.group(2)))
put("subtype.interaction.hi", float(m.group(3)))
for r in pd.read_csv(f"{P3}/subtype_phenotype_prevalence.csv").itertuples():
    put("prev." + r.subtype + "." + re.sub(r"[^a-z0-9]+", "_", r.feature.lower()).strip("_"), 100 * r.prevalence)

# ------------------------------------------------------------------------------ audit of inherited preprocessing
_u = pd.read_csv(f"{P3}/audit_unseen_patients.csv")
assert _u.patients[0] == N["cohort.val.patients"] and abs(_u.delta[0] - N["confirmatory.delta_capture"]) < 1e-12
for i, tag in ((1, "unseen"), (2, "seen")):
    for c in ["patients", "events", "auroc_M0state", "delta", "lo", "hi"]:
        put(f"audit.{tag}.{c}", _u[c][i])
put("audit.seen_pct", 100 * _u.patients[2] / _u.patients[0])
_l = pd.read_csv(f"{P3}/audit_lab_result_time.csv").iloc[0]
assert _l.lab == "all eight labs"
put("audit.lab.values_used", int(_l.values_used)); put("audit.lab.late_pct", _l.resulted_after_landmark_pct)
put("audit.lab.delay_median_h", _l.median_delay_after_landmark_h_if_late)
put("audit.lab.delay_p90_h", _l.p90_delay_after_landmark_h_if_late)
for r in pd.read_csv(f"{P3}/audit_lab_result_time.csv").itertuples():          # per-test rows of Table S13
    k = "audit.lab." + ("all" if r.lab == "all eight labs" else r.lab)
    put(k + ".n", int(r.values_used)); put(k + ".late_pct", r.resulted_after_landmark_pct)
    put(k + ".delay_median", r.median_delay_after_landmark_h_if_late); put(k + ".delay_p90", r.p90_delay_after_landmark_h_if_late)
_s = pd.read_csv(f"{P3}/audit_lab_result_time_sensitivity.csv")
assert abs(_s.delta_pp[0] - N["confirmatory.delta_capture"]) < 1e-12 and abs(_s.hi[0] - N["confirmatory.delta_capture_hi"]) < 1e-9
for c in ["auroc_M0A", "auroc_M1D", "capture_M0A", "capture_M1D"]:
    put(f"audit.labsens.{c}", _s[c][1])
put("audit.labsens.delta", _s.delta_pp[1]); put("audit.labsens.lo", _s.lo[1]); put("audit.labsens.hi", _s.hi[1])

# ------------------------------------------------------------------------------ C1: repeated extraction (protocol v1.3)
_c = json.load(open(f"{P3}/c1_second_extractor/c1_results.json"))
_sc = _c["selfcheck"]                                     # c1_analysis.py rebuilt the primary result first
assert abs(_sc["delta"] - N["confirmatory.delta_capture"]) < 1e-9
assert abs(_sc["lo"] - N["confirmatory.delta_capture_lo"]) < 1e-9 and abs(_sc["hi"] - N["confirmatory.delta_capture_hi"]) < 1e-9
assert abs(_sc["auroc_aug"] - N["model.M1-D.auroc"]) < 1e-9 and abs(_sc["auroc_base"] - N["model.M0+A.auroc"]) < 1e-9
for tag in ("selfcheck", "a", "b"):
    for k in ("delta", "lo", "hi", "auroc_base", "auroc_aug", "events_base", "events_aug", "events_total", "n_features"):
        put(f"c1.{tag}.{k}", _c[tag][k])
    assert _c[tag]["consistent"] or tag == "selfcheck"
for k, v in _c["validation"].items():
    put(f"c1.kappa.{k}", v)
for k, v in _c["agreement"].items():
    put(f"c1.agree.{k}", v)
put("c1.agree.n_reports", _c["n_both"])
put("c1.agree.min", min(_c["agreement"][k] for k in ("intracranial_haemorrhage", "intraventricular_haemorrhage",
    "midline_shift_present", "cerebral_oedema", "acute_infarction", "mass_effect", "chronic_ischaemic_change")))
put("c1.agree.max", max(_c["agreement"][k] for k in ("intracranial_haemorrhage", "intraventricular_haemorrhage",
    "midline_shift_present", "cerebral_oedema", "acute_infarction", "mass_effect", "chronic_ischaemic_change")))
for k, v in _c["full_run"].items():
    if not isinstance(v, bool):
        put(f"c1.run.{k}", v)
put("c1.run.quarantined_pct", 100 * _c["full_run"]["quarantined"] / _c["full_run"]["reports"])
assert _c["full_run"]["all_errors_json"] and _c["full_run"]["quarantined_in_frozen_quarantine"] == _c["full_run"]["frozen_quarantined"]
put("c1.model.params_b", _c["model"]["params_b"])

# ------------------------------------------------------------------------------ independent reproduction (49)
_o49 = subprocess.run(["python3", f"{P3}/49_independent_reproduction.py"], capture_output=True, text=True, cwd=P3).stdout
put("repro.delta", float(re.search(r"point estimate ([+-][\d.]+) pp", _o49).group(1)))
_rci = re.search(r"95% CI \[([+-][\d.]+), ([+-][\d.]+)\]", _o49).groups()
put("repro.lo", float(_rci[0])); put("repro.hi", float(_rci[1]))
assert abs(N["repro.delta"] - N["confirmatory.delta_capture"]) < 0.001

# ------------------------------------------------------------------------------ protocol v1.4 D1 / v1.5 D2
_d = json.load(open(f"{P3}/d1_before_after.json"))           # frozen record of the pre-correction values
for k, v in _d["before"].items():
    put("d1.before." + k, v)
for k, v in _d["sens3_before"].items():
    put("d1.sens3_before." + k, v)
for k, v in _d["excluded"].items():
    put("d1.excluded." + k, v)
assert N["d1.before.cohort.val.landmarks"] - N["cohort.val.landmarks"] == N["d1.excluded.landmarks_val"]
assert N["d1.before.cohort.dev.landmarks"] - N["cohort.dev.landmarks"] == N["d1.excluded.landmarks_dev"]
_cal = pd.read_csv(f"{P3}/calibration_validation.csv").set_index("model")
for m_ in ("M0+A", "M1-D"):
    put(f"calib.{m_}.mean_pred_pct", 100 * _cal.loc[m_, "mean_pred"])
put("calib.observed_pct", 100 * _cal.loc["M0+A", "observed"])

json.dump(N, open(f"{P3}/manuscript/numbers.json", "w"), indent=1, ensure_ascii=False)
print(f"{len(N)} numbers -> manuscript/numbers.json; all consistency assertions passed")
