"""
Paper 3, C1.4 — secondary binary agreement (protocol v1.2 CLARIFICATION_LOG, 12 Sep 2026):
among reports where annotator and extractor both give a definitive label (Present or Absent),
Cohen's κ, sensitivity and specificity. Uncertain and Not assessable are treated as missing.
Never alters B9 eligibility.

Scores any extractor output file, so the frozen and the second extractor are scored by the same
code. Prints counts and statistics only; no report text is read.

Usage  python evaluate_binary.py <output.jsonl> [<output.jsonl> ...]
"""
import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "extractor"))
from evaluate_validation import PRIMARY, SECONDARY, ontology_name  # noqa: E402

P3 = Path(__file__).resolve().parents[1]
LABELS = P3 / "annotation_validation" / "validation_labels_v1.2.csv"


def annotator():
    lab = pd.read_csv(LABELS, keep_default_na=False)
    lab["note_id"] = lab.note_id.astype(str)
    ann = {}
    for _, r in lab[lab.kind == "assertion"].iterrows():
        name = ontology_name(r.field)
        if name == "midline_shift":
            name = "midline_shift_present"
        if name:
            ann.setdefault(r.note_id, {})[name] = r.level
    for nid, s in lab[lab.kind == "herniation"].groupby("note_id")["level"]:
        v = ("Present" if (s == "Present").any() else "Uncertain" if (s == "Uncertain").any()
             else "Not assessable" if (s == "Not assessable").any() else "Absent")
        ann.setdefault(str(nid), {})["herniation"] = v
    return ann


def score(path, ann):
    rec = {}
    for line in open(path, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            if not r["error"]:
                rec[str(r["note_id"])] = r["record"]
    common = sorted(set(ann) & set(rec))
    print(f"\n{path}\nscored {len(common)} reports")
    print(f"{'phenotype':30s} {'n':>4} {'κ(bin)':>7} {'sens':>6} {'spec':>6}  TP  FN  FP  TN")
    for ph in PRIMARY + SECONDARY:
        pairs = [(ann[n].get(ph), rec[n].get(ph)) for n in common]
        pairs = [(a, b) for a, b in pairs if a in ("Present", "Absent") and b in ("Present", "Absent")]
        if len(pairs) < 2 or len({a for a, _ in pairs} | {b for _, b in pairs}) < 2:
            print(f"{ph:30s} {len(pairs):>4}  not computable")
            continue
        a, b = zip(*pairs)
        tp = sum(x == "Present" and y == "Present" for x, y in pairs)
        fn = sum(x == "Present" and y == "Absent" for x, y in pairs)
        fp = sum(x == "Absent" and y == "Present" for x, y in pairs)
        tn = sum(x == "Absent" and y == "Absent" for x, y in pairs)
        k = cohen_kappa_score(a, b)
        se = tp / (tp + fn) if tp + fn else float("nan")
        sp = tn / (tn + fp) if tn + fp else float("nan")
        print(f"{ph:30s} {len(pairs):>4} {k:>7.2f} {se:>6.2f} {sp:>6.2f} {tp:>3} {fn:>3} {fp:>3} {tn:>3}")


if __name__ == "__main__":
    A = annotator()
    for p in sys.argv[1:]:
        score(p, A)
