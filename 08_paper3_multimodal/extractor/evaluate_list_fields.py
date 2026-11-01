"""
Paper 3: per-category reliability of the list fields — frozen extractor against the primary
annotator on the 200 random validation reports.

Rebuilt 16 Sep 2026. The list-field κ values in PROJECT_LOG.md (12 Sep) decided four of the seven
frozen primary features (MCA 0.78, cerebellum 0.66, intraparenchymal 0.75, subarachnoid 0.73),
but the script that produced them was not kept. This one re-derives them from the source files so
that every number in the manuscript has a script behind it.

The annotator recorded list fields as free text. Each cell is split into terms and each term is
mapped to an ontology category by keyword (Chinese or English). The annotator's text may
paraphrase a report, so NOTHING from it is printed: only κ, counts, and the number of terms that
could not be mapped.

κ is Cohen's κ for the presence of each category in a report (binary, 200 reports).
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # repository root
import json
import re

import pandas as pd
from sklearn.metrics import cohen_kappa_score

HERE = _REPO_ROOT + "/08_paper3_multimodal"
LABELS = f"{HERE}/annotation_validation/validation_labels_v1.2.csv"
OUTPUT = f"{HERE}/extractor/validation200_v12_out.jsonl"

MAP = {
    "infarct_territory": {
        "ACA": ["ACA", "大脑前动脉", "前动脉"], "MCA": ["MCA", "大脑中动脉", "中动脉"],
        "PCA": ["PCA", "大脑后动脉", "后动脉"],
        "vertebrobasilar": ["vertebrobasilar", "椎基底", "基底动脉", "椎动脉"],
        "watershed": ["watershed", "分水岭", "交界区", "边缘带"],
    },
    "infarct_region": {
        "frontal": ["frontal", "额叶", "额"], "parietal": ["parietal", "顶叶"],
        "temporal": ["temporal", "颞叶", "颞"], "occipital": ["occipital", "枕叶", "枕"],
        "insula": ["insula", "岛叶"], "basal_ganglia": ["basal ganglia", "basal_ganglia", "基底节"],
        "thalamus": ["thalam", "丘脑"], "brainstem": ["brainstem", "brain stem", "pons", "脑干", "脑桥", "延髓", "中脑"],
        "cerebellum": ["cerebell", "小脑"],
    },
    "haemorrhage_compartment": {
        "intraparenchymal": ["intraparenchymal", "IPH", "脑实质", "实质"],
        "subarachnoid": ["subarachnoid", "SAH", "蛛网膜下"],
        "subdural": ["subdural", "SDH", "硬膜下"], "epidural": ["epidural", "EDH", "硬膜外"],
    },
}
EXTRACTOR_FIELD = {"infarct_territory": "infarct_territory", "infarct_region": "infarct_region",
                   "haemorrhage_compartment": "haemorrhage_compartment"}
SPLIT = re.compile(r"[,，、;；/|\n]+|\s{2,}|\band\b|和|及")
NONE = re.compile(r"^(无|没有|none|n/?a|-|—|未见|不适用)$", re.I)


def categories(cell, field):
    found, unmapped = set(), 0
    for term in SPLIT.split(cell):
        term = term.strip()
        if not term or NONE.match(term):
            continue
        hit = [cat for cat, keys in MAP[field].items()
               if any(k.lower() in term.lower() for k in keys)]
        if hit:
            found.update(hit)
        else:
            unmapped += 1
    return found, unmapped


def main():
    lab = pd.read_csv(LABELS, keep_default_na=False)
    lab = lab[lab.kind == "field"].copy()
    lab["name"] = lab.field.str.extract(r"([a-z][a-z_]+)\s*$")[0]
    lab["note_id"] = lab.note_id.astype(str)
    rec = {}
    for line in open(OUTPUT, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            if not r["error"]:
                rec[str(r["note_id"])] = r["record"]
    notes = sorted(set(lab.note_id) & set(rec))
    print(f"reports scored {len(notes)}\n")
    rows = []
    for field in MAP:
        cells = lab[lab.name == field].set_index("note_id").value
        ann, unm, nonempty = {}, 0, 0
        for n in notes:
            c = cells.get(n, "")
            if c.strip():
                nonempty += 1
            ann[n], u = categories(c, field)
            unm += u
        ext = {n: set(rec[n][EXTRACTOR_FIELD[field]] or []) for n in notes}
        jac = [len(ann[n] & ext[n]) / len(ann[n] | ext[n]) for n in notes if ann[n] | ext[n]]
        print(f"{field}: non-empty annotator cells {nonempty}, unmapped terms {unm}, "
              f"mean Jaccard {sum(jac)/len(jac):.2f}")
        for cat in MAP[field]:
            a = [int(cat in ann[n]) for n in notes]
            b = [int(cat in ext[n]) for n in notes]
            k = cohen_kappa_score(a, b) if (sum(a) or sum(b)) and len(set(a + b)) > 1 else float("nan")
            rows.append({"field": field, "category": cat, "kappa": k,
                         "annotator_pos": sum(a), "extractor_pos": sum(b)})
            print(f"   {cat:18s} κ {k:>5.2f}   annotator+ {sum(a):3d}   extractor+ {sum(b):3d}")
        print()
    pd.DataFrame(rows).to_csv(f"{HERE}/extractor/list_field_kappa.csv", index=False)
    print("Saved: extractor/list_field_kappa.csv")


if __name__ == "__main__":
    main()
