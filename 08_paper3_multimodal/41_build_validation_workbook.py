"""
Paper 3, step 8c: the annotation workbook for the random validation set (v1.2).

One report per page, in the pre-randomised order of random200_index.csv. Each page
shows ONLY the order number, the note_id and the report text — no stroke subtype, no
times, nothing from the outcome, the states or the extractor (guideline v1.2 §1: the
annotator sees report text only; subtype comes from ICD codes, not from the report,
and could prime the reader).

Report text is in a verbatim block, untranslated. Scoring follows ontology v1.2: ten
assertion phenotypes with a change column, six herniation subtypes, four lists,
midline-shift millimetres, the adjudication flag and a rule note.

DUA: the output contains MIMIC-IV-Note report text. It stays on this machine. The
intermediate markdown is deleted after conversion. Nothing here prints report text.

Writes: annotation_validation/validation_workbook_v1.2_CN.docx
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import os
import re
import subprocess

import pandas as pd

P3 = _REPO_ROOT + "/08_paper3_multimodal"
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import project_paths  # noqa: E402  数据位置在项目根目录的 data_paths.cfg 里设置
NOTE = project_paths.MIMIC_NOTE
D = f"{P3}/annotation_validation"
PAGEBREAK = '\n```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```\n'

idx = pd.read_csv(f"{D}/random200_index.csv").sort_values("order")
want = set(idx.note_id)
parts = []
for ch in pd.read_csv(f"{NOTE}/radiology.csv.gz", usecols=["note_id", "text"], chunksize=100_000):
    parts.append(ch[ch.note_id.isin(want)])
txt = pd.concat(parts).set_index("note_id").text
assert set(txt.index) == want, "some sampled reports were not found"

ASSERT = [
    "1 急性脑梗死 acute_infarction",
    "2 大面积梗死 large_territorial_infarct",
    "3 颅内出血 intracranial_haemorrhage",
    "4 脑室内出血 intraventricular_haemorrhage",
    "5 脑水肿 cerebral_oedema",
    "6 中线移位 midline_shift_present",
    "7 脑积水 hydrocephalus",
    "8 占位效应 mass_effect",
    "9 慢性缺血性改变 chronic_ischaemic_change",
    "10 大血管闭塞 large_vessel_occlusion",
]
HERN = ["镰下疝 subfalcine(含 parafalcine)", "钩回疝 uncal", "小脑幕切迹疝 transtentorial",
        "小脑扁桃体疝 tonsillar", "经骨窗外疝 external", "未注明亚型 unspecified"]
LISTS = [
    ("梗死供血区 infarct_territory", "ACA / MCA / PCA / vertebrobasilar / watershed —— 仅报告明写供血区时"),
    ("梗死解剖部位 infarct_region", "frontal / parietal / temporal / occipital / insula / basal_ganglia / thalamus / deep_white_matter / brainstem / cerebellum —— 按报告原样"),
    ("出血腔隙 haemorrhage_compartment", "intraparenchymal / subarachnoid / subdural / epidural —— 脑室内由第 4 行推出,此处不重复"),
    ("脑实质出血部位 iph_location", "lobar / deep_basal_ganglia / thalamic / brainstem / cerebellar —— 仅脑实质出血"),
    ("中线移位毫米数 midline_shift_mm", "报告写明才填,cm 换算为 mm;不插补;前后不一致时两个都写并送裁定"),
    ("送裁定 adjudication_flag", "是 / 否;是则写明原因"),
    ("规则备注", "规则无法直接判定之处"),
]

out = ["---", 'title: "随机验证集标注工作本 —— 200 份(v1.2)"',
       'subtitle: "Paper 3 · 正式标注。机密 —— 受 PhysioNet DUA 约束的 MIMIC 数据。"', "---", "",
       "# 使用说明", "",
       "本工作本共 200 份报告,取自分析总体(属于本次住院、在 48 h landmark 前存档的头颅 CT/MRI 报告),"
       "每位患者 1 份,按卒中亚型分层抽取,已排除 50 份开发报告及其 47 位患者。报告顺序已随机化。", "",
       "**盲法。** 每份只显示序号、note_id 和报告原文。请只依据报告原文判断,不参考任何结局、状态或模型输出。", "",
       "**规则以 `protocol_v1.2/radiology_annotation_guideline_v1.2.md` 为准**,下方速查仅供提示。", "",
       "**报告原文保持英文原样,不作翻译。**", "",
       "**数据安全。** 本文件含 MIMIC-IV-Note 报告原文,受 PhysioNet 数据使用协议约束。仅限本机使用,"
       "不得通过邮件发送、上传,或粘贴到任何外部服务(包括任何 AI 工具)。", "",
       "**送裁定。** 规则无法解决的冲突(Findings 与 Impression 直接矛盾、同一报告数值不一致、边界病例),"
       "勾选\"送裁定\"并写明原因。全部 200 份第一遍完成后,再集中第二遍处理(指南 §5)。", "",
       "# 速查:全局规则", "",
       "- **G1 未提及 → 不存在**;检查本身无法显示的(非血管检查上的 LVO)→ 无法评估。",
       "- **G2 否定**:no / no evidence of / without / negative for / **no definite (evidence of)** → 不存在;同一句另有保留措辞时 → 不确定。",
       "- **G3 保留措辞 → 不确定**:possible、probable、likely、suggestive of、suspicious for、cannot exclude、may represent、equivocal、early / impending。consistent with、compatible with → 存在。",
       "- **G4 保留措辞 + 检查受限 → 不确定**;只有明说无法评价、且未暗示存在时才记无法评估。",
       "- **G5 否定只作用于被否定对象**:no large territorial infarct 不否定梗死本身。",
       "- **G6 现状与变化分开**:稳定、减少、增加,只要仍存在就记存在;**\"无新发出血\"不等于没有出血**。",
       "- **G7 不推断**:大面积梗死 ≠ 水肿;占位效应 ≠ 脑疝;脑叶 ≠ 供血区。",
       "- **G8 Findings 与 Impression**:具体阳性描述优先于笼统总结;无法解决的矛盾 → 不确定 + 送裁定。",
       "- **G9 可共存**:供血区、部位、腔隙、脑疝亚型均可多选;急性与慢性改变相互独立。", "",
       "# 速查:大血管闭塞(LVO)", "",
       "| 情形 | 判定 |", "|---|---|",
       "| 血管成像(CTA / MRA / DSA 或明确评价通畅性)直接显示闭塞 | 存在 |",
       "| 血管成像直接显示通畅 | 不存在 |",
       "| 非血管检查出现间接征象(如高密度血管征) | 不确定 —— 永不升级为存在 |",
       "| 非血管检查,无任何相关征象 | 无法评估 —— 不是不存在 |", ""]

for _, r in idx.iterrows():
    body = "\n".join(l.rstrip() for l in str(txt[r.note_id]).split("\n"))
    fence = "`" * max(3, max((len(m) for m in re.findall(r"`+", body)), default=0) + 1)
    out += [PAGEBREAK, f"## 报告 {int(r.order)} / 200", "",
            "| | |", "|---|---|", f"| 序号 | {int(r.order)} |", f"| note_id | `{r.note_id}` |", "",
            "### 报告原文(英文原样,不翻译)", "", fence, body, fence, "",
            "### 评分:四级判定与变化", "",
            "| 表型 | Present 存在 | Absent 不存在 | Uncertain 不确定 | Not assessable 无法评估 | 变化 new / increased / stable / decreased / resolved |",
            "|---|:--:|:--:|:--:|:--:|---|"]
    out += [f"| {a} |  |  |  |  |  |" for a in ASSERT]
    out += ["", "### 评分:脑疝亚型", "",
            "| 亚型 | Present 存在 | Absent 不存在 | Uncertain 不确定 | Not assessable 无法评估 |",
            "|---|:--:|:--:|:--:|:--:|"]
    out += [f"| {h} |  |  |  |  |" for h in HERN]
    out += ["", "### 评分:多选、数值与备注", "", "| 字段 | 可选项 / 说明 | 记录 |", "|---|---|---|"]
    out += [f"| {a} | {b} |  |" for a, b in LISTS]
    out.append("")

md = f"{D}/_validation_workbook.md"
open(md, "w", encoding="utf-8").write("\n".join(out))
docx = f"{D}/validation_workbook_v1.2_CN.docx"
try:
    subprocess.run(["pandoc", md, "-o", docx], check=True)
finally:
    os.remove(md)
print(f"{len(idx)} reports -> {docx}")
