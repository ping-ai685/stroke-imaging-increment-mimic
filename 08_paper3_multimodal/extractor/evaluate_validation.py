"""
Paper 3 — the confirmatory extraction check: frozen extractor against the annotator's labels
on the 200 random validation reports, and the B9 verdict.

B9 (protocol v1.2): a phenotype enters the primary M1 feature set only if Cohen's κ ≥ 0.60
against the primary annotator AND the random set holds at least 10 annotator-positive reports.
The extractor is never re-tuned on these data; this script only scores it.

Prints counts, κ and the verdict — never report text. The annotator's free-text cells are not
read here.

Usage
  python evaluate_validation.py --output validation200_v12_out.jsonl \
      --labels ../annotation_validation/validation_labels_v1.2.csv
"""
import argparse
import json
import re

import pandas as pd
from sklearn.metrics import cohen_kappa_score

LEVELS = ["Present", "Absent", "Uncertain", "Not assessable"]
PRIMARY = ["intracranial_haemorrhage", "acute_infarction", "cerebral_oedema", "mass_effect",
           "midline_shift_present", "chronic_ischaemic_change", "intraventricular_haemorrhage"]
SECONDARY = ["large_territorial_infarct", "hydrocephalus", "herniation", "large_vessel_occlusion"]


def ontology_name(field):
    """The workbook writes '急性脑梗死 acute_infarction'; take the trailing ASCII identifier."""
    m = re.search(r"([a-z][a-z_]+)\s*$", field.strip())
    return m.group(1) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--labels", required=True)
    args = ap.parse_args()

    recs, fails, versions = {}, 0, set()
    for line in open(args.output, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        versions.add(r["prompt_version"])
        if r["error"]:
            fails += 1
        else:
            recs[str(r["note_id"])] = r["record"]

    lab = pd.read_csv(args.labels, keep_default_na=False)
    lab["note_id"] = lab.note_id.astype(str)
    ann = {}
    for _, r in lab[lab.kind == "assertion"].iterrows():
        name = ontology_name(r.field)
        if name == "midline_shift":
            name = "midline_shift_present"
        if name:
            ann.setdefault(r.note_id, {})[name] = r.level
    hern = lab[lab.kind == "herniation"].groupby("note_id")["level"]
    for nid, s in hern:
        v = ("Present" if (s == "Present").any() else "Uncertain" if (s == "Uncertain").any()
             else "Not assessable" if (s == "Not assessable").any() else "Absent")
        ann.setdefault(str(nid), {})["herniation"] = v

    common = sorted(set(ann) & set(recs))
    print(f"prompt_version {sorted(versions)} | annotated {len(ann)} | extracted {len(recs)} | "
          f"failed {fails} | scored {len(common)}\n")
    print(f"{'phenotype':30s} {'κ':>6} {'agree':>7} {'pos':>5}  B9")
    verdict = {}
    for ph in PRIMARY + SECONDARY:
        a = [ann[n].get(ph) for n in common]
        b = [recs[n].get(ph) for n in common]
        pairs = [(x, y) for x, y in zip(a, b) if x in LEVELS and y in LEVELS]
        if not pairs:
            print(f"{ph:30s} {'—':>6} {'—':>7} {'—':>5}  not scored")
            continue
        x, y = zip(*pairs)
        k = cohen_kappa_score(x, y, labels=LEVELS)
        agree = sum(i == j for i, j in pairs) / len(pairs)
        pos = sum(i == "Present" for i in x)
        ok = (k >= 0.60) and (pos >= 10) and ph in PRIMARY
        verdict[ph] = ok
        why = "in primary M1" if ok else ("κ < 0.60" if pos >= 10 and ph in PRIMARY else
                                          "<10 positives" if ph in PRIMARY else "not a primary candidate")
        print(f"{ph:30s} {k:>6.2f} {100*agree:>6.1f}% {pos:>5}  {why}")
    print(f"\nprimary M1 phenotypes passing B9: {sum(verdict.values())} of {len(PRIMARY)}")
    fail = [p for p in PRIMARY if not verdict.get(p)]
    if fail:
        print("failing: " + ", ".join(fail) + "  → sensitivity analysis only, not re-tuned")
    print("\nList fields (territory, region, compartment, intraparenchymal site) are recorded as "
          "free text in the workbook and are scored separately; they are not part of this table.")


if __name__ == "__main__":
    main()
