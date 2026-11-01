"""
Paper 3: pull the study lead's labels out of the annotated validation workbook.

Reads the .docx locally and writes one row per note_id x field. Free-text cells (change
direction, list selections, millimetres, adjudication reason, rule note) are written to the
file but never printed: an annotator's note may quote report wording, so the output file is
treated as DUA data. Only counts reach the console.

Writes: annotation_validation/validation_labels_v1.2.csv
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

import pandas as pd

D = _REPO_ROOT + "/08_paper3_multimodal/annotation_validation"
SRC = sys.argv[1] if len(sys.argv) > 1 else f"{D}/validation_workbook_v1.2_CN_blind_annotated.docx"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
LEVELS = ["Present", "Absent", "Uncertain", "Not assessable"]

root = ET.fromstring(zipfile.ZipFile(SRC).read("word/document.xml"))
cell = lambda tc: "".join(t.text or "" for t in tc.iter(W + "t")).strip()

rows, note, n_meta, kinds = [], None, 0, []
for tb in root.iter(W + "tbl"):
    tr = [[cell(c) for c in r.findall(W + "tc")] for r in tb.findall(W + "tr")]
    if not tr:
        continue
    flat = " ".join(tr[0])
    if any(len(r) == 2 and r[0] == "note_id" for r in tr):
        note = next(r[1] for r in tr if len(r) == 2 and r[0] == "note_id").strip("`")
        n_meta += 1
        continue
    if "表型" in flat:
        kind = "assertion"
    elif "亚型" in flat:
        kind = "herniation"
    elif "字段" in flat:
        kind = "fields"
    else:
        continue
    kinds.append(kind)
    for r in tr[1:]:
        if not r or not r[0].strip():
            continue
        name = re.sub(r"^\d+\s*", "", r[0]).strip()
        if kind in ("assertion", "herniation"):
            marks = [lv for lv, v in zip(LEVELS, r[1:5]) if v.strip()]
            rows.append({"note_id": note, "kind": kind, "field": name,
                         "level": "|".join(marks), "n_marks": len(marks),
                         "value": r[5].strip() if kind == "assertion" and len(r) > 5 else ""})
        else:
            rows.append({"note_id": note, "kind": "field", "field": name,
                         "level": "", "n_marks": 0, "value": r[2].strip() if len(r) > 2 else ""})

d = pd.DataFrame(rows)
out = f"{D}/validation_labels_v1.2.csv"
d.to_csv(out, index=False)

idx = pd.read_csv(f"{D}/random200_index.csv")
print(f"reports with a note_id block: {n_meta} | scoring tables: {len(kinds)} "
      f"({kinds.count('assertion')} assertion, {kinds.count('herniation')} herniation, {kinds.count('fields')} field)")
print(f"note_ids matching the sample index: {d.note_id.isin(set(idx.note_id)).groupby(d.note_id).any().sum()}/200")
a = d[d.kind == "assertion"]
print(f"\nassertion rows: {len(a)} | marked: {(a.n_marks == 1).sum()} | unmarked: {(a.n_marks == 0).sum()} | multi-marked: {(a.n_marks > 1).sum()}")
print("\nlabels per phenotype (annotator):")
t = pd.crosstab(a.field, a.level).reindex(columns=[c for c in LEVELS if c in a.level.unique()], fill_value=0)
t["positives"] = t.get("Present", 0)
t["B9 ≥10 positives"] = t["positives"] >= 10
print(t.to_string())
h = d[d.kind == "herniation"]
print("\nherniation subtypes — Present counts:")
print(h[h.level == "Present"].field.value_counts().to_string() or "(none)")
f = d[d.kind == "field"]
print(f"\nfree-text fields filled: {(f.value != '').sum()} of {len(f)} "
      f"(written to the CSV, not printed — may quote report wording)")
print(f"\nwritten: {out}")
