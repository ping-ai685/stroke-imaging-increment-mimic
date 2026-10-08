"""
Paper 3: build the supplementary material (English and Chinese) from the analysis outputs.

Every table is generated here from numbers.json and the result CSVs; every number in the methods text is
read from the file or code that defines it (freeze record, extractor source, protocol, manifest). Nothing
is typed. Writes manuscript/supplement_v1.md and manuscript/supplement_v1_CN.md; 62 builds the .docx files
and runs the number-tracing check over both.

No report text, no row-level data.
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
freeze = (HERE / "extractor" / "EXTRACTOR_FREEZE_v1.2.md").read_text()
extract_src = (HERE / "extractor" / "extract_v12.py").read_text()
protocol = (HERE / "protocol_v1.2" / "PROTOCOL_v1.2_EN.md").read_text()
MINUS = "−"


def f(v, d, sign=False):
    s = f"{abs(v):,.{d}f}"
    if v < 0 and s.strip("0.,"):
        return MINUS + s
    return ("+" + s) if sign and v > 0 else s


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


# --------------------------------------------------------------------------------- facts from sources
PV = re.search(r"`prompt_version` \| \*\*(\w+)\*\*", freeze).group(1)
MODEL = re.search(r"Model \| `([^`]+)` \(([^,]+),", freeze).groups()
OLLAMA = re.search(r"Ollama (\d+\.\d+\.\d+)", freeze).group(1)
GEN = re.search(r"Generation \| `temperature (\d+)`, `seed (\d+)`, `num_ctx (\d+)`", freeze).groups()
TIMEOUT = int(re.search(r"def call_model\(text, timeout=(\d+)\)", extract_src).group(1))
ATTEMPTS = len(re.search(r"for attempt in \(([\d, ]+)\)", extract_src).group(1).split(","))
old91 = re.search(r"difference \+([\d.]+) \(95% CI \+([\d.]+) to \+([\d.]+)\) by patient-level bootstrap", protocol).groups()
oldA = re.search(r"difference from M0-full is \+([\d.]+) \(95% CI (−?[\d.]+) to \+([\d.]+)\) and the top-10% capture "
                 r"difference \+([\d.]+) percentage points \((−[\d.]+) to \+([\d.]+)\)", protocol).groups()

# reproduction: rerun 49, parse its summary
out49 = subprocess.run([sys.executable, str(HERE / "49_independent_reproduction.py")], capture_output=True, text=True).stdout
rep_pt = float(re.search(r"point estimate ([+-][\d.]+) pp", out49).group(1))
rep_ci = [float(x) for x in re.search(r"95% CI \[([+-][\d.]+), ([+-][\d.]+)\]", out49).groups()]
rep_seed = int(re.search(r"seed (\d+), \d+ replicates", out49).group(1))
rep_auc = [float(x) for x in re.search(r"AUROC M0\+A ([\d.]+)\s+M1-D ([\d.]+)", out49).groups()]
rep_identical = "→ IDENTICAL" in out49

lm = pd.read_csv(HERE / "landmark_dataset.csv", usecols=["stay_id", "landmark_idx", "landmark_h", "note_era"])
lm = lm[lm.note_era].merge(pd.read_csv(HERE / "landmark_imaging_features.csv",
                                       usecols=["stay_id", "landmark_idx", "img_available_locked", "img_report_age_h"]),
                           on=["stay_id", "landmark_idx"], validate="one_to_one")
age = lm[lm.img_available_locked == 1].groupby("landmark_h").img_report_age_h.median()
v = pd.read_csv(HERE / "m1_validation_predictions.csv")
ich = pd.read_csv(HERE / "ichsah_coding_sensitivity.csv")
sd = pd.read_csv(HERE / "subtype_descriptives.csv")
prev = pd.read_csv(HERE / "subtype_phenotype_prevalence.csv")
dca = pd.read_csv(HERE / "dca_delta_net_benefit.csv")
lk = pd.read_csv(HERE / "extractor" / "list_field_kappa.csv")

PH = [("midline_shift_present", "Midline shift", "中线移位"), ("intraventricular_haemorrhage", "Intraventricular haemorrhage", "脑室内出血"),
      ("intracranial_haemorrhage", "Intracranial haemorrhage", "颅内出血"), ("acute_infarction", "Acute or subacute infarction", "急性或亚急性梗死"),
      ("cerebral_oedema", "Cerebral oedema", "脑水肿"), ("mass_effect", "Mass effect", "占位效应"),
      ("chronic_ischaemic_change", "Chronic ischaemic change", "慢性缺血改变"), ("herniation", "Herniation", "脑疝"),
      ("large_territorial_infarct", "Large territorial infarct", "大面积梗死"), ("hydrocephalus", "Hydrocephalus", "脑积水"),
      ("large_vessel_occlusion", "Large-vessel occlusion", "大血管闭塞")]
CANDIDATE = {"midline_shift_present", "intraventricular_haemorrhage", "intracranial_haemorrhage", "acute_infarction",
             "cerebral_oedema", "mass_effect", "chronic_ischaemic_change"}
FIELD = {"infarct_territory": ("Territory", "供血区"), "infarct_region": ("Region", "解剖区域"),
         "haemorrhage_compartment": ("Haemorrhage compartment", "出血腔室")}
CAT_CN = {"ACA": "大脑前动脉", "MCA": "大脑中动脉", "PCA": "大脑后动脉", "vertebrobasilar": "椎基底动脉", "watershed": "分水岭",
          "frontal": "额叶", "parietal": "顶叶", "temporal": "颞叶", "occipital": "枕叶", "insula": "岛叶",
          "basal_ganglia": "基底节", "thalamus": "丘脑", "brainstem": "脑干", "cerebellum": "小脑",
          "intraparenchymal": "脑实质内", "subarachnoid": "蛛网膜下腔", "subdural": "硬膜下", "epidural": "硬膜外"}
MODELS = [("M0-state", "Dynamic-state baseline", "动态状态基线"), ("M0-full", "Full physiological baseline", "完整生理基线"),
          ("M0+A", "Imaging-availability baseline", "影像可得性基线"), ("M1-D", "Imaging-augmented model", "影像增强模型")]
SUB = [("AIS", "AIS"), ("ICH", "ICH"), ("SAH", "SAH"), ("ICH+SAH", "ICH and SAH")]
thr, mnp = N["extraction.kappa_threshold"], N["extraction.min_positives"]


def build(lang):
    E = lang == "EN"
    T = lambda en, cn: en if E else cn
    L = []
    A = L.append
    A(T("# Additional file 1: supplementary methods and tables\n\n**Dynamic Risk Stratification for Short-Term Deterioration After Acute Stroke: "
        "Incremental Value of Radiology-Report-Derived Neuroimaging Phenotypes Beyond Dynamic ICU States — a retrospective cohort study with temporal validation**\n",
        "---\ntitle: \"附加文件 1：补充方法与补充表\"\nsubtitle: \"急性卒中后短期恶化的动态风险分层：放射报告衍生神经影像表型在动态 ICU 状态之外的增量价值\"\n---\n"))
    A(T("<!-- Generated by 65_build_supplement.py from the analysis outputs. Do not edit by hand. -->\n",
        "<!-- 由 65_build_supplement.py 从分析结果生成，请勿手工修改。 -->\n"))

    # ------------------------------------------------------------------------- Supplementary Methods
    A(T("## Supplementary Methods\n", "# 补充方法\n"))
    A(T("### S1. Protocol and amendments\n", "## S1. 研究方案与修订\n"))
    A(T("The analysis protocol (version 1.2) was fixed before any validation annotation, before the extractor was fixed, "
        "and before any model containing imaging content was fitted. Amendments made before that point, and every later "
        "decision, were recorded with their date and with whether they preceded the result they governed. Decisions made "
        "after the protocol was fixed were: locking the rule for using imaging reports at landmarks, before any imaging "
        "model was fitted; adding the redundancy analysis, after the primary result was known, and therefore reported as "
        "post hoc; not seeking a second annotator; reporting the coding of patients with both ICH and SAH in this "
        "supplement rather than re-running the pipeline, decided after the corrected coding was shown to change no "
        "reported estimate (Table S10); and correcting implementation errors found during checking, none of which changed "
        "a conclusion (Table S11 and the project log); and, after an audit of the preprocessing inherited from the earlier "
        "study, two analyses with interpretation rules written down before they were run (Tables S12 and S13); and, after "
        "the primary result was known, a repetition of the extraction with a larger model, added to the protocol as version "
        "1.3 before that model processed any report (S6, Table S14). Two further implementation errors were found after "
        "all results were known and corrected under protocol versions 1.4 and 1.5; the corrected results replace the "
        "original ones throughout (Table S15). First, the risk set had admitted landmarks at or after the patient's "
        "recorded death, because time windows ran to ICU discharge, which for some deaths was recorded later than "
        "death; and windows after death had entered the full-sequence decoding that defines the outcome. Landmarks at "
        "or after death were removed, and windows after a death within 72 hours were removed before decoding. Second, "
        "the sensitivity analysis with a treatment-inclusive outcome state had used the wrong state of the earlier "
        "study's model; it now uses the respiratory-support state, as specified.\n",
        "分析方案（1.2 版）在任何验证标注之前、抽取器固定之前、以及任何含影像内容的模型拟合之前即已固定。此前的修订及此后的每一项决定，"
        "均记录日期，并注明是否发生在其所管辖的结果出现之前。方案固定后作出的决定包括：在任何影像模型拟合之前，锁定 landmark 上使用影像"
        "报告的规则；在主要结果已知之后加入冗余分析，因此作为事后分析报告；不再寻求第二位标注者；在确认修正编码不改变任何报告估计值之后，"
        "决定将同时患 ICH 和 SAH 患者的编码问题在本补充材料中报告，而不重跑整个流程（表 S10）；以及更正核对过程中发现的实现错误，"
        "这些更正均未改变任何结论（表 S11 及项目日志）；以及在对沿用自前一项研究的预处理进行审计之后，追加两项判读规则事先书面确定的分析"
        "（表 S12 和 S13）；以及在主要结果已知之后，用更大模型重复抽取，并在该模型处理任何报告之前写入研究方案 1.3 版（S6，表 S14）。另有两项实现错误在全部结果已知之后发现，并按研究方案 1.4 版和 1.5 版修正；"
        "全文均以修正后的结果取代原结果（表 S15）。其一，风险集纳入了处于患者记录死亡时刻或之后的 landmark——时间窗截至 ICU 转出，而部分"
        "死亡患者记录的转出时间晚于死亡时间；死亡之后的时间窗也参与了判定结局的整序列解码。已去除处于死亡时刻或之后的 landmark，并在解码前"
        "去除 72 小时内死亡者死亡之后的时间窗。其二，含治疗结局状态的敏感性分析使用了前一项研究模型中错误的状态；现按方案规定使用呼吸支持型"
        "状态。\n"))

    A(T("### S2. Automated extraction\n", "## S2. 自动抽取\n"))
    A(T(f"Reports were processed by `{MODEL[0]}` ({MODEL[1]} quantisation) through Ollama {OLLAMA} on local hardware, "
        f"with temperature {GEN[0]}, seed {GEN[1]}, a context of {int(GEN[2]):,} tokens and output constrained by a JSON "
        f"schema. Deterministic post-processing verified the model output against the report text — a sentence-scoped rule "
        f"for findings the report says cannot be assessed, a check that each claimed finding and location is mentioned, a "
        f"rule restricting large-vessel occlusion to studies able to assess vessel patency, and cleaning of change "
        f"statements — and every application was logged. The prompt, rules, schema and post-processing code were hashed "
        f"into a version identifier (`{PV}`); every one of the {N['reports.extracted']:,} extracted records carries it. The "
        f"extractor was developed on {N['extraction.dev_reports']} reports and then fixed; it was not changed after "
        f"validation.\n",
        f"报告由本地硬件上通过 Ollama {OLLAMA} 运行的 `{MODEL[0]}`（{MODEL[1]} 量化）处理，温度 {GEN[0]}，随机种子 {GEN[1]}，"
        f"上下文 {int(GEN[2]):,} 个 token，输出受 JSON schema 约束。确定性后处理对照报告原文核验模型输出——包括按句判断报告所称"
        f"无法评估的发现、核对每项所称发现和位置确实在报告中被提及、将大血管闭塞限定于能够评估血管通畅性的检查，以及清理变化描述——"
        f"每次触发均有记录。提示词、规则、schema 和后处理代码被哈希为版本标识（`{PV}`），全部 {N['reports.extracted']:,} 条抽取记录"
        f"均带有该标识。抽取器在 {N['extraction.dev_reports']} 份报告上开发后即固定，验证之后未作修改。\n"))
    A(T(f"**Reports that could not be processed.** {N['reports.quarantined']} of {N['reports.analysis_population']:,} "
        f"reports did not return a valid record within {TIMEOUT} seconds on either of {ATTEMPTS} attempts. Replaying the "
        f"fixed prompt showed the model repeating one anatomical region without end inside the region list; because "
        f"decoding was deterministic, the failure recurred identically on every attempt. A typical record needed a median "
        f"of {N['extraction.output_tokens_median']:.0f} output tokens. The two reports were treated as unavailable — never "
        f"as a negative finding — and were not re-run with a modified extractor.\n",
        f"**无法处理的报告。**{N['reports.analysis_population']:,} 份报告中有 {N['reports.quarantined']} 份在 {ATTEMPTS} 次尝试中"
        f"均未能在 {TIMEOUT} 秒内返回有效记录。重放固定的提示词显示，模型在解剖区域列表中无休止地重复同一个区域；由于解码是确定性的，"
        f"每次尝试都以同样的方式失败。正常记录的输出 token 中位数为 {N['extraction.output_tokens_median']:.0f}。这两份报告按不可得处理"
        f"——从不当作阴性发现——也没有用修改过的抽取器重跑。\n"))

    A(T("### S3. Validation of automated extraction\n", "## S3. 自动抽取的验证\n"))
    A(T(f"{N['extraction.val_reports']} reports were drawn at random from the analysis population, one per patient, "
        f"stratified by stroke subtype, excluding the {N['extraction.dev_reports']} development reports and all reports "
        f"of their patients. One trained annotator labelled them following a written guideline, blind to the extractor's "
        f"output. Agreement for phenotypes was Cohen's κ on the four-level scale (present, absent, uncertain, not "
        f"assessable); for location categories, κ for the presence of each category in a report. A phenotype or category "
        f"entered the primary model if κ ≥ {thr:.2f} with at least {mnp} annotator-positive reports (Tables S1 and S2). "
        f"The criterion was an eligibility rule for automated extraction, not a claim of interchangeability with expert "
        f"annotation, and no inter-rater agreement was measured.\n",
        f"从分析总体中随机抽取 {N['extraction.val_reports']} 份报告，每位患者一份，按卒中亚型分层，并排除 {N['extraction.dev_reports']} "
        f"份开发报告及其患者的全部报告。一名经过培训的标注者按书面指南、在不知道抽取结果的情况下进行标注。表型的一致性以四级量表（存在、"
        f"不存在、不确定、无法评估）上的 Cohen's κ 衡量；位置类别以每个类别是否出现在报告中的 κ 衡量。κ ≥ {thr:.2f} 且标注者阳性报告不少于 "
        f"{mnp} 份的表型或类别进入主模型（表 S1、表 S2）。该标准是自动抽取的准入规则，并不意味着可以替代专家标注；本研究未测量标注者间一致性。\n"))

    A(T("### S4. Independent reproduction\n", "## S4. 独立复现\n"))
    A(T("The primary result was recomputed by a script that imports none of the analysis code and uses different "
        "algorithms at each step: the imaging features were rebuilt with an as-of merge and cumulative maxima rather than "
        "a per-landmark loop; ranking used positional sorting; and bootstrap resampling used positional indices with a "
        "different random seed (Table S9).\n",
        "主要结果由一个不导入任何分析代码的脚本重新计算，并在每一步采用不同算法：影像特征用按时间向后匹配和累积最大值重建，而非逐个 landmark "
        "循环；排序按位置进行；bootstrap 重抽样使用位置索引和不同的随机种子（表 S9）。\n"))

    A(T("### S5. Data governance\n", "## S5. 数据管理\n"))
    A(T("MIMIC-IV and MIMIC-IV-Note were used under the PhysioNet credentialed data use agreement. Report text was "
        "processed only on the study computer; no report text or patient-level data was sent to an external service or "
        "shared, and none appears in this supplement.\n",
        "MIMIC-IV 和 MIMIC-IV-Note 按 PhysioNet 认证数据使用协议使用。报告文本仅在研究计算机上处理，未发送至任何外部服务或共享；"
        "本补充材料中不含任何报告文本或患者层面数据。\n"))

    # ------------------------------------------------------------------------- S6, protocol v1.3 C1
    C = json.load(open(HERE / "c1_second_extractor" / "c1_results.json"))
    fr1 = (HERE / "c1_second_extractor" / "EXTRACTOR_FREEZE_C1.md").read_text(encoding="utf-8")
    TAG1 = re.search(r"\| Model \| `([^`]+)`", fr1).group(1).replace("-q4_K_M", "")
    QUANT1 = re.search(r"Q\d_K_M", fr1).group(0)
    OLL1 = C["model"]["ollama"]
    run, ag = C["full_run"], C["agreement"]
    A(T("### S6. Repeated extraction with a larger model\n", "## S6. 更大模型重新抽取\n"))
    A(T("After the primary result was known, the extraction was repeated with a second model to examine whether the absence "
        "of an observed increment depended on the extraction model. The analysis was added to the protocol as version 1.3 on "
        "1 October 2026, before the second model was installed or had processed any report, together with its "
        "interpretation rule. It is reported as a post hoc analysis and does not replace the primary result.\n",
        "在主要结果得到之后，我们用第二个模型重复抽取，以考察未观察到增量这一结果是否取决于抽取模型。该分析连同其判读规则于 2026 年 "
        "10 月 1 日作为 1.3 版写入研究方案，当时第二个模型尚未安装，也未处理任何报告。它作为事后分析报告，不替代主要结果。\n"))
    A(T(f"The second model was chosen from a fixed, ordered list of candidates by technical criteria alone — valid output for "
        f"four fictional reports, and a processing time compatible with the full run — without reference to agreement with "
        f"any label. The first candidate met both: `{TAG1}` ({C['model']['params_b']} billion parameters, {QUANT1} "
        f"quantisation), run locally through Ollama {OLL1}. The prompt, rules, output schema, generation settings and "
        f"post-processing were those of the fixed extractor; the model's reasoning output was switched off, and nothing else "
        f"was changed. The second model was not developed or tuned on any report.\n",
        f"第二个模型从一份事先排定顺序的候选清单中选出，只依据技术标准——对 4 份虚构报告返回有效输出，且处理速度能够完成全量运行——"
        f"不参考与任何标注的一致程度。第一个候选即满足两项标准：`{TAG1}`（{C['model']['params_b'] * 10} 亿参数，{QUANT1} 量化），"
        f"通过 Ollama {OLL1} 在本地运行。提示词、规则、输出 schema、生成参数和后处理均与固定的抽取器相同；关闭了模型的推理过程输出，"
        f"除此之外未作任何改动。第二个模型没有在任何报告上开发或调试。\n"))
    A(T(f"It was validated on the same {N['extraction.val_reports']} reports against the same annotator, then applied to all "
        f"{run['reports']:,} reports, and the primary comparison was repeated, with the same landmark rule, models and "
        f"bootstrap, on two sets of findings, namely the {C['a']['n_features']} findings of the primary model and the findings that "
        f"met the reliability criterion under the new extraction — the same {C['a']['n_features']} plus cerebral oedema and "
        f"the occipital region. A result was to be read as consistent with the primary result if its confidence interval "
        f"included zero and its upper limit was below 5 percentage points; both were (Table S14).\n",
        f"它在同样的 {N['extraction.val_reports']} 份报告上对照同一名标注者进行验证，然后用于全部 {run['reports']:,} 份报告；随后沿用"
        f"相同的 landmark 规则、模型和 bootstrap，在两组影像发现上重复主要比较：主模型的 {C['a']['n_features']} 项发现，以及按新抽取"
        f"结果达到可靠性标准的发现——即这 {C['a']['n_features']} 项加上脑水肿和枕叶部位。事先规定：若置信区间包含零且上限低于 5 个"
        f"百分点，即视为与主要结果一致；两项结果均符合（表 S14）。\n"))
    _ph7 = ("intracranial_haemorrhage", "intraventricular_haemorrhage", "midline_shift_present", "cerebral_oedema",
            "acute_infarction", "mass_effect", "chronic_ischaemic_change")
    assert min(ag[k] for k in _ph7) == ag["acute_infarction"] and max(ag[k] for k in _ph7) == ag["midline_shift_present"]
    A(T(f"{run['quarantined']} of {run['reports']:,} reports ({f(N['c1.run.quarantined_pct'], 1)}%), "
        f"{C['validation']['failed']} of them in the validation set, could not be processed: the model repeated its output "
        f"until the context was full, and because decoding was deterministic the failure recurred on every attempt. They "
        f"include the {run['frozen_quarantined']} reports that the fixed extractor could not process. As in the primary "
        f"analysis, they were treated as unavailable, never as negative. Over the {C['n_both']:,} reports processed by both "
        f"models, agreement between them (κ) ranged from {f(ag['acute_infarction'], 2)} for acute or subacute infarction to "
        f"{f(ag['midline_shift_present'], 2)} for midline shift.\n",
        f"{run['reports']:,} 份报告中有 {run['quarantined']} 份（{f(N['c1.run.quarantined_pct'], 1)}%）无法处理，其中 "
        f"{C['validation']['failed']} 份在验证集中：模型不断重复输出直至上下文写满，由于解码是确定性的，每次尝试都以同样的方式失败。"
        f"固定抽取器无法处理的 {run['frozen_quarantined']} 份报告也在其中。与主要分析相同，这些报告按不可得处理，从不当作阴性。在两个"
        f"模型都成功处理的 {C['n_both']:,} 份报告上，两者之间的一致性（κ）从急性或亚急性梗死的 {f(ag['acute_infarction'], 2)} 到"
        f"中线移位的 {f(ag['midline_shift_present'], 2)} 不等。\n"))

    # ------------------------------------------------------------------------------ Supplementary Tables
    A(T("## Supplementary Tables\n", "# 补充表\n"))

    A(T("### Table S1. Agreement for all annotated phenotypes (four-level scale)\n", "**表 S1. 全部标注表型的一致性（四级量表）**\n"))
    rows = []
    for k, en, cn in PH:
        pos = N[f"kappa.{k}.pos"]; kap = N[f"kappa.{k}"]
        if k not in CANDIDATE:
            dec = T(f"not a candidate; <{mnp} positives" if pos < mnp else "not a candidate", f"非候选；阳性 <{mnp}" if pos < mnp else "非候选")
        else:
            dec = T("primary model", "主模型") if (kap >= thr and pos >= mnp) else T("sensitivity analysis only", "仅敏感性分析")
        rows.append([T(en, cn), f(kap, 2), f(N[f"kappa.{k}.agree_pct"], 1), f(pos, 0), dec])
    A(table([T("Phenotype", "表型"), "κ", T("Agreement, %", "一致率，%"), T("Annotator-positive reports", "标注者阳性报告数"), T("Use", "用途")], rows) + "\n")
    A(T(f"{N['extraction.val_reports']} random reports. Candidates for the primary model were the seven phenotypes listed first.\n",
        f"{N['extraction.val_reports']} 份随机报告。主模型候选为前七项表型。\n"))

    A(T("### Table S2. Agreement for all location categories\n", "**表 S2. 全部位置类别的一致性**\n"))
    rows = []
    for r in lk.itertuples():
        kap = "—" if pd.isna(r.kappa) else f(r.kappa, 2)
        use = T("primary model", "主模型") if (not pd.isna(r.kappa) and r.kappa >= thr and r.annotator_pos >= mnp) else "—"
        rows.append([T(FIELD[r.field][0], FIELD[r.field][1]), T(r.category.replace("_", " "), CAT_CN[r.category]), kap,
                     f(r.annotator_pos, 0), f(r.extractor_pos, 0), use])
    A(table([T("Field", "字段"), T("Category", "类别"), "κ", T("Annotator-positive", "标注者阳性"), T("Extractor-positive", "抽取器阳性"), T("Use", "用途")], rows) + "\n")
    A(T("κ for the presence of each category in a report. — : not estimable (no positives on either side).\n",
        "κ 为每个类别是否出现在报告中的一致性。—：无法估计（双方均无阳性）。\n"))

    A(T("### Table S3. Risk sets, events and imaging availability by landmark\n", "**表 S3. 各 landmark 的风险集、事件与影像可得性**\n"))
    rows = []
    for h in sorted(age.index):
        h = int(h)
        rows.append([f"{h}", f(N[f"landmark.{h}.at_risk"], 0), f"{f(N[f'landmark.{h}.events'], 0)} ({f(N[f'landmark.{h}.event_rate_pct'], 1)})",
                     f(N[f"landmark.{h}.imaging_pct"], 1), f(age[h], 1), f(N[f"landmark.{h}.val_at_risk"], 0), f(N[f"landmark.{h}.val_events"], 0)])
    A(table([T("Landmark, h", "Landmark，小时"), T("At risk", "风险集"), T("Events (%)", "事件（%）"), T("Report available, %", "有合格报告，%"),
             T("Report age, median h", "报告时龄中位数，小时"), T("Validation at risk", "验证集风险集"), T("Validation events", "验证集事件")], rows) + "\n")
    A(T("Both cohorts unless stated. Report age is the time from storage of the report used to the landmark.\n",
        "除另有说明外为两个队列合计。报告时龄为所用报告存档至 landmark 的时间。\n"))

    A(T("### Table S4. Risk stratification at the top 5%, 10% and 20%, temporal validation\n", "**表 S4. 风险最高 5%、10% 和 20% 的风险分层表现（时间验证集）**\n"))
    rows = []
    for m, en, cn in MODELS:
        for k in (5, 10, 20):
            rows.append([T(f"{en} ({m})", f"{cn}（{m}）"), f"{k}%", f(N[f"model.{m}.top{k}.capture"], 1),
                         f(N[f"model.{m}.top{k}.ppv"], 1), f(N[f"model.{m}.top{k}.lift"], 2)])
    A(table([T("Model", "模型"), T("Flagged", "标记比例"), T("Event capture, %", "事件捕获率，%"), T("Positive predictive value, %", "阳性预测值，%"), T("Lift", "提升度")], rows) + "\n")
    A(T("Ranking within each landmark, flagged patients pooled across landmarks.\n", "在各 landmark 内排序，被标记患者跨 landmark 合并。\n"))

    A(T("### Table S5. Availability model and overlap of propensity scores by landmark, temporal validation\n",
        "**表 S5. 各 landmark 的可得性模型与倾向分数重叠（时间验证集）**\n"))
    rows = []
    for h, g in v.groupby("landmark_h"):
        im, no = g[g.img_available_locked == 1].ps, g[g.img_available_locked == 0].ps
        inside = ((im >= no.min()) & (im <= no.max())).mean()
        rows.append([f"{int(h)}", f(len(g), 0), f(100 * g.img_available_locked.mean(), 1), f"{f(im.min(), 3)}–{f(im.max(), 3)}",
                     f"{f(no.min(), 3)}–{f(no.max(), 3)}", f(100 * inside, 1)])
    A(table([T("Landmark, h", "Landmark，小时"), "n", T("Report available, %", "有合格报告，%"), T("Propensity, imaged", "倾向分数，有影像"),
             T("Propensity, not imaged", "倾向分数，无影像"), T("Imaged within non-imaged range, %", "有影像者落在无影像者范围内，%")], rows) + "\n")
    A(T(f"Availability model AUROC {f(N['ipw.ps_auroc_val'], 3)}. Stabilised weights truncated at the 1st and 99th percentiles "
        f"ranged {f(N['ipw.weight_min'], 2)} to {f(N['ipw.weight_max'], 2)}; effective sample size {f(N['ipw.ess_rounded'], 0)} of "
        f"{f(N['ipw.n_imaged_dev'], 0)} development landmarks ({f(N['ipw.ess_pct'], 1)}%). No landmark was excluded.\n",
        f"可得性模型 AUROC 为 {f(N['ipw.ps_auroc_val'], 3)}。在第 1 和第 99 百分位截断的稳定化权重范围为 {f(N['ipw.weight_min'], 2)} 至 "
        f"{f(N['ipw.weight_max'], 2)}；有效样本量为开发集 {f(N['ipw.n_imaged_dev'], 0)} 个 landmark 中的 {f(N['ipw.ess_rounded'], 0)} 个"
        f"（{f(N['ipw.ess_pct'], 1)}%）。没有 landmark 被排除。\n"))

    A(T("### Table S6. Stroke subtypes: patients, events, imaging and phenotype prevalence\n", "**表 S6. 卒中亚型：患者、事件、影像与表型患病率**\n"))
    rows = []
    for s, lab in SUB:
        for coh, en, cn in (("development", "Development", "开发集"), ("validation", "Validation", "验证集")):
            r = sd[(sd.subtype == s) & (sd.cohort == coh)].iloc[0]
            rows.append([T(lab, {"AIS": "AIS", "ICH": "ICH", "SAH": "SAH", "ICH and SAH": "ICH 合并 SAH"}[lab]), T(en, cn),
                         f(r.patients, 0), f(r.landmarks, 0), f"{f(r.events, 0)} ({f(100 * r.event_rate, 1)})", f(100 * r.imaging, 1)])
    A(table([T("Subtype", "亚型"), T("Cohort", "队列"), T("Patients", "患者"), T("Patient-landmarks", "患者-landmark"), T("Events (%)", "事件（%）"), T("Report available, %", "有合格报告，%")], rows) + "\n")
    feats = list(dict.fromkeys(prev.feature))
    FEAT_CN = {"Intracranial haemorrhage": "颅内出血", "Intraventricular haemorrhage": "脑室内出血", "Midline shift": "中线移位",
               "Compartment: intraparenchymal": "腔室：脑实质内", "Compartment: subarachnoid": "腔室：蛛网膜下腔",
               "Territory: MCA": "供血区：大脑中动脉", "Region: cerebellum": "区域：小脑"}
    rows = [[T(ft, FEAT_CN[ft])] + [f(100 * prev[(prev.feature == ft) & (prev.subtype == s)].prevalence.iloc[0], 1) for s, _ in SUB] for ft in feats]
    A("\n" + table([T("Phenotype, % positive among imaged landmarks", "表型（有影像 landmark 中的阳性率，%）"), "AIS", "ICH", "SAH", T("ICH and SAH", "ICH 合并 SAH")], rows) + "\n")
    A(T("Both cohorts. Prevalence among landmarks with an eligible report and a known (positive or negative) value.\n",
        "两个队列合计。患病率以有合格报告且取值已知（阳性或阴性）的 landmark 为分母。\n"))

    A(T("### Table S7. Primary comparison within stroke subtypes, temporal validation\n", "**表 S7. 各卒中亚型内部的主要比较（时间验证集）**\n"))
    rows = []
    for s in ("AIS", "ICH", "SAH"):
        rows.append([s, f(N[f"subtype.{s}.events"], 0), f"{f(N[f'subtype.{s}.auroc_M0A'], 3)} → {f(N[f'subtype.{s}.auroc_M1D'], 3)}",
                     f"{f(N[f'subtype.{s}.capture_M0A'], 1)} → {f(N[f'subtype.{s}.capture_M1D'], 1)}",
                     f"{f(N[f'subtype.{s}.delta'], 2, True)} ({f(N[f'subtype.{s}.lo'], 2)} {T('to', '至')} {f(N[f'subtype.{s}.hi'], 2)})"])
    A(table([T("Subtype", "亚型"), T("Events", "事件"), T("AUROC, baseline → augmented", "AUROC：基线 → 增强"),
             T("Top-10% capture, %", "风险最高 10% 捕获率，%"), T("Difference, pp (95% CI)", "差值，百分点（95% CI）")], rows) + "\n")
    A(T(f"Ranked within landmark and subtype. Subtype-by-imaging interaction, compared with the imaging-augmented model: "
        f"{f(N['subtype.interaction.delta'], 2, True)} ({f(N['subtype.interaction.lo'], 2)} to {f(N['subtype.interaction.hi'], 2)}). "
        f"Patients with both ICH and SAH had no validation events.\n",
        f"在 landmark 与亚型内部排序。亚型×影像交互模型相对影像增强模型：{f(N['subtype.interaction.delta'], 2, True)}"
        f"（{f(N['subtype.interaction.lo'], 2)} 至 {f(N['subtype.interaction.hi'], 2)}）。同时患 ICH 和 SAH 的患者在验证集中无事件。\n"))

    A(T("### Table S8. Net benefit, temporal validation\n", "**表 S8. 净获益（时间验证集）**\n"))
    rows = [[f"{int(round(100 * r.threshold))}%", f(100 * r.nb_M0A, 2), f(100 * r.nb_M1D, 2),
             f"{f(100 * r.delta, 2, True)} ({f(100 * r.lo, 2)} {T('to', '至')} {f(100 * r.hi, 2)})"] for r in dca.itertuples()]
    A(table([T("Threshold", "阈值"), T("Imaging-availability baseline", "影像可得性基线"), T("Imaging-augmented model", "影像增强模型"),
             T("Difference (95% CI)", "差值（95% CI）")], rows) + "\n")
    A(T("Net benefit per 100 patient-landmarks; patient-level bootstrap confidence intervals.\n", "净获益以每 100 个患者-landmark 表示；置信区间来自以患者为单位的 bootstrap。\n"))

    A(T("### Table S9. Independent reproduction of the primary result\n", "**表 S9. 主要结果的独立复现**\n"))
    rows = [[T("Imaging feature table, every cell", "影像特征表（逐格）"), T("identical" if rep_identical else "DIFFERENT", "完全一致" if rep_identical else "不一致"), "—"],
            [T("AUROC, imaging-availability baseline", "AUROC，影像可得性基线"), f(rep_auc[0], 3), f(N["model.M0+A.auroc"], 3)],
            [T("AUROC, imaging-augmented model", "AUROC，影像增强模型"), f(rep_auc[1], 3), f(N["model.M1-D.auroc"], 3)],
            [T("Difference in top-10% capture, pp", "风险最高 10% 捕获率差值，百分点"), f(rep_pt, 3, True), f(N["confirmatory.delta_capture"], 3, True)],
            [T("95% CI", "95% CI"), f"{f(rep_ci[0], 2)} {T('to', '至')} {f(rep_ci[1], 2)}", f"{f(N['confirmatory.delta_capture_lo'], 2)} {T('to', '至')} {f(N['confirmatory.delta_capture_hi'], 2)}"]]
    A(table([T("Quantity", "指标"), T(f"Independent code (seed {rep_seed})", f"独立代码（种子 {rep_seed}）"), T("Analysis", "分析代码")], rows) + "\n")

    A(T("### Table S10. Coding of patients with both ICH and SAH\n", "**表 S10. 同时患 ICH 和 SAH 患者的编码**\n"))
    rows = []
    for r in ich.itertuples():
        lab = T("As analysed: reference category" if r.Index == 0 else "Corrected: both ICH and SAH", "原分析：参照类别" if r.Index == 0 else "修正：同时编码为 ICH 和 SAH")
        rows.append([lab, f(r.auroc_M0A, 4), f(r.auroc_M1D, 4), f(r.delta, 3, True), f"{f(r.lo, 2)} {T('to', '至')} {f(r.hi, 2)}"])
    A(table([T("Coding", "编码方式"), T("AUROC, baseline", "AUROC，基线"), T("AUROC, augmented", "AUROC，增强"), T("Difference in top-10% capture, pp", "风险最高 10% 捕获率差值，百分点"), "95% CI"], rows) + "\n")
    A(T(f"{N['t1.all.sub_ICH+SAH_n']} patients. In the models, subtype indicators were ICH and SAH, so these patients fell in the reference category with AIS.\n",
        f"{N['t1.all.sub_ICH+SAH_n']} 例患者。模型中的亚型指示变量为 ICH 和 SAH，因此这些患者与 AIS 一起落入参照类别。\n"))

    A(T("### Table S11. Correction to baseline-model differences quoted in the protocol\n", "**表 S11. 对研究方案中所引基线模型差值的更正**\n"))
    rows = [[T("Full physiological minus dynamic-state baseline, AUROC", "完整生理基线减动态状态基线，AUROC"),
             f"+{old91[0]} (+{old91[1]} {T('to', '至')} +{old91[2]})",
             f"{f(N['ladder.full_vs_state.delta_auroc'], 3, True)} ({f(N['ladder.full_vs_state.delta_auroc_lo'], 3, True)} {T('to', '至')} {f(N['ladder.full_vs_state.delta_auroc_hi'], 3, True)})"],
            [T("Imaging-availability minus full physiological baseline, AUROC", "影像可得性基线减完整生理基线，AUROC"),
             f"+{oldA[0]} ({oldA[1]} {T('to', '至')} +{oldA[2]})",
             f"{f(N['ladder.A_vs_full.delta_auroc'], 3, True)} ({f(N['ladder.A_vs_full.delta_auroc_lo'], 3)} {T('to', '至')} {f(N['ladder.A_vs_full.delta_auroc_hi'], 3, True)})"],
            [T("Imaging-availability minus full physiological baseline, top-10% capture, pp", "影像可得性基线减完整生理基线，风险最高 10% 捕获率，百分点"),
             f"+{oldA[3]} ({oldA[4]} {T('to', '至')} +{oldA[5]})",
             f"{f(N['ladder.A_vs_full.delta_capture'], 2, True)} ({f(N['ladder.A_vs_full.delta_capture_lo'], 2)} {T('to', '至')} {f(N['ladder.A_vs_full.delta_capture_hi'], 2, True)})"]]
    A(table([T("Difference", "差值"), T("Quoted in protocol §9.1", "研究方案 §9.1 所引"), T("Observed (reported in the manuscript)", "观测值（正文所报告）")], rows) + "\n")
    A(T("The protocol quoted the mean of the bootstrap replicates in place of the observed difference. No conclusion changes.\n",
        "研究方案引用的是 bootstrap 重复的均值，而非观测差值。结论均未改变。\n"))

    A(T("### Table S12. Temporal-validation patients used and not used to estimate the state model\n",
        "**表 S12. 参与与未参与状态模型估计的时间验证集患者**\n"))
    au = pd.read_csv(HERE / "audit_unseen_patients.csv")
    lab_ = [T("All temporal-validation patients", "全部时间验证集患者"),
            T("Not used to estimate the state model", "未参与状态模型估计"),
            T("Used to estimate the state model", "参与状态模型估计")]
    rows = [[lab_[i], f"{r.patients:,}", f"{r.events:,}", f(r.auroc_M0state, 3),
             f"{f(r.delta, 2, True)} ({f(r.lo, 2)} {T('to', '至')} {f(r.hi, 2)})"] for i, r in enumerate(au.itertuples())]
    A(table([T("Patients", "患者"), "n", T("Events", "事件"), T("AUROC, state-only baseline", "AUROC，仅状态基线"),
             T("Difference in top-10% capture, pp (95% CI)", "风险最高 10% 捕获率差值，百分点（95% CI）")], rows) + "\n")
    A(T("The state model and its preprocessing were estimated in the earlier study on a random split of its 2008–2022 "
        "cohort. The fitted models are unchanged; they are evaluated separately in the two groups. If the state model were "
        "optimistic on patients it had seen, the state-only baseline would discriminate clearly better in that group.\n",
        "状态模型及其预处理是在前一项研究中，以 2008–2022 年队列的随机分割估计的。已拟合的模型不变，仅在两组患者中分别评估。"
        "若状态模型对其见过的患者过于乐观，仅状态基线在该组中的区分度应明显更高。\n"))

    A(T("### Table S13. Laboratory result times and the result-time rebuild\n", "**表 S13. 化验出结果时间及按出结果时间的重建**\n"))
    lt = pd.read_csv(HERE / "audit_lab_result_time.csv")
    LN = {"all eight labs": T("All eight", "全部 8 项"), "bun": T("Urea nitrogen", "尿素氮"), "creatinine": T("Creatinine", "肌酐"),
          "glucose": T("Glucose", "血糖"), "sodium": T("Sodium", "钠"), "potassium": T("Potassium", "钾"),
          "hemoglobin": T("Haemoglobin", "血红蛋白"), "platelet": T("Platelets", "血小板"), "wbc": T("White cells", "白细胞")}
    rows = [[LN[r.lab], f"{r.values_used:,}", f(r.resulted_after_landmark_pct, 1), f(r.median_delay_after_landmark_h_if_late, 2),
             f(r.p90_delay_after_landmark_h_if_late, 2)] for r in lt.itertuples()]
    A(table([T("Laboratory value", "化验"), T("Values used", "使用的数值"), T("Resulted after the landmark, %", "晚于 landmark 出结果，%"),
             T("Delay if late, median, h", "迟到者延迟中位数，小时"), T("Delay if late, 90th percentile, h", "迟到者延迟第 90 百分位，小时")], rows) + "\n")
    ls = pd.read_csv(HERE / "audit_lab_result_time_sensitivity.csv")
    lab_ = [T("As analysed: specimen time", "原分析：采样时间"), T("Rebuilt: result time", "重建：出结果时间")]
    rows = [[lab_[i], f(r.auroc_M0A, 3), f(r.auroc_M1D, 3), f(r.capture_M0A, 1), f(r.capture_M1D, 1),
             f"{f(r.delta_pp, 2, True)} ({f(r.lo, 2)} {T('to', '至')} {f(r.hi, 2)})"] for i, r in enumerate(ls.itertuples())]
    A(table([T("Laboratory timing", "化验计时"), T("AUROC, baseline", "AUROC，基线"), T("AUROC, augmented", "AUROC，增强"),
             T("Capture, baseline, %", "捕获率，基线，%"), T("Capture, augmented, %", "捕获率，增强，%"),
             T("Difference, pp (95% CI)", "差值，百分点（95% CI）")], rows) + "\n")
    A(T("Values used: the last value of each laboratory variable in each window 0–7 of the analysis patients, assigned by "
        "specimen time as in the earlier study. In the rebuild, values were assigned to the window of their result; the "
        "earlier study's range checks, forward fill, training medians and scaling, and the fixed state model, were applied "
        "unchanged, and the laboratory predictors and filtered state recomputed. Outcome, landmarks, imaging features, "
        "models and bootstrap were those of the primary analysis. The first row, run through the same code, reproduces the "
        "primary result.\n",
        "使用的数值：分析患者第 0–7 个窗口中每项化验的最后一个值，沿用前一项研究的做法按采样时间归入窗口。重建时，化验值归入其出结果"
        "时间所在的窗口；前一项研究的范围检查、向前填充、训练集中位数和标准化，以及固定的状态模型，均原样沿用，并重新计算化验预测因子"
        "和实时推断状态。结局、landmark、影像特征、模型和 bootstrap 均与主要分析相同。第一行用同一段代码运行，复现了主要结果。\n"))

    A(T("### Table S14. Repeated extraction with a larger model\n", "**表 S14. 更大模型重新抽取**\n"))
    A(T(f"**A. Agreement with the annotator ({N['extraction.val_reports']} random reports)**\n",
        f"**A. 与标注者的一致性（{N['extraction.val_reports']} 份随机报告）**\n"))
    K = C["validation"]
    R14 = [("midline_shift_present", "Midline shift", "中线移位"),
           ("intraventricular_haemorrhage", "Intraventricular haemorrhage", "脑室内出血"),
           ("intracranial_haemorrhage", "Intracranial haemorrhage", "颅内出血"),
           ("cerebral_oedema", "Cerebral oedema", "脑水肿"),
           ("acute_infarction", "Acute or subacute infarction", "急性或亚急性梗死"),
           ("chronic_ischaemic_change", "Chronic ischaemic change", "慢性缺血性改变"),
           ("mass_effect", "Mass effect", "占位效应"),
           ("list.intraparenchymal", "Compartment: intraparenchymal", "出血部位：脑实质内"),
           ("list.subarachnoid", "Compartment: subarachnoid", "出血部位：蛛网膜下腔"),
           ("list.MCA", "Territory: MCA", "供血区：大脑中动脉"),
           ("list.cerebellum", "Region: cerebellum", "部位：小脑"),
           ("list.occipital", "Region: occipital", "部位：枕叶")]
    rows = [[T(en, cn), f(N[f"kappa.{k}.pos"], 0), f(N[f"kappa.{k}"], 2), f(K[k], 2)] for k, en, cn in R14]
    A(table([T("Finding", "影像发现"), T("Annotator-positive reports", "标注阳性报告数"),
             T("κ, fixed extractor (7B)", "κ，固定抽取器（7B）"), T(f"κ, larger model ({C['model']['params_b']}B)", f"κ，更大模型（{C['model']['params_b']}B）")], rows) + "\n")
    A(T(f"**B. Primary comparison repeated (temporal validation, {N['cohort.val.landmarks']:,} patient-landmarks, "
        f"{N['cohort.val.events']:,} events)**\n",
        f"**B. 重复主要比较（时间验证集，{N['cohort.val.landmarks']:,} 个 patient-landmark，{N['cohort.val.events']:,} 个事件）**\n"))
    lab14 = {"selfcheck": T(f"Fixed extractor, {C['a']['n_features']} findings (primary result)", f"固定抽取器，{C['a']['n_features']} 项发现（主要结果）"),
             "a": T(f"Larger model, the same {C['a']['n_features']} findings", f"更大模型，相同的 {C['a']['n_features']} 项发现"),
             "b": T(f"Larger model, {C['b']['n_features']} findings meeting the criterion", f"更大模型，达到标准的 {C['b']['n_features']} 项发现")}
    rows = [[lab14[t], f"{C[t]['events_base']} / {C[t]['events_aug']}", f"{f(C[t]['auroc_base'], 3)} / {f(C[t]['auroc_aug'], 3)}",
             f"{f(C[t]['delta'], 2, True)} ({f(C[t]['lo'], 2)} {T('to', '至')} {f(C[t]['hi'], 2)})"] for t in ("selfcheck", "a", "b")]
    A(table([T("Extraction and findings", "抽取方式与影像发现"), T("Events captured, baseline / augmented", "捕获事件数，基线 / 加入影像"),
             T("AUROC, baseline / augmented", "AUROC，基线 / 加入影像"),
             T("Difference in top-10% capture, pp (95% CI)", "风险最高 10% 事件捕获率差值，个百分点（95% CI）")], rows) + "\n")
    A(T(f"Post hoc analysis, specified in protocol version 1.3 before the larger model processed any report (Supplementary "
        f"Methods S6). Panel A: four-level κ; annotator-positive counts are for all {N['extraction.val_reports']} reports, and "
        f"the larger model's κ is computed on the {K['scored']} it processed. Findings enter a model when κ ≥ "
        f"{N['extraction.kappa_threshold']:.2f} with at least {N['extraction.min_positives']} annotator-positive reports. "
        f"Panel B: the baseline does not use imaging content and is the same in every row; the {C['b']['n_features']} findings "
        f"are the {C['a']['n_features']} plus cerebral oedema and the occipital region. Each row was computed by the same code, "
        f"which reproduces the primary result in the first row.\n",
        f"事后分析，在更大模型处理任何报告之前写入研究方案 1.3 版（补充方法 S6）。A 部分：四级量表 κ；标注阳性报告数按全部 "
        f"{N['extraction.val_reports']} 份计，更大模型的 κ 按其成功处理的 {K['scored']} 份计算。影像发现在 κ ≥ "
        f"{N['extraction.kappa_threshold']:.2f} 且标注阳性报告不少于 {N['extraction.min_positives']} 份时进入模型。B 部分：基线不使用"
        f"影像内容，各行相同；{C['b']['n_features']} 项发现为 {C['a']['n_features']} 项加上脑水肿和枕叶部位。各行由同一段代码计算，"
        f"第一行精确复现主要结果。\n"))
    A(T("### Table S15. Correction of two implementation errors found after the results were known\n",
        "**表 S15. 结果已知后发现的两项实现错误的修正**\n"))
    D = json.load(open(HERE / "d1_before_after.json"))
    b, x, s3 = D["before"], D["excluded"], D["sens3_before"]
    ci = lambda d, lo, hi: f"{f(d, 2, True)} ({f(lo, 2)} {T('to', '至')} {f(hi, 2, True)})"
    sk = "sens.3.treatment_inclusive_outcome_state"
    rows = [
        [T("Development: patient-landmarks / events", "开发集：患者-landmark / 事件"),
         f"{b['cohort.dev.landmarks']:,} / {b['cohort.dev.events']:,}", f"{N['cohort.dev.landmarks']:,} / {N['cohort.dev.events']:,}"],
        [T("Temporal validation: patients / patient-landmarks / events", "时间验证集：患者 / 患者-landmark / 事件"),
         f"{b['cohort.val.patients']:,} / {b['cohort.val.landmarks']:,} / {b['cohort.val.events']:,}",
         f"{N['cohort.val.patients']:,} / {N['cohort.val.landmarks']:,} / {N['cohort.val.events']:,}"],
        [T("AUROC, baseline / augmented", "AUROC，基线 / 加入影像"),
         f"{f(b['model.M0+A.auroc'], 3)} / {f(b['model.M1-D.auroc'], 3)}", f"{f(N['model.M0+A.auroc'], 3)} / {f(N['model.M1-D.auroc'], 3)}"],
        [T("Primary comparison, difference in top-10% capture, pp (95% CI)", "主要比较，风险最高 10% 捕获率差值，百分点（95% CI）"),
         ci(b["confirmatory.delta_capture"], b["confirmatory.delta_capture_lo"], b["confirmatory.delta_capture_hi"]),
         ci(N["confirmatory.delta_capture"], N["confirmatory.delta_capture_lo"], N["confirmatory.delta_capture_hi"])],
        [T("Treatment-inclusive outcome state: validation events; difference, pp (95% CI)", "含治疗结局状态：验证集事件数；差值，百分点（95% CI）"),
         f"{s3['events']:,}; {ci(s3['delta'], s3['lo'], s3['hi'])}",
         f"{N[sk + '.events']:,}; {ci(N[sk + '.delta'], N[sk + '.lo'], N[sk + '.hi'])}"],
    ]
    A(table([T("Quantity", "项目"), T("Before correction", "修正前"), T("After correction", "修正后")], rows) + "\n")
    A(T(f"Landmarks at or after the recorded death: {x['landmarks_note_era']} in the analysis period ({x['landmarks_dev']} "
        f"development, {x['landmarks_val']} validation; {x['patients_note_era']} patients), carrying {x['events_among_excluded']} "
        f"events, all windows after death decoded as the adverse state. Windows after a death within 72 hours removed before "
        f"decoding: {x['windows_truncated']} in {x['stays_truncated']} stays. Before correction the treatment-inclusive analysis "
        f"used the neurological impairment–low support state; on the uncorrected landmarks the specified respiratory-support "
        f"state gives {x['sens3_events_val_target1_uncorrected']} validation events. Every conclusion is unchanged.\n",
        f"处于记录死亡时刻或之后的 landmark：分析时段内 {x['landmarks_note_era']} 个（开发集 {x['landmarks_dev']} 个、验证集 "
        f"{x['landmarks_val']} 个；{x['patients_note_era']} 例患者），其中含 {x['events_among_excluded']} 个事件，均为死亡之后的时间窗被解码为"
        f"不良状态。解码前去除的 72 小时内死亡者死亡之后的时间窗：{x['stays_truncated']} 个病程中共 {x['windows_truncated']} 个。修正前的含治疗"
        f"结局状态分析使用的是神经受损–低支持型；在未修正的 landmark 上，按方案规定的呼吸支持型计算，验证集事件数为 "
        f"{x['sens3_events_val_target1_uncorrected']} 个。所有结论均未改变。\n"))
    return "\n".join(L)


for lang, name in (("EN", "supplement_v1.md"), ("CN", "supplement_v1_CN.md")):
    (MS / name).write_text(build(lang), encoding="utf-8")
    print("written", name)
