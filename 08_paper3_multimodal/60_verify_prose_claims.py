"""
Paper 3: check the claims that are not table cells.

58 traces numbers and 59 checks table cells, but the sentences a reviewer tests first are claims —
"no sensitivity analysis showed statistically supported incremental capture", "common support held at
every landmark", "no patient contributed to both cohorts", "the same model supplied the real-time state
and the outcome". Each is restated here as something a computer can fail, against the data or the code
that produced the result. The last section checks the wording boundaries the study lead set: what the
abstract may conclude, how the post hoc analysis is labelled, and phrases that were removed because they
overstated the evidence.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
MS = HERE / "manuscript"
N = json.load(open(MS / "numbers.json"))
EN = (MS / "paper3_draft_v5.md").read_text(encoding="utf-8")
CN = (MS / "paper3_draft_v5_CN.md").read_text(encoding="utf-8")
R = []


def claim(text, ok, detail=""):
    R.append(bool(ok))
    print(f"  {'OK ' if ok else 'BAD'}  {text}" + (f"\n         {detail}" if detail else ""))


def includes0(lo, hi):
    return lo <= 0 <= hi


print("Cohort and validation design\n")
d = pd.read_csv(HERE / "landmark_dataset.csv", usecols=["stay_id", "subject_id", "note_era", "anchor_year_group",
                                                         "filtered_state", "composite_event", "future_24h_adverse",
                                                         "future_24h_death", "icu_discharge_before_24h", "landmark_h"])
d = d[d.note_era]
dev_s = set(d[d.anchor_year_group != "2017 - 2019"].subject_id)
val_s = set(d[d.anchor_year_group == "2017 - 2019"].subject_id)
claim("no patient contributed to both development and validation", not (dev_s & val_s),
      f"{len(dev_s)} development and {len(val_s)} validation patients, overlap {len(dev_s & val_s)}")
claim("no eligible landmark is already in the adverse state (eligibility by the filtered state)",
      (d.filtered_state != 0).all(), f"filtered state 0 at {int((d.filtered_state == 0).sum())} landmarks")
claim("the composite outcome is deterioration or death, and ICU discharge alone is not an event",
      ((d.future_24h_adverse | d.future_24h_death) == d.composite_event).all()
      and not ((d.icu_discharge_before_24h == 1) & (d.future_24h_adverse == 0) & (d.future_24h_death == 0) & (d.composite_event == 1)).any())
v = pd.read_csv(HERE / "m1_validation_predictions.csv")
ev = v.groupby("landmark_h").composite_event.sum()
claim("no single landmark had more than 104 validation events (text says so)", ev.max() <= 104 and "more than 104 validation events" in EN,
      f"max {int(ev.max())} at {int(ev.idxmax())} h")

r200 = pd.read_csv(HERE / "annotation_validation" / "random200_index.csv")
dev50 = pd.read_csv(HERE / "annotation_session" / "session_packet_index.csv")
claim("validation: 200 reports, one per patient", len(r200) == 200 and r200.subject_id.is_unique)
claim("validation excludes the development reports and their patients",
      not (set(r200.note_id) & set(dev50.note_id)) and not (set(r200.subject_id) & set(dev50.subject_id)))
claim("validation is stratified by stroke subtype (all three subtypes present)",
      {"AIS", "ICH", "SAH"} <= set(r200.stroke_subtype), dict(r200.stroke_subtype.value_counts()))
claim("the extractor was developed on 50 reports", len(dev50) == 50 and
      sum(1 for l in open(HERE / "extractor" / "dev50_v12_out.jsonl") if l.strip()) == 50)
claim("two reports could not be processed", len(pd.read_csv(HERE / "extractor" / "analysis_population_failed.csv")) == 2)

print("\nReliability criterion\n")
PH = ["midline_shift_present", "intraventricular_haemorrhage", "intracranial_haemorrhage", "acute_infarction",
      "cerebral_oedema", "mass_effect", "chronic_ischaemic_change"]
passed = [k for k in PH if N[f"kappa.{k}"] >= 0.60 and N[f"kappa.{k}.pos"] >= 10]
claim("three of seven candidate phenotypes met the criterion: midline shift, IVH, intracranial haemorrhage",
      sorted(passed) == sorted(["midline_shift_present", "intraventricular_haemorrhage", "intracranial_haemorrhage"]), passed)
claim("the four that did not are acute infarction, oedema, mass effect, chronic ischaemic change (all on κ)",
      sorted(set(PH) - set(passed)) == sorted(["acute_infarction", "cerebral_oedema", "mass_effect", "chronic_ischaemic_change"])
      and all(N[f"kappa.{k}.pos"] >= 10 for k in set(PH) - set(passed)))
locs = [k.split(".")[2] for k in N if k.startswith("kappa.list.") and not k.endswith(".pos")
        and N[k] is not None and N[k] >= 0.60 and N[k + ".pos"] >= 10]
claim("four location categories met it: intraparenchymal, subarachnoid, MCA, cerebellum",
      sorted(locs) == sorted(["intraparenchymal", "subarachnoid", "MCA", "cerebellum"]), locs)
claim("herniation, large territorial infarct, hydrocephalus, large-vessel occlusion had fewer than 10 positives",
      all(N[f"kappa.{k}.pos"] < 10 for k in ["herniation", "large_territorial_infarct", "hydrocephalus", "large_vessel_occlusion"]))
ev_src = (HERE / "extractor" / "evaluate_validation.py").read_text()
claim("the criterion in the scoring code is κ ≥ 0.60 and ≥ 10 positives", "k >= 0.60" in ev_src and "pos >= 10" in ev_src)

print("\nMethods as implemented\n")
m46 = (HERE / "46_merge_imaging_features.py").read_text()
claim("reports stored more than 72 h before ICU admission are excluded", "FLOOR_H = -72.0" in m46)
out49 = subprocess.run([sys.executable, str(HERE / "49_independent_reproduction.py")], capture_output=True, text=True).stdout
claim("the update rule (most recent / ever-positive / unknown coding) is reproduced by independent code",
      "→ IDENTICAL" in out49, re.findall(r"→ \w+", out49))
claim("independent code reproduces the primary point estimate", "point estimate +0.000 pp" in out49)
fo = pd.read_csv(HERE.parent / "07_paper2_eicu" / "frozen_params_treatment_free" / "feature_order.csv").feature.tolist()
fp = pd.read_csv(HERE.parent / "07_paper2_eicu" / "frozen_params" / "feature_order.csv").feature.tolist()
claim("the treatment-free state model has the 17 physiological/laboratory emissions only",
      len(fo) == 17 and all(c.endswith("_z") for c in fo))
claim("it excludes exactly mechanical ventilation, CRRT, vasopressors and sedation",
      sorted(set(fp) - set(fo)) == sorted(["mech_vent", "crrt", "vasopressor", "sedative"]), sorted(set(fp) - set(fo)))
s31, s34 = (HERE / "31_decode_treatment_free_all.py").read_text(), (HERE / "34_filtered_state_decoding.py").read_text()
claim("the same frozen treatment-free model supplies the outcome states (31) and the real-time state (34)",
      "frozen_params_treatment_free" in s31 and "frozen_params_treatment_free" in s34)
s35 = (HERE / "35_build_landmark_dataset.py").read_text()
claim("eligibility is decided by the filtered state in the dataset build", "if r.filtered_state == TARGET:" in s35)
M1 = (HERE / "47_m1_models.py").read_text()
claim("models are L2-penalised logistic regressions", "LogisticRegression(max_iter=4000, C=1.0)" in M1 and "StandardScaler()" in M1)

print("\nResults\n")
claim("primary: interval includes zero", includes0(N["confirmatory.delta_capture_lo"], N["confirmatory.delta_capture_hi"]))
claim("primary: upper limit below the 5-point benchmark", N["confirmatory.delta_capture_hi"] < 5)
claim("primary: the same number of events captured by both models (348 of 666 each), as the text says (EN and CN)",
      N["model.M1-D.top10.events_captured"] == N["model.M0+A.top10.events_captured"] == 348
      and "348 of 666 each" in EN and "各捕获 348 个" in CN)
claim("24-h landmark: both models flag 117 of 1,171; the baseline captures more of 84 events than the augmented model",
      N["lm24.flagged"] == 117 and N["lm24.val_at_risk"] == 1171 and N["lm24.val_events"] == 84
      and N["model.M0+A.lm24.capture"] > N["model.M1-D.lm24.capture"]
      and f"the baseline captured {N['model.M0+A.lm24.capture']:.1f}%" in EN)
claim("adding imaging availability changed neither AUROC nor capture (both intervals include zero)",
      includes0(N["ladder.A_vs_full.delta_capture_lo"], N["ladder.A_vs_full.delta_capture_hi"])
      and includes0(round(N["ladder.A_vs_full.delta_auroc_lo"], 6), round(N["ladder.A_vs_full.delta_auroc_hi"], 6)))
claim("adding physiology improved AUROC and capture (both intervals exclude zero)",
      N["ladder.full_vs_state.delta_auroc_lo"] > 0 and N["ladder.full_vs_state.delta_capture_lo"] > 0)
cal = pd.read_csv(HERE / "calibration_validation.csv").set_index("model")
claim("both models over-predict in the later period (negative intercept, mean predicted > observed)",
      (cal.intercept < 0).all() and (cal.mean_pred > cal.observed).all())
claim("intercept-only recalibration removes the offset and leaves the slope unchanged",
      (cal.recal_intercept.abs() < 1e-3).all() and ((cal.recal_slope - cal.slope).abs() < 1e-3).all())
dca = pd.read_csv(HERE / "dca_delta_net_benefit.csv")
claim("decision curves: net-benefit difference includes zero at every reported threshold",
      all(includes0(a, b) for a, b in zip(dca.lo, dca.hi)), f"thresholds {list(dca.threshold)}")
claim("M1-I weights stable: range after truncation within 0.5–2.5 and ESS ≥ 90%",
      N["ipw.weight_min"] > 0.5 and N["ipw.weight_max"] < 2.5 and N["ipw.ess_pct"] >= 90)
support = []
for h, g in v.groupby("landmark_h"):
    im, no = g[g.img_available_locked == 1].ps, g[g.img_available_locked == 0].ps
    inside = ((im >= no.min()) & (im <= no.max())).mean()
    support.append((int(h), round(float(inside), 4)))
claim("propensity ranges overlap at every landmark, 98.0%–100% of imaged within the non-imaged range, none excluded",
      round(100 * min(s for _, s in support), 1) == 98.0 and round(100 * max(s for _, s in support), 1) == 100.0
      and "98.0% to 100% of imaged landmarks" in EN and "98.0% 至 100% 的有影像 landmark" in CN
      and "common support held" not in EN and "均满足共同支撑" not in CN, support)
claim("M1-I: AUROC rose but capture did not improve (interval includes zero)",
      N["m1i.auroc_M1I"] > N["m1i.auroc_M0full"] and includes0(N["m1i.delta_capture_lo"], N["m1i.delta_capture_hi"]))
sens = pd.concat([pd.read_csv(HERE / "sensitivity_results.csv"), pd.read_csv(HERE / "sensitivity_results_11_12.csv")])
claim("sixteen sensitivity analyses, none with an interval excluding zero",
      len(sens) == 16 and all(includes0(a, b) for a, b in zip(sens.lo, sens.hi)))
claim("sensitivity point estimates range −1.43 to +1.00, no upper limit above +3.53 (and the text says so)",
      round(sens.delta_pp.min(), 2) == -1.43 and round(sens.delta_pp.max(), 2) == 1.00 and round(sens.hi.max(), 2) == 3.53
      and "ranged from −1.43 to +1.00" in EN and "exceeded +3.53" in EN)
sub = pd.read_csv(HERE / "subtype_performance.csv")
claim("every subtype interval includes zero", all(includes0(a, b) for a, b in zip(sub.lo, sub.hi)))
sd = pd.read_csv(HERE / "subtype_descriptives.csv")
dev_ev = sd[(sd.cohort == "development") & sd.subtype.isin(["AIS", "ICH", "SAH"])].events
claim("every subtype had at least 280 development events", (dev_ev >= 280).all(), list(dev_ev))
claim("the interaction model did not improve capture", includes0(N["subtype.interaction.lo"], N["subtype.interaction.hi"]))
claim("phenotypes follow the expected pattern (haemorrhage >90% in ICH and SAH, <25% in AIS; MCA AIS > ICH)",
      N["prev.ICH.intracranial_haemorrhage"] > 90 and N["prev.SAH.intracranial_haemorrhage"] > 90
      and N["prev.AIS.intracranial_haemorrhage"] < 25 and N["prev.AIS.territory_mca"] > N["prev.ICH.territory_mca"])

print("\nPost hoc redundancy analysis\n")
claim("imaging increment over the weakest baseline excludes zero", N["redund.B1.d_capture_lo"] > 0)
claim("after the state is added, the increment interval includes zero, and stays so at B3 and B4",
      all(includes0(N[f"redund.B{i}.d_capture_lo"], N[f"redund.B{i}.d_capture_hi"]) for i in (2, 3, 4)))
s50 = (HERE / "50_redundancy_posthoc.py").read_text()
claim("baselines are nested in the order stated (B2 = B1 + state, B3 = B2 + GCS, B4 = B2 + GCS + other)",
      'B2 = B1 + ["s0", "s2", "s3", "entropy"]' in s50 and "B3 = B2 + GCS" in s50 and "B4 = B2 + GCS + OTHER" in s50)
claim("no model with GCS but without the state was fitted (so GCS alone is not assessed)",
      all(not ("GCS" in line and "B1" in line and "B2" not in line) for line in s50.splitlines() if line.startswith("B")))

print("\nWording boundaries\n")
abs_en = EN.split("**Conclusions.**")[1].split("**Keywords")[0]
abs_cn = CN.split("**结论**")[1].split("**关键词")[0]
claim("abstract conclusion (EN) carries no post hoc overlap statement", not re.search(r"overlap|post hoc", abs_en, re.I))
claim("abstract conclusion (CN) carries no post hoc overlap statement", not re.search("重叠|事后", abs_cn))
con_en = EN.split("### Conclusions")[1].split("## Additional files")[0]
con_cn = CN.split("## 结论")[1].split("# 参考文献")[0]
claim("main conclusion states the overlap as possible (EN 'may', CN '可能')",
      re.search(r"may overlap", con_en) and "可能存在明显重叠" in con_cn)
claim("title names radiology-report-derived phenotypes, not neuroimaging in general",
      "Radiology-Report-Derived Neuroimaging Phenotypes" in EN.splitlines()[0] and "放射报告衍生神经影像表型" in CN[:200])
BANNED_EN = ["captured by the", "absorb", "did not remove", "whereas the state did", "clinically equivalent",
             "non-inferior to", "noninferior", "Most, however", "already expressed", "held in all", "did not depend", "re-estimated"]
hits = [p for p in BANNED_EN if p.lower() in EN.lower()]
claim("English draft contains none of the removed overstatements", not hits, hits)
BANNED_CN = ["吸收", "被动态 ICU 状态所捕获", "均成立", "不取决于", "已经通过意识", "单独加入格拉斯哥昏迷量表评分并不能"]
hits = [p for p in BANNED_CN if p in CN]
claim("Chinese draft contains none of the removed overstatements", not hits, hits)
claim("equivalence appears only in the sentence denying it",
      [m.start() for m in re.finditer("equivalence", EN)] == [EN.index("significance, equivalence or non-inferiority threshold") + len("significance, ")]
      and CN.count("等效") == CN.count("显著性、等效性或非劣效性界值"))


def paragraphs_mentioning(text, pattern):
    return [p for p in re.split(r"\n\s*\n", text) if re.search(pattern, p)]


body_en = EN.split("## References")[0]
unlabelled = [p[:70] for p in paragraphs_mentioning(body_en, r"[Rr]edundancy")
              if not re.search(r"[Pp]ost hoc", p)]
claim("every English paragraph mentioning the redundancy analysis labels it post hoc", not unlabelled, unlabelled)
body_cn = CN.split("# 参考文献")[0]
unlabelled = [p[:40] for p in paragraphs_mentioning(body_cn, "冗余") if "事后" not in p]
claim("every Chinese paragraph mentioning the redundancy analysis labels it post hoc", not unlabelled, unlabelled)
claim("reliability criterion is described as an eligibility rule, not interchangeability (EN and CN)",
      "not as a claim of clinical interchangeability" in EN and "并不意味着自动抽取可以替代" in CN)
claim("single-annotator reference standard is stated in Methods and Limitations (EN)",
      EN.count("single trained annotator") >= 2 and "not with a multi-expert consensus" in EN)

# ---- audit of inherited preprocessing (added 18 Sep 2026)
au = pd.read_csv(HERE / "audit_unseen_patients.csv")
claim("state-only baseline no better in patients used to estimate the state model (seen AUROC ≤ unseen)",
      au.auroc_M0state[2] <= au.auroc_M0state[1] and au.patients[1] + au.patients[2] == au.patients[0])
claim("'result was similar in patients not used': unseen interval includes zero, upper limit < 5 pp",
      includes0(au.lo[1], au.hi[1]) and au.hi[1] < 5)
claim("'most temporal-validation patients' were in the state model's training split (> 50%)",
      au.patients[2] / au.patients[0] > 0.5)
lt = pd.read_csv(HERE / "audit_lab_result_time.csv").iloc[0]
claim("'about one in six' laboratory values resulted after the landmark (1/6 = 16.7% ± 2 pp)",
      abs(lt.resulted_after_landmark_pct - 100 / 6) < 2 and "about one in six" in EN and "约六分之一" in CN)
_p90 = f"{lt.p90_delay_after_landmark_h_if_late:.2f}"
claim(f"delay stated as a 90th percentile of {_p90} h, never as a maximum (EN and CN)",
      f"90th percentile delay of {_p90} hours" in EN and f"第 90 百分位约为 {_p90} 小时" in CN
      and "up to about" not in EN and "最多约" not in CN)
claim("Methods do not claim that only information available at the landmark was used (EN and CN)",
      "only information recorded before a landmark" not in EN and "仅使用截至该时点" not in CN
      and "status available at each landmark" not in EN and "时点可获得的" not in CN)
claim("post-audit analyses are not called sensitivity analyses and have their own Results subsection",
      "### Post-audit analyses" in EN and "## 审计后追加分析" in CN and "not counted among the sensitivity analyses" in EN
      and "不计入上述敏感性分析" in CN and "analyses added after the audit" not in EN)
claim("no 'nearly doubling' / 'strongly associated' / 'clear prognostic' emphasis (EN and CN)",
      not any(w in EN for w in ["nearly doubl", "strongly associated", "prognostic on their own"])
      and not any(w in CN for w in ["几乎翻", "密切相关", "明显的预后"]))
claim("state-representation independence limitation uses the agreed wording (EN)",
      "not fully independent with respect to estimation of the pre-existing state representation" in EN)
ls = pd.read_csv(HERE / "audit_lab_result_time_sensitivity.csv")
claim("result-time rebuild 'did not change the result': interval includes zero, upper limit < 5 pp; row 1 reproduces primary",
      includes0(ls.lo[1], ls.hi[1]) and ls.hi[1] < 5 and abs(ls.delta_pp[0] - N["confirmatory.delta_capture"]) < 1e-12)
claim("audit analyses are labelled as not in the protocol (EN and CN)",
      "not in the protocol" in EN and "不属于研究方案" in CN and "not prespecified" in EN and "非预设" in CN)
claim("the 'no upper limit above +3.53' sentence is restricted to prespecified analyses (EN)",
      "No prespecified sensitivity analysis showed" in EN)

print("\nRepeated extraction with a larger model (protocol v1.3, C1)\n")
SUP = (MS / "supplement_v1.md").read_text(encoding="utf-8")
SUPCN = (MS / "supplement_v1_CN.md").read_text(encoding="utf-8")
print("\nCorrections D1 and D2 (protocol v1.4, v1.5)\n")
_lm = pd.read_csv(HERE / "landmark_dataset.csv", usecols=["stay_id", "landmark_h"])
_co = pd.read_csv(HERE.parent / "04_outputs" / "tables" / "patient_level_cohort.csv", parse_dates=["intime", "deathtime"])
_co["dh"] = (_co.deathtime - _co.intime).dt.total_seconds() / 3600
_x = _lm.merge(_co[["stay_id", "dh"]], on="stay_id")
claim("D1: no landmark in the analysis lies at or after the recorded death", not (_x.dh.notna() & (_x.dh <= _x.landmark_h)).any())
claim("D2: sensitivity analysis 3 targets canonical state 1 (respiratory support)",
      "TARGET_P1 = 1" in (HERE / "48_sensitivity_analyses.py").read_text())
claim("the supplement states that the corrected results replace the original ones and that every conclusion is unchanged (EN and CN)",
      "the corrected results replace the original ones throughout" in SUP and "Every conclusion is unchanged" in SUP
      and "全文均以修正后的结果取代原结果" in SUPCN and "所有结论均未改变" in SUPCN)
claim("the C1 analysis rebuilt the primary result exactly before running C1-a and C1-b",
      all(abs(N[f"c1.selfcheck.{a}"] - N[f"confirmatory.delta_capture{b}"]) < 1e-9 for a, b in (("delta", ""), ("lo", "_lo"), ("hi", "_hi"))))
for t, lab in (("a", "same seven findings"), ("b", "nine findings")):
    claim(f"'did not change the result' — C1-{t} ({lab}): interval includes zero and upper limit < 5 pp (C1.6 rule 2)",
          includes0(N[f"c1.{t}.lo"], N[f"c1.{t}.hi"]) and N[f"c1.{t}.hi"] < 5)
_ph = ["intracranial_haemorrhage", "acute_infarction", "cerebral_oedema", "mass_effect", "midline_shift_present",
       "chronic_ischaemic_change", "intraventricular_haemorrhage"]
_cats = ["intraparenchymal", "subarachnoid", "subdural", "ACA", "MCA", "PCA", "watershed", "frontal", "parietal",
         "temporal", "occipital", "insula", "basal_ganglia", "thalamus", "brainstem", "cerebellum"]
_pass = {k for k in _ph if N[f"c1.kappa.{k}"] >= 0.60 and N[f"kappa.{k}.pos"] >= 10} | \
        {c for c in _cats if N.get(f"c1.kappa.list.{c}", -1) >= 0.60 and N[f"kappa.list.{c}.pos"] >= 10}
claim("'the nine that met the reliability criterion' are the seven plus oedema and occipital, by B9 on the second extractor",
      _pass == {"intracranial_haemorrhage", "intraventricular_haemorrhage", "midline_shift_present", "cerebral_oedema",
                "intraparenchymal", "subarachnoid", "MCA", "cerebellum", "occipital"} and N["c1.b.n_features"] == 9
      and N["c1.a.n_features"] == 7, f"passing: {sorted(_pass)}")
_d = [N[f"c1.kappa.{k}"] - N[f"kappa.{k}"] for k in _ph]
claim("'agreed only slightly better': mean κ change over the seven candidate phenotypes < 0.10, none > 0.15",
      float(np.mean(_d)) < 0.10 and max(_d) < 0.15, f"mean {np.mean(_d):+.3f}, range {min(_d):+.2f} to {max(_d):+.2f}")
claim("every report the larger model could not process failed by output overflow, and includes the fixed extractor's two",
      N["c1.run.quarantined_in_frozen_quarantine"] == N["c1.run.frozen_quarantined"] == 2
      and (pd.read_csv(HERE / "c1_second_extractor" / "analysis_population_c1_failed.csv").error == "JSONDecodeError").all())
claim("C1 has its own Results subsection, is labelled as after the primary result, and is not called a sensitivity analysis (EN and CN)",
      "### Repeated extraction with a larger model" in EN and "## 更大模型重新抽取" in CN
      and "after the primary result was known, with a larger language model" in EN and "在主要结果得到之后，我们用一个更大的语言模型" in CN
      and "sensitivity" not in EN.split("### Repeated extraction with a larger model")[1].split("###")[0])
_fr = (HERE / "c1_second_extractor" / "EXTRACTOR_FREEZE_C1.md").read_text(encoding="utf-8")
claim("the larger model is named as in its freeze record (Qwen3.8, 27 billion parameters) in Methods and Results, EN and CN, "
      "and its Methods paragraph says it was added to the protocol before the model processed any report",
      "qwen3.8:27b" in _fr and "27.3 billion parameters" in _fr and EN.count("Qwen3.8, 27 billion parameters") == 2 and CN.count("Qwen3.8，270 亿参数") == 2
      and "**Repeated extraction with a larger model.** After the primary result was known" in EN
      and "added to the protocol before the model processed any report" in EN and "在该模型处理任何报告之前写入研究方案" in CN)
claim("the Limitations sentence keeps the single-annotator limitation explicit (EN and CN)",
      "not the reliance on a single reference standard" in EN and "参照标准仅来自一名标注者" in CN)
claim("the supplement labels C1 post hoc, dated to protocol v1.3 before the model processed any report, and not replacing the primary result",
      "reported as a post hoc analysis and does not replace the primary result" in SUP
      and "before the second model was installed or had processed any report" in SUP
      and "作为事后分析报告，不替代主要结果" in SUPCN)
claim("C1 does not appear in the abstract, Table 4 or the Conclusions (C1.6 rule 3)",
      "larger" not in EN.split("## Background")[0] and "larger model" not in EN.split("### Table 4")[1].split("### Table 5")[0]
      and "larger" not in EN.split("### Conclusions")[1].split("## Additional files")[0])

print("\nDiagnostic and Prognostic Research format (4 Oct 2026)\n")
_ab = EN.split("## List of abbreviations")[1].split("## Declarations")[0]
_listed = set(re.findall(r"(?:^|; )\s*([A-Z][A-Za-z+\-]*[A-Z+]),", _ab.strip()))
_body = EN.split("## Background")[1].split("## Additional files")[0] + EN.split("## Tables")[1]   # text, tables, legends
_cand = {"AIS", "AUPRC", "AUROC", "CI", "CT", "GCS", "ICH", "ICU", "IPW", "IQR", "IVH", "LLM", "MCA", "MRI", "SAH", "TRIPOD+AI"}
_used = {a for a in _cand if re.search(rf"(?<![A-Za-z]){re.escape(a)}(?![A-Za-z])", _body)}
claim("every abbreviation used in the main text is in the list, and every listed one is used",
      _used == _listed, f"used {sorted(_used)}; listed {sorted(_listed)}")
_decl = EN.split("## Declarations")[1].split("\n---\n")[0]
_heads = ["Ethics approval and consent to participate", "Consent for publication", "Availability of data and materials",
          "Competing interests", "Funding", "Authors' contributions", "Acknowledgements"]
claim("Declarations carries the seven headings the journal requires, in its order",
      [h for h in _heads if f"**{h}.**" in _decl] == _heads
      and sorted(_decl.index(f"**{h}.**") for h in _heads) == [_decl.index(f"**{h}.**") for h in _heads])
claim("the main text refers to 'Additional file 1', never to 'Supplementary' material (EN and CN)",
      "Supplementary" not in EN.split("## Additional files")[0] and "补充方法" not in CN.split("# 参考文献")[0]
      and "补充表" not in CN.split("# 参考文献")[0] and "Additional file 1" in EN)
claim("figure and table titles have at most 15 words (EN)",
      all(len(t.split()) <= 15 for t in re.findall(r"^\*\*Figure \d+\.\*\* ([^.]+)\.", EN, re.M))
      and all(len(t.split()) <= 15 for t in re.findall(r"^### Table \d+\. (.+)$", EN, re.M)))
claim("the title states the study design", "a retrospective cohort study with temporal validation" in EN.split("\n")[0])

bad = R.count(False)
print(f"\n{len(R)} claims checked, {bad} failed")
sys.exit(1 if bad else 0)
