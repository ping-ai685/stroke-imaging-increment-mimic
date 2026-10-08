"""
Paper 3 — compare extractor v1.2 output with manual labels.

Prints counts and label-level disagreements only; never reads or prints report text.

The development labels (annotation_session/draft_labels_no_text_v2.csv) were scored on the
13-row workbook that predates ontology v1.2, so three rows are compared only approximately:
  infarct_territory       workbook mixed territory and region -> Present if either v1.2 list
                          is non-empty
  haemorrhage_location    workbook mixed compartment and site -> Present if either v1.2 list
                          is non-empty
  herniation              workbook overall row -> v1.2 derived overall herniation
They are marked "≈" in the output. The random-set labels will be scored on the v1.2 fields
directly.

Usage
  python evaluate_v12.py --output dev50_v12_out.jsonl --labels ../annotation_session/draft_labels_no_text_v2.csv
"""
import argparse
import csv
import json
from collections import Counter, defaultdict

DIRECT = {"acute_infarction": "acute_infarction", "large_territorial_infarct": "large_territorial_infarct",
          "intracranial_haemorrhage": "intracranial_haemorrhage",
          "intraventricular_haemorrhage": "intraventricular_haemorrhage",
          "cerebral_oedema": "cerebral_oedema", "midline_shift": "midline_shift_present",
          "hydrocephalus": "hydrocephalus", "mass_effect": "mass_effect",
          "chronic_ischaemic_change": "chronic_ischaemic_change",
          "large_vessel_occlusion": "large_vessel_occlusion", "herniation": "herniation"}
APPROX = {"infarct_territory", "haemorrhage_location", "herniation"}


def value(rec, phenotype):
    if phenotype == "infarct_territory":
        return "Present" if (rec["infarct_territory"] or rec["infarct_region"]) else "Absent"
    if phenotype == "haemorrhage_location":
        return "Present" if (rec["haemorrhage_compartment"] or rec["iph_location"]) else "Absent"
    return rec[DIRECT[phenotype]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--labels", required=True)
    args = ap.parse_args()

    recs, fails, flags = {}, 0, Counter()
    versions = set()
    for line in open(args.output, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        versions.add(r["prompt_version"])
        if r["error"]:
            fails += 1
            continue
        recs[str(r["note_id"])] = r["record"]
        flags.update(f.split(":")[0] for f in r["flags"])
    ref = defaultdict(dict)
    for r in csv.DictReader(open(args.labels, encoding="utf-8")):
        if r["level"]:
            ref[str(r["note_id"])][r["phenotype"]] = r["level"]

    common = sorted(set(ref) & set(recs))
    print(f"prompt_version(s) {sorted(versions)} | reference {len(ref)} | extracted {len(recs)} | "
          f"failed {fails} | scored {len(common)}")
    agree, n, conf = Counter(), Counter(), defaultdict(Counter)
    for nid in common:
        for ph, rv in ref[nid].items():
            gv = value(recs[nid], ph)
            n[ph] += 1
            agree[ph] += (rv == gv)
            conf[ph][(rv, gv)] += 1
    ta, tn = sum(agree.values()), sum(n.values())
    print(f"overall field agreement: {ta}/{tn} ({100 * ta / tn:.1f}%)\n")
    print(f"{'phenotype':32s} {'agree':>7} {'n':>3}  most common disagreements (reference→extractor)")
    for ph in sorted(n):
        dis = [(k, c) for k, c in conf[ph].most_common() if k[0] != k[1]][:2]
        mark = "≈" if ph in APPROX else " "
        print(f"{mark}{ph:31s} {agree[ph]:>4}/{n[ph]:<3}  " + "; ".join(f"{r}→{g} ×{c}" for (r, g), c in dis))
    print(f"\npost-processing flags: {dict(flags)}")


if __name__ == "__main__":
    main()
