"""
Paper 3 — compare extractor output with reference labels.

Prints counts and label-level mismatches (note_id, field, reference, extractor) only.
It never reads or prints report text, so it is safe to run on real MIMIC output.

Reference sources
  --fictional              extractor/fictional_test_reports.json ("expected" blocks);
                           fields set to null there are deliberately not scored
  --labels CSV             columns note_id, phenotype, level — the manual annotation
                           format, e.g. annotation_session/draft_labels_no_text.csv

Usage
  python evaluate.py --fictional
  python evaluate.py --output out.jsonl --labels labels.csv [--show-mismatches]
"""
import argparse
import csv
import json
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

# manual-annotation phenotype name -> extractor field
LABEL_MAP = {"midline_shift": "midline_shift_present"}
LIST_FIELDS = {"infarct_territory", "haemorrhage_location"}


def load_output(path):
    recs, errors = {}, 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            if r["error"]:
                errors += 1
            else:
                recs[str(r["note_id"])] = r["record"]
    return recs, errors


def reference_fictional():
    with open(os.path.join(HERE, "fictional_test_reports.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    return {r["id"]: {k: v for k, v in r["expected"].items() if v is not None}
            for r in d["reports"]}


def reference_labels(path):
    ref = defaultdict(dict)
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not r["level"]:
                continue
            f = LABEL_MAP.get(r["phenotype"], r["phenotype"])
            ref[str(r["note_id"])][f] = r["level"]
    return ref


def extractor_value(rec, field, ref_value):
    """Express the extractor's answer in the same form as the reference."""
    v = rec.get(field)
    if field in LIST_FIELDS and isinstance(ref_value, str):
        # manual annotation scored list fields on the assertion scale
        return "Present" if v else "Absent"
    return v


def same(field, ref, got):
    if isinstance(ref, list):
        return isinstance(got, list) and set(ref) == set(got)
    if field == "midline_shift_mm":
        return got is not None and abs(float(got) - float(ref)) <= 0.5
    return ref == got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fictional", action="store_true")
    ap.add_argument("--output")
    ap.add_argument("--labels")
    ap.add_argument("--show-mismatches", action="store_true")
    args = ap.parse_args()

    if args.fictional:
        out, ref, show = os.path.join(HERE, "fictional_out.jsonl"), reference_fictional(), True
    else:
        if not (args.output and args.labels):
            ap.error("give --fictional, or both --output and --labels")
        out, ref, show = args.output, reference_labels(args.labels), args.show_mismatches

    recs, n_err = load_output(out)
    common = sorted(set(ref) & set(recs))
    print(f"reference reports {len(ref)} | extracted {len(recs)} | failed extractions {n_err} | "
          f"scored {len(common)}")

    per_field = defaultdict(lambda: [0, 0])          # field -> [agree, n]
    confusion = defaultdict(Counter)                  # field -> Counter((ref, got))
    mismatches = []
    for nid in common:
        for field, rv in ref[nid].items():
            gv = extractor_value(recs[nid], field, rv)
            ok = same(field, rv, gv)
            per_field[field][1] += 1
            per_field[field][0] += ok
            if not isinstance(rv, list) and field != "midline_shift_mm":
                confusion[field][(rv, gv)] += 1
            if not ok:
                mismatches.append((nid, field, rv, gv))

    tot_a = sum(a for a, _ in per_field.values())
    tot_n = sum(n for _, n in per_field.values())
    print(f"overall field agreement: {tot_a}/{tot_n} ({100 * tot_a / tot_n:.1f}%)\n")
    print(f"{'field':38s} {'agree':>7} {'n':>4}  most common disagreements (reference→extractor)")
    for field in sorted(per_field):
        a, n = per_field[field]
        dis = [(k, c) for k, c in confusion[field].most_common() if k[0] != k[1]][:2]
        dis_s = "; ".join(f"{r}→{g} ×{c}" for (r, g), c in dis)
        print(f"{field:38s} {a:>4}/{n:<3}      {dis_s}")

    if show and mismatches:
        print("\nmismatches (labels only):")
        for nid, field, rv, gv in mismatches:
            print(f"  {nid:>12}  {field:36s} ref={rv!s:18} got={gv!s}")


if __name__ == "__main__":
    main()
