"""
Paper 3: check every table cell against the specific value it is supposed to show.

58 proves that each number has *some* source. It cannot see a right number in the wrong cell — an
AUROC of the neighbouring model, a development percentage in the validation column. This script
builds each table row from numbers.json, key by key, formatted to the decimals the table prints,
and compares it with the row in the English draft; the Chinese draft's rows must carry the same
numbers in the same order.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
MS = HERE / "manuscript"
N = json.load(open(MS / "numbers.json"))
EN = (MS / "paper3_draft_v5.md").read_text(encoding="utf-8")
CN = (MS / "paper3_draft_v5_CN.md").read_text(encoding="utf-8")
NUM = re.compile(r"[−+\-]?\d[\d,]*(?:\.\d+)?")
BAD = []


def f(v, d, sign=False):
    s = f"{abs(v):,.{d}f}" if abs(v) >= 1000 else f"{abs(v):.{d}f}"
    if v < 0 and s.strip("0.,") != "":
        return "−" + s
    return ("+" + s) if (sign and v > 0) else s


def rows(text, start, stop):
    block = text[text.index(start):]
    block = block[:block.index(stop)] if stop in block else block
    out, header_seen = [], False
    for line in block.splitlines():
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        if not header_seen:                 # the header row names columns (n = …, years, 95% CI)
            header_seen = True
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        nums = NUM.findall(" ".join(cells[1:]))
        if nums:
            out.append((cells[0], [n.lstrip("+") if n.startswith("+") else n for n in nums]))
    return out


def check(title, en_rows, cn_rows, expected):
    print(f"\n{title}")
    if len(en_rows) != len(expected):
        BAD.append(title); print(f"  BAD row count: draft {len(en_rows)}, expected {len(expected)}")
    for (label, got), (name, exp) in zip(en_rows, expected):
        exp = [e.lstrip("+") for e in exp]
        ok = got == exp
        print(f"  {'OK ' if ok else 'BAD'}  {name}" + ("" if ok else f"\n        draft    {got}\n        expected {exp}"))
        if not ok:
            BAD.append(f"{title}: {name}")
    if [g for _, g in cn_rows] != [g for _, g in en_rows]:
        BAD.append(f"{title}: CN differs from EN")
        for (le, ge), (lc, gc) in zip(en_rows, cn_rows):
            if ge != gc:
                print(f"  BAD  CN row differs: {lc}: {gc}  vs EN {ge}")
    else:
        print(f"  OK   Chinese table carries the same numbers row by row ({len(cn_rows)} rows)")


# ---------------------------------------------------------------------------------- Table 1
T1 = []
cols = ["all", "dev", "val"]
T1.append(("Age", sum([[f(N[f"t1.{c}.age_median"], 0), f(N[f"t1.{c}.age_q1"], 0), f(N[f"t1.{c}.age_q3"], 0)] for c in cols], [])))
T1.append(("Male", sum([[f(N[f"t1.{c}.male_n"], 0), f(N[f"t1.{c}.male_pct"], 1)] for c in cols], [])))
for s, lab in [("AIS", "AIS"), ("ICH", "ICH"), ("SAH", "SAH"), ("ICH+SAH", "ICH and SAH")]:
    T1.append((lab, sum([[f(N[f"t1.{c}.sub_{s}_n"], 0), f(N[f"t1.{c}.sub_{s}_pct"], 1)] for c in cols], [])))
T1.append(("Charlson", sum([[f(N[f"t1.{c}.charlson_median"], 0), f(N[f"t1.{c}.charlson_q1"], 0), f(N[f"t1.{c}.charlson_q3"], 0)] for c in cols], [])))
for v in ["hypertension", "diabetes", "atrial_fibrillation", "heart_failure", "ckd"]:
    T1.append((v, sum([[f(N[f"t1.{c}.{v}_n"], 0), f(N[f"t1.{c}.{v}_pct"], 1)] for c in cols], [])))
T1.append(("Imaging at first landmark", sum([[f(N[f"t1.{c}.first_landmark_imaging_n"], 0), f(N[f"t1.{c}.first_landmark_imaging_pct"], 1)] for c in cols], [])))
T1.append(("Patient-landmarks", [f(N[f"cohort.{c}.landmarks"], 0) for c in cols]))
T1.append(("Events", sum([[f(N[f"cohort.{c}.events"], 0), f(N[f"cohort.{c}.event_rate_pct"], 1)] for c in cols], [])))
check("Table 1", rows(EN, "### Table 1", "### Table 2"), rows(CN, "**表 1", "**表 2"), T1)

# ---------------------------------------------------------------------------------- Table 2
T2 = []
for k, lab in [("midline_shift_present", "Midline shift"), ("intraventricular_haemorrhage", "IVH"),
               ("intracranial_haemorrhage", "ICH"), ("acute_infarction", "acute infarction"),
               ("cerebral_oedema", "oedema"), ("mass_effect", "mass effect"),
               ("chronic_ischaemic_change", "chronic ischaemic change")]:
    T2.append((lab, [f(N[f"kappa.{k}"], 2), f(N[f"kappa.{k}.pos"], 0)]))
for k, lab in [("intraparenchymal", "intraparenchymal"), ("subarachnoid", "subarachnoid"),
               ("MCA", "MCA"), ("cerebellum", "cerebellum")]:
    T2.append((lab, [f(N[f"kappa.list.{k}"], 2), f(N[f"kappa.list.{k}.pos"], 0)]))
check("Table 2", rows(EN, "### Table 2", "### Table 3"), rows(CN, "**表 2", "**表 3"), T2)

# ---------------------------------------------------------------------------------- Table 3
M = ["M0-state", "M0-full", "M0+A", "M1-D"]
T3 = [("AUROC", [f(N[f"model.{m}.auroc"], 3) for m in M]),
      ("AUPRC", [f(N[f"model.{m}.auprc"], 3) for m in M]),
      ("Brier", [f(N[f"model.{m}.brier"], 3) for m in M]),
      ("capture", [f(N[f"model.{m}.top10.capture"], 1) for m in M]),
      ("PPV", [f(N[f"model.{m}.top10.ppv"], 1) for m in M]),
      ("lift", [f(N[f"model.{m}.top10.lift"], 2) for m in M]),
      ("cal intercept", [f(N[f"model.{m}.cal_intercept"], 2) for m in M]),
      ("cal slope", [f(N[f"model.{m}.cal_slope"], 2) for m in M])]
check("Table 3", rows(EN, "### Table 3", "Primary comparison, imaging-augmented"),
      rows(CN, "**表 3", "主要比较（影像增强模型"), T3)

# ---------------------------------------------------------------------------------- Table 4
def s3(k):
    return [f(N[f"{k}.delta"], 2, True), f(N[f"{k}.lo"], 2), f(N[f"{k}.hi"], 2)]
T4 = [("primary", [f(N["confirmatory.delta_capture"], 2, True), f(N["confirmatory.delta_capture_lo"], 2), f(N["confirmatory.delta_capture_hi"], 2)]),
      ("12 h", s3("sens.2.12_hour_prediction_horizon")),
      ("treatment-inclusive", s3("sens.3.treatment_inclusive_outcome_state")),
      ("deterioration only", s3("sens.4.deterioration_alone_death_competing")),
      ("no treatment predictors", s3("sens.5.no_ventilation_crrt_vasopressor_sedation")),
      ("hard state", s3("sens.6.hard_filtered_state_label_no_posterior")),
      ("discordant excluded", s3("sens.1.discordant_landmarks_excluded")),
      ("6 h excluded", s3("sens.10.6_hour_landmark_excluded")),
      ("unknown to negative", s3("sens.7b.unknown_imaging_set_to_reference")),
      ("uncertain positive", s3("sens.11")),
      ("below-criterion phenotypes", s3("sens.12")),
      ("no 72 h limit", s3("sens.8.update_rule_no_floor")),
      ("24 h limit", s3("sens.8.update_rule_floor_24_h")),
      ("age cap 72 h", s3("sens.8.update_rule_age_cap_72_h")),
      ("gradient boosting", s3("sens.7a.native_missing_handling_gradient_boosting")),
      ("availability model without physiology", s3("sens.9.availability_model_without_physiology")),
      ("truncation 2.5/97.5", s3("sens.9.weight_truncation_p2_5_p97_5")),
      ("audit: unseen patients", s3("audit.unseen")),
      ("audit: labs by result time", s3("audit.labsens"))]
check("Table 4", rows(EN, "### Table 4", "### Table 5"), rows(CN, "**表 4", "**表 5"), T4)

# ---------------------------------------------------------------------------------- Table 5
T5 = []
for i in range(1, 5):
    b = f"redund.B{i}"
    T5.append((f"B{i}", [f(N[f"{b}.auroc_base"], 3), f(N[f"{b}.auroc_img"], 3), f(N[f"{b}.capture_base"], 1),
                         f(N[f"{b}.capture_img"], 1), f(N[f"{b}.d_capture"], 2, True), f(N[f"{b}.d_capture_lo"], 2),
                         f(N[f"{b}.d_capture_hi"], 2)]))
check("Table 5", rows(EN, "### Table 5", "Not part of the protocol"), rows(CN, "**表 5", "不属于研究方案"), T5)

print(f"\n{'ALL TABLE CELLS MATCH' if not BAD else str(len(BAD)) + ' PROBLEM(S)'}")
sys.exit(1 if BAD else 0)
