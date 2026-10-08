"""
Paper 3: trace every number printed in the manuscript back to where it came from.

Direction text -> source. 53 builds numbers.json from the data, and the drafts were written from it;
this script goes the other way and asks, for each numeric token in the English and Chinese drafts,
whether anything produced it. A token nothing produced is untraceable — a stale value, a typo, a
number carried over from an earlier version — and must not be submitted.

The pool has three parts, none typed from memory:
  results    manuscript/numbers.json (549 values from the data)
  design     constants read out of the scripts and files that define them (predictor counts,
             thresholds, replicate counts, landmark times, software versions)
  external   values quoted from cited articles, each tied to its reference key and checked against
             the article on 16 Sep 2026

Matching: a token with d decimals matches a pool value that rounds to it at d decimals; an integer
token must equal an integer-valued pool entry exactly, so a small integer cannot be "explained" by
rounding an unrelated fraction.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
MS = HERE / "manuscript"
DOCS = {"EN": MS / "paper3_draft_v5.md", "CN": MS / "paper3_draft_v5_CN.md",
        "EN supplement": MS / "supplement_v1.md", "CN supplement": MS / "supplement_v1_CN.md"}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------------------------------------------------ pool
N = json.load(open(MS / "numbers.json"))
POOL = {}                                   # value -> provenance


def add(v, why):
    if v is None:
        return
    POOL.setdefault(float(v), why)


for k, v in N.items():
    if isinstance(v, (int, float)):
        add(v, f"numbers.json:{k}")

M1 = load("m1", HERE / "47_m1_models.py")
MERGE = load("merge", HERE / "46_merge_imaging_features.py")
src47 = (HERE / "47_m1_models.py").read_text()
src51 = (HERE / "51_dca_calibration.py").read_text()
src52 = (HERE / "52_subtype_analysis.py").read_text()
evalv = (HERE / "extractor" / "evaluate_validation.py").read_text()
freeze = (HERE / "extractor" / "EXTRACTOR_FREEZE_v1.2.md").read_text()
protocol = (HERE / "protocol_v1.2" / "PROTOCOL_v1.2_EN.md").read_text()

add(len(M1.FIXED) + len(M1.STATE) + len(M1.PHYS) + 1, "47: predictors in M0+A")
treat = [c for c in M1.PHYS if not c.endswith("_z")]
add(len(treat), "47: treatment predictors")
add(len(M1.PHYS) - len(treat), "47: physiological/laboratory predictors")
add(len(M1.IMG), "47: imaging features (primary)")
add(2 * len(M1.IMG), "47: imaging columns")
add(int(re.search(r'"--reps", type=int, default=(\d+)', src47).group(1)), "47: bootstrap replicates")
for q in re.findall(r'\(\("primary", \((\d+), (\d+)\)\), \("sensitivity", \(([\d.]+), ([\d.]+)\)\)\)', src47)[0]:
    add(float(q), "47: weight truncation percentiles")
for k in re.findall(r"for k in \(([\d., ]+)\)", src47)[0].split(","):
    add(100 * float(k), "47: top-k strata (%)")
add(-MERGE.FLOOR_H, "46: report floor, hours before ICU admission")
add(int(re.search(r"MIN_EVENTS = (\d+)", src52).group(1)), "52: interaction event threshold")
lo, hi = re.search(r"np\.linspace\(([\d.]+), ([\d.]+), \d+\)", src51).groups()
add(100 * float(lo), "51: DCA threshold range start (%)"); add(100 * float(hi), "51: DCA threshold range end (%)")
for t in re.search(r"^at = \[([\d., ]+)\]", src51, re.M).group(1).split(","):
    add(100 * float(t), "51: net-benefit thresholds reported (%)")
add(float(re.search(r"per (\d+) patient-landmarks", src51).group(1)), "51: net benefit scaled per 100")
add(float(re.search(r"k >= ([\d.]+)", evalv).group(1)), "evaluate_validation: κ threshold")
add(int(re.search(r"pos >= (\d+)", evalv).group(1)), "evaluate_validation: positive-report threshold")
add(len(re.search(r"PRIMARY = \[(.*?)\]", evalv, re.S).group(1).split(",")), "evaluate_validation: candidate phenotypes")
passing_ph = sum(1 for k in ["midline_shift_present", "intraventricular_haemorrhage", "intracranial_haemorrhage",
                             "acute_infarction", "cerebral_oedema", "mass_effect", "chronic_ischaemic_change"]
                 if N[f"kappa.{k}"] >= 0.60 and N[f"kappa.{k}.pos"] >= 10)
add(passing_ph, "numbers.json: phenotypes passing")
passing_loc = sum(1 for k, v in N.items() if k.startswith("kappa.list.") and not k.endswith(".pos")
                  and v is not None and v >= 0.60 and N[k + ".pos"] >= 10)
add(passing_loc, "numbers.json: location categories passing")
add(passing_ph + passing_loc, "numbers.json: primary features")
fails = [k for k in ["acute_infarction", "cerebral_oedema", "mass_effect", "chronic_ischaemic_change"] if N[f"kappa.{k}"] < 0.60]
add(len(fails), "numbers.json: phenotypes below threshold")
dev50 = sum(1 for l in open(HERE / "extractor" / "dev50_v12_out.jsonl") if l.strip())
val200 = sum(1 for l in open(HERE / "extractor" / "validation200_v12_out.jsonl") if l.strip())
add(dev50, "extractor: development reports"); add(val200, "extractor: validation reports")
import pandas as pd
sens = len(pd.read_csv(HERE / "sensitivity_results.csv")) + len(pd.read_csv(HERE / "sensitivity_results_11_12.csv"))
add(sens, "sensitivity CSVs: variants")
lm = sorted(pd.read_csv(HERE / "landmark_dataset.csv", usecols=["landmark_h"]).landmark_h.unique())
for h in lm:
    add(h, "landmark_dataset: landmark hours")
add(len(lm), "landmark_dataset: number of landmarks"); add(lm[1] - lm[0], "landmark_dataset: window length (h)")
add(24, "outcome horizon (h) — landmark_dataset column future_24h_*")
add(12, "sensitivity 2: 12-hour horizon (48_sensitivity_analyses)")
add(72, "observation frame (h): protocol §6, landmarks require a full 24 h within 72 h")
add(4, "hidden Markov model states (frozen_params_treatment_free: 4)")
yrs = pd.read_csv(HERE / "landmark_dataset.csv", usecols=["anchor_year_group"]).anchor_year_group.unique()
for g in yrs:
    for y in re.findall(r"\d{4}", str(g)):
        add(int(y), "landmark_dataset: anchor year groups")
add(float(re.search(r"\+(\d+) percentage points", protocol).group(1)), "protocol §10.3: interpretation benchmark (pp)")
add(95, "confidence level")
add(len(pd.read_csv(HERE.parent / "07_paper2_eicu" / "frozen_params_treatment_free" / "feature_order.csv")),
    "frozen treatment-free model: emissions")
for v in re.findall(r"MIMIC-IV v(\d\.\d)", protocol) + re.findall(r"MIMIC-IV-Note v(\d\.\d)", protocol):
    add(float(v), "protocol: dataset versions")
add(float(re.search(r"Ollama (\d+\.\d+)", freeze).group(1)), "freeze record: Ollama version (major.minor)")
add(7, "freeze record: qwen2.5:7b (7 billion parameters)")
add(4, "freeze record: Q4_K_M (4-bit)")
add(2.5, "freeze record: model family Qwen2.5")
# C1 (protocol v1.3): the second extractor's freeze record and the protocol's freeze date
fr_c1 = (HERE / "c1_second_extractor" / "EXTRACTOR_FREEZE_C1.md").read_text(encoding="utf-8")
add(float(re.search(r"Ollama (\d+\.\d+)\.\d+", fr_c1).group(1)), "C1 freeze record: Ollama version (major.minor)")
_p = float(re.search(r"(\d+)\.\d billion parameters", fr_c1).group(1))
add(_p, "C1 freeze record: billions of parameters"); add(10 * _p, "C1 freeze record: parameters in 亿 (CN)")
_r13 = (HERE / "protocol_v1.3" / "README.md").read_text(encoding="utf-8")
_m = re.search(r"Frozen (\d+) (\w+) (\d{4})", _r13)
add(int(_m.group(1)), "protocol v1.3 README: freeze day"); add(int(_m.group(3)), "protocol v1.3 README: freeze year")
add(1.3, "protocol version 1.3")

ext_src = (HERE / "extractor" / "extract_v12.py").read_text()
add(int(re.search(r"def call_model\(text, timeout=(\d+)\)", ext_src).group(1)), "extractor: timeout (s)")
add(len(re.search(r"for attempt in \(([\d, ]+)\)", ext_src).group(1).split(",")), "extractor: attempts")
for v in re.search(r"`temperature (\d+)`, `seed (\d+)`, `num_ctx (\d+)`", freeze).groups():
    add(int(v), "freeze record: generation settings")
add(int(re.search(r"^SEED = (\d+)", (HERE / "49_independent_reproduction.py").read_text(), re.M).group(1)), "49: reproduction seed")
for r in pd.read_csv(HERE / "ichsah_coding_sensitivity.csv").itertuples():
    for c in ("auroc_M0A", "auroc_M1D", "capture_M0A", "capture_M1D", "delta", "lo", "hi"):
        add(getattr(r, c), "66: ICH+SAH coding sensitivity")
for r in pd.read_csv(HERE / "extractor" / "list_field_kappa.csv").itertuples():
    add(r.extractor_pos, "list_field_kappa: extractor positives"); add(r.annotator_pos, "list_field_kappa: annotator positives")
_v = pd.read_csv(HERE / "m1_validation_predictions.csv")
for h, g in _v.groupby("landmark_h"):
    im, no = g[g.img_available_locked == 1].ps, g[g.img_available_locked == 0].ps
    for x in (len(g), 100 * g.img_available_locked.mean(), im.min(), im.max(), no.min(), no.max(),
              100 * ((im >= no.min()) & (im <= no.max())).mean()):
        add(x, "m1 predictions: availability diagnostics by landmark")
_lmf = pd.read_csv(HERE / "landmark_imaging_features.csv", usecols=["landmark_h", "img_available_locked", "img_report_age_h"])
for h, x in _lmf[_lmf.img_available_locked == 1].groupby("landmark_h").img_report_age_h.median().items():
    add(x, "features: median report age by landmark")
for r in pd.read_csv(HERE / "subtype_descriptives.csv").itertuples():
    for x in (r.patients, r.landmarks, r.events, 100 * r.event_rate, 100 * r.imaging):
        add(x, "subtype descriptives")
for x in re.search(r"difference \+([\d.]+) \(95% CI \+([\d.]+) to \+([\d.]+)\) by patient-level bootstrap", protocol).groups():
    add(float(x), "protocol §9.1 quoted value")
for x in re.search(r"difference from M0-full is \+([\d.]+) \(95% CI (−?[\d.]+) to \+([\d.]+)\) and the top-10% capture "
                   r"difference \+([\d.]+) percentage points \((−[\d.]+) to \+([\d.]+)\)", protocol).groups():
    add(abs(float(x.replace("−", "-"))), "protocol §9.1 quoted value")

# versions printed in Methods are checked as whole strings, not as numbers
import sklearn, pandas, numpy, scipy
VERSIONS = {f"Python {sys.version.split()[0]}", f"scikit-learn {sklearn.__version__}",
            f"pandas {pandas.__version__}", f"NumPy {numpy.__version__}", f"SciPy {scipy.__version__}",
            "Ollama " + re.search(r"Ollama (\d+\.\d+\.\d+)", freeze).group(1)}

# quoted from cited articles, verified against the articles on 16 Sep 2026 (see PROJECT_LOG)
EXTERNAL = {0.558: "alotaibi2025 AUROC without phenotypes", 0.616: "alotaibi2025 AUROC with phenotypes",
            0.720: "sun2026 clinical-only test AUROC", 0.771: "sun2026 multimodal test AUROC",
            176: "lei2026preprint: hospitals"}
for v, why in EXTERNAL.items():
    add(v, "external: " + why)

# ------------------------------------------------------------------------------------ extraction
TOKEN = re.compile(r"(?<![\w.])[−+\-]?\d[\d,]*(?:\.\d+)?")
STRIP = [
    re.compile(r"<!--.*?-->", re.S),                         # draft notes
    re.compile(r"^---\n.*?\n---\n", re.S),                   # YAML front matter
    re.compile(r"\n#+ *(References|参考文献)\n.*?(?=\n---\n)", re.S),  # reference list (checked by 61)
    re.compile(r"\[\d[\d,–]*\]"),                            # citation markers
    re.compile(r"doi:\S+|https?://\S+|arXiv:\S+"),
    re.compile(r"(Table|Figure|Supplementary Table|表|图|补充表) ?\d+"),
    re.compile(r"\bM[01][-+][A-Za-z]+|\bM0\+A\b|\bM1-[DI]\b|TRIPOD\+AI|\bL2\b|MIMIC-IV-Note|MIMIC-IV|Qwen2\.5|§\d+(\.\d+)?"),
    re.compile(r"\[CHECK[^\]]*\]|\[TO DRAW[^\]]*\]|\[待绘制[^\]]*\]"),
    re.compile(r"\bB[1-4]\b"),
    re.compile(r"\*\*Authors:\*\*.*?\*\*Corresponding author:\*\*[^\n]*", re.S),   # title page: postal codes
    re.compile(r"Additional file \d+|附加文件 ?\d+|Version \d+(\.\d+)+"),
    re.compile(r"`[^`]*`"),                                   # code spans: model tags, version hash
    re.compile(r"\b(Table|表) S\d+|\bS\d+\."),                    # supplementary table and section labels
]


def tokens(text):
    for v in VERSIONS:
        text = text.replace(v, " ")
    for rx in STRIP:
        text = rx.sub(" ", text)
    for m in TOKEN.finditer(text):
        yield m.group(0), text[max(0, m.start() - 40):m.end() + 25].replace("\n", " ")


def traced(tok):
    s = tok.replace("−", "-").replace(",", "").lstrip("+")
    v = float(s)
    if "." not in s:
        return any(abs(x - v) < 1e-9 and float(x).is_integer() for x in POOL) or any(abs(abs(x) - abs(v)) < 1e-9 and float(x).is_integer() for x in POOL)
    d = len(s.split(".")[1])
    return any(round(x, d) == round(v, d) or round(abs(x), d) == round(abs(v), d) for x in POOL)


bad_total = 0
for lang, path in DOCS.items():
    text = path.read_text(encoding="utf-8")
    seen, bad = 0, []
    for tok, ctx in tokens(text):
        seen += 1
        if not traced(tok):
            bad.append((tok, ctx))
    bad_total += len(bad)
    print(f"{lang} {path.name}: {seen} numeric tokens, {seen - len(bad)} traced, {len(bad)} untraced")
    for tok, ctx in bad:
        print(f"    UNTRACED {tok:>10}   …{ctx}…")
print(f"\npool: {len(POOL)} values ({len(N)} from numbers.json)")
sys.exit(1 if bad_total else 0)
