"""
Build the Word workbook for the annotation-rules session.

One report per page: metadata header, the report text exactly as written, and a
13-row scoring table so the clinician can mark decisions while reading rather than
afterwards. The point of the session is to discover the conventions, so the table
carries a "rule note" column — what was ambiguous and how it should be handled is
more valuable than the label itself.

Usage:  python 38_build_annotation_workbook.py [en|cn]

  en  annotation_workbook_v1.1.docx
  cn  annotation_workbook_v1.1_CN.docx

Both scaffolds are aligned with protocol v1.1 and correspond item for item: the
rules v1.1 already fixed are listed for reference, the open items are guideline
v1.1 §8, and the assertion columns use the v1.1 scale (Present / Absent /
Uncertain / Not assessable). The first English workbook, v1.0, was built before
v1.1, was never circulated, and has been withdrawn; it is no longer generated.

In BOTH versions the report text stays in English, exactly as written. It is never
translated: the extractor runs on the English text, the rules must be fixed on the
original wording, and translation would erase the very distinctions the session
exists to settle ("cannot exclude" versus "possible").

Report text is placed in a verbatim (fenced code) block, shown in a monospace
font. As ordinary markdown it was reinterpreted: runs of spaces used for column
alignment collapsed and numbered lines became lists. An earlier build altered 651
of 1,487 report lines that way — every word intact, but not the layout. A verbatim
block reproduces the text exactly, including the underscore runs that MIMIC uses
as de-identification masks.

DUA: the output contains MIMIC-IV-Note report text. It stays on this machine.
Do not email it, upload it, or paste it into any external service. The
intermediate markdown is deleted after conversion, so only one copy of the report
text exists per workbook besides the source CSV.
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import os
import re
import subprocess
import sys

import pandas as pd

LANG = sys.argv[1] if len(sys.argv) > 1 else "en"
assert LANG in ("en", "cn"), "language must be en or cn"

D = _REPO_ROOT + "/08_paper3_multimodal/annotation_session"
PAGEBREAK = '\n```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```\n'

d = pd.read_csv(f"{D}/session_packet_REPORT_TEXT.csv")
d = d.sort_values(["reason", "note_id"]).reset_index(drop=True)

if LANG == "en":
    FEATURES = [
        "1 acute infarction (acute_infarction)",
        "2 infarct territory (infarct_territory; multi-label, list in rule note)",
        "3 large territorial infarct (large_territorial_infarct)",
        "4 intracranial haemorrhage (intracranial_haemorrhage)",
        "5 haemorrhage location (haemorrhage_location; multi-label, list in rule note)",
        "6 intraventricular haemorrhage (intraventricular_haemorrhage)",
        "7 cerebral oedema (cerebral_oedema)",
        "8 midline shift (midline_shift_present; mm in rule note if stated)",
        "9 hydrocephalus (hydrocephalus)",
        "10 mass effect (mass_effect)",
        "11 herniation (herniation)",
        "12 chronic ischaemic change (chronic_ischaemic_change)",
        "13 large-vessel occlusion (large_vessel_occlusion; Not assessable by default on non-vascular studies)",
    ]
    FIND = {"ivh": "intraventricular haemorrhage", "edema": "oedema",
            "midline_shift": "midline shift", "hydrocephalus": "hydrocephalus",
            "mass_effect": "mass effect", "herniation": "herniation"}
    out = ["---", 'title: "Radiology annotation — rules session workbook (v1.1)"',
           'subtitle: "Paper 3, Phase 4 preparation. CONFIDENTIAL — MIMIC data under the PhysioNet DUA."',
           "---", "",
           "# How to use this workbook", "",
           "Fifty reports: five random per stroke subtype, and five candidates for each of "
           "six findings (intraventricular haemorrhage, oedema, midline shift, hydrocephalus, "
           "mass effect, herniation).", "",
           "**The rules matter more than the labels.** For each report, mark your call — and, "
           "more importantly, use the last column for any case where the answer was not obvious "
           "and the convention that should settle it. Those notes become "
           "`protocol_v1.1/radiology_annotation_guideline_v1.1.md` §8.", "",
           "**The report text is verbatim — not translated, not edited.** The extractor runs on "
           "the original wording, so the rules must be fixed on it.", "",
           "**Data protection.** This file contains MIMIC-IV-Note report text under the PhysioNet "
           "data use agreement. Use it on this machine only. Do not email it, upload it, or paste "
           "it into any external service, including any AI tool. When writing up rules, record the "
           "rule and a generalised example — never copy report text.", "",
           "# Rules already fixed by protocol v1.1 (for reference — not for discussion)", "",
           "1. **One assertion scale.** Every phenotype takes exactly one of four values — "
           "**Present**: asserted; **Absent**: explicitly excluded (\"no evidence of\", \"without\", "
           "\"negative for\"); **Uncertain**: hedged (\"cannot exclude\", \"possible\", "
           "\"suspicious for\", \"equivocal\"); **Not assessable**: this examination cannot "
           "demonstrate it. Phenotype-specific wording exceptions sit on top of this scale; they "
           "do not replace it.",
           "2. **Negation is scoped.** \"No large territorial infarct\" excludes large territorial "
           "infarction, not infarction.",
           "3. **Not assessable is not Absent.** A non-contrast CT that does not mention LVO has "
           "not excluded it.",
           "4. **Midline shift is judged on presence.** Where the report gives a measurement, "
           "record the millimetres in the rule note. An unmeasured mention is never 0 mm (only "
           "22.1% of mentions in this corpus carry a number).",
           "5. **Comparisons record the current state and the direction of change.** \"IVH "
           "decreased\" is still Present; only \"resolved\" or \"no residual\" makes it Absent. "
           "Write the direction in the rule note.",
           "6. **Infarct territory and haemorrhage location are multi-label.** Do not force a "
           "single category; list them in the rule note.",
           "7. **Acute infarction and chronic ischaemic change are independent.** Both may be "
           "Present.",
           "8. **Findings versus impression.** A specific, localised positive description outranks "
           "a general summary — \"no acute intracranial process\" in the impression does not "
           "override a specific lesion described in the findings. A genuine contradiction that "
           "context cannot resolve is Uncertain and goes to adjudication.", "",
           "# What this session must settle (guideline v1.1 §8)", "",
           "1. Phenotype-specific wording and context exceptions on top of the assertion scale.",
           "2. An operational definition of \"large territorial infarct\".",
           "3. Midline shift measurement: continuous, or dichotomised — and at what threshold.",
           "4. Herniation subtypes: free text or a closed list.",
           "5. Which phrasings in this corpus count as Not assessable, for each phenotype.",
           "6. Two or three worked examples per phenotype with the agreed label — generalised, "
           "not copied from a report.",
           "7. The adjudication procedure for dual-read disagreements.",
           "8. The interface or spreadsheet template for the formal annotation.", ""]
    def title(i, n, reason):
        kind, _, what = str(reason).partition(":")
        label = (f"random · {what}" if kind == "random"
                 else f"candidate · {FIND.get(what, what)}" if kind == "candidate" else str(reason))
        return f"## Report {i+1} of {n} — {label}"
    META = ["note_id", "subject_id", "stroke subtype", "charttime (exam time)",
            "storetime (report filed)"]
    H_TEXT, H_SCORE = "### Report text (verbatim, as written)", "### Scoring"
    SCORE_HEAD = "| Phenotype | Present | Absent | Uncertain | Not assessable | Rule note |"
    SCORE_ALIGN = "|---|:--:|:--:|:--:|:--:|---|"
    OUT = "annotation_workbook_v1.1.docx"

else:
    FEATURES = [
        "1 急性脑梗死 (acute_infarction)",
        "2 梗死供血区 (infarct_territory;可多选,列于备注)",
        "3 大面积梗死 (large_territorial_infarct)",
        "4 颅内出血 (intracranial_haemorrhage)",
        "5 出血部位 (haemorrhage_location;可多选,列于备注)",
        "6 脑室内出血 (intraventricular_haemorrhage)",
        "7 脑水肿 (cerebral_oedema)",
        "8 中线移位 (midline_shift_present;如有数值,mm 记于备注)",
        "9 脑积水 (hydrocephalus)",
        "10 占位效应 (mass_effect)",
        "11 脑疝 (herniation)",
        "12 慢性缺血性改变 (chronic_ischaemic_change)",
        "13 大血管闭塞 (large_vessel_occlusion;非血管检查默认无法评估)",
    ]
    FIND = {"ivh": "脑室内出血", "edema": "脑水肿", "midline_shift": "中线移位",
            "hydrocephalus": "脑积水", "mass_effect": "占位效应", "herniation": "脑疝"}
    out = ["---", 'title: "放射报告标注 —— 规则发现会议工作本"',
           'subtitle: "Paper 3 · Phase 4 准备。机密 —— 受 PhysioNet DUA 约束的 MIMIC 数据。"',
           "---", "",
           "# 使用说明", "",
           "本工作本共 50 份报告:每个卒中亚型随机抽取 5 份;另有六个征象(脑室内出血、"
           "脑水肿、中线移位、脑积水、占位效应、脑疝)各 5 份候选报告。", "",
           "**规则比标签重要。** 每份报告请勾选你的判断;更重要的是,凡判断不显而易见之处,"
           "请在最后一栏写下哪里有歧义、应当按什么规则处理。这些规则备注将写入 "
           "`protocol_v1.1/radiology_annotation_guideline_v1.1.md` §8。", "",
           "**报告原文保持英文原样,不作翻译。** 自动抽取器处理的是英文原文,规则必须针对"
           "原始措辞制定;\"cannot exclude\" 与 \"possible\" 这类区别,一经翻译就会丢失。", "",
           "**数据安全。** 本文件含 MIMIC-IV-Note 报告原文,受 PhysioNet 数据使用协议约束。"
           "仅限本机使用,不得通过邮件发送、上传,或粘贴到任何外部服务(包括任何 AI 工具)。"
           "整理规则时只记录规则本身和概括性例句,不要照抄报告原文。", "",
           "# 已由方案 v1.1 确定的规则(作为参照,会上不再讨论)", "",
           "1. **统一判定尺度。** 每个表型只取以下四级之一 —— **Present(存在)**:明确描述存在;"
           "**Absent(不存在)**:明确排除,如 \"no evidence of\"、\"without\"、\"negative for\";"
           "**Uncertain(不确定)**:有保留的表述,如 \"cannot exclude\"、\"possible\"、"
           "\"suspicious for\"、\"equivocal\";**Not assessable(无法评估)**:该检查本身无法显示该征象。"
           "各表型的特殊措辞例外叠加在这四级之上,而不取代它。",
           "2. **否定只作用于被否定的对象。** \"no large territorial infarct\" 只否定大面积梗死,"
           "不否定梗死本身。",
           "3. **无法评估 ≠ 不存在。** 非增强 CT 未提及大血管闭塞,记\"无法评估\",不记\"不存在\"。",
           "4. **中线移位以\"是否存在\"为主要判定。** 报告给出数值时,在规则备注中记录毫米数;"
           "未给数值不得视为 0 mm(本语料仅 22.1% 的提及带有数值)。",
           "5. **比较性表述同时记录当前状态与变化方向。** \"IVH decreased\" 仍记\"存在\","
           "只有明确\"已消散 / 无残留\"才记\"不存在\"。变化方向写在规则备注中。",
           "6. **梗死供血区与出血部位可多选**,不强行归为单一类别,在规则备注中列出。",
           "7. **急性梗死与慢性缺血性改变是两个独立表型**,可同时为\"存在\"。",
           "8. **Findings 与 Impression 不一致时**,具体、定位明确的阳性描述优先于笼统总结"
           "(例如 impression 中一句 \"no acute intracranial process\" 不能覆盖 findings 中描述的"
           "具体病灶);确属矛盾且无法由语境判断的,记\"不确定\"并提交裁定。", "",
           "# 本次会议需要确定的事项(指南 v1.1 §8)", "",
           "1. 在统一尺度之上,各表型特有的词汇与语境例外。",
           "2. \"大面积梗死\"的操作性定义。",
           "3. 中线移位数值作为连续变量,还是按阈值二分;若按阈值,取多少。",
           "4. 脑疝亚型:自由文本还是封闭列表。",
           "5. 本语料中,哪些措辞对各表型应记为\"无法评估\"。",
           "6. 每个表型 2–3 个示范例句及其约定标签(用概括性写法,不照抄报告原文)。",
           "7. 双人标注出现分歧时的裁定程序。",
           "8. 正式标注使用的界面或表格模板。", ""]
    def title(i, n, reason):
        kind, _, what = str(reason).partition(":")
        label = (f"随机抽样 · {what}" if kind == "random"
                 else f"候选 · {FIND.get(what, what)}" if kind == "candidate" else str(reason))
        return f"## 报告 {i+1} / {n} —— {label}"
    META = ["note_id", "subject_id", "卒中亚型", "charttime(检查时间)", "storetime(报告存档时间)"]
    H_TEXT, H_SCORE = "### 报告原文(英文原样,不翻译)", "### 评分"
    SCORE_HEAD = ("| 表型 | Present 存在 | Absent 不存在 | Uncertain 不确定 | "
                  "Not assessable 无法评估 | 规则备注 |")
    SCORE_ALIGN = "|---|:--:|:--:|:--:|:--:|---|"
    OUT = "annotation_workbook_v1.1_CN.docx"

for i, r in d.iterrows():
    out.append(PAGEBREAK)
    out.append(title(i, len(d), r.reason))
    out.append("")
    out.append(f"| | |\n|---|---|\n| {META[0]} | `{r.note_id}` |\n"
               f"| {META[1]} | {r.subject_id} |\n| {META[2]} | {r.stroke_subtype} |\n"
               f"| {META[3]} | {r.charttime} |\n| {META[4]} | {r.storetime} |")
    out.append("")
    out.append(H_TEXT)
    out.append("")
    body = "\n".join(l.rstrip() for l in str(r.text).split("\n"))
    run = max((len(m) for m in re.findall(r"`+", body)), default=0)
    fence = "`" * max(3, run + 1)          # longer than any backtick run in the text
    out += [fence, body, fence, ""]
    out.append(H_SCORE)
    out.append("")
    out.append(SCORE_HEAD)
    out.append(SCORE_ALIGN)
    for f in FEATURES:
        out.append(f"| {f} |  |  |  |  |  |")
    out.append("")

md = f"{D}/_workbook_{LANG}.md"
with open(md, "w") as fh:
    fh.write("\n".join(out))
docx = f"{D}/{OUT}"
try:
    subprocess.run(["pandoc", md, "-o", docx], check=True)
finally:
    os.remove(md)          # never leave a second copy of the report text behind
print(f"{len(d)} reports -> {docx}")
