"""
Paper 3: run the frozen extractor over the analysis population in segments.

The extractor itself is frozen and is NOT touched: this wrapper only decides which reports to
hand it next. Each segment takes the reports not yet done, writes a temporary chunk, and calls
extract_v12.py, which appends to the same master output. Stopping mid-segment loses nothing —
the extractor writes each record as it finishes and skips completed note_ids on the next run.

Analysis population (protocol v1.2 B4): head CT/MRI reports of the qualifying admission stored
by the 48 h landmark, for the note-era landmark cohort.

Usage
  python 44_run_extraction_segment.py --build-only          build the input list, extract nothing
  python 44_run_extraction_segment.py --reports 150         do the next 150 reports
  caffeinate -i python 44_run_extraction_segment.py --reports 150
  python 44_run_extraction_segment.py --retry-failed --reports 5   re-attempt quarantined reports
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import argparse
import json
import os
import re
import subprocess
import sys

import pandas as pd

ROOT = _REPO_ROOT
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import project_paths  # noqa: E402  数据位置在项目根目录的 data_paths.cfg 里设置
BASE = project_paths.MIMIC_IV
NOTE = project_paths.MIMIC_NOTE
P3 = f"{ROOT}/08_paper3_multimodal"
INPUT = f"{P3}/analysis_population_input.csv"
OUTPUT = f"{P3}/extractor/analysis_population_out.jsonl"
FAILED = f"{P3}/extractor/analysis_population_failed.csv"
TIER_A = re.compile(r"^(CT HEAD|PORTABLE HEAD CT|MR HEAD|STROKE PROTOCOL \(BRAIN)", re.I)


def build_input():
    if not os.path.isdir(NOTE):
        sys.exit(f"The report text is not available at {NOTE} — see data_paths.cfg.")
    coh = pd.read_csv(f"{ROOT}/04_outputs/tables/patient_level_cohort.csv",
                      parse_dates=["intime", "admittime"])
    yr = pd.read_csv(f"{BASE}/hosp/patients.csv.gz", usecols=["subject_id", "anchor_year_group"])
    coh = coh.merge(yr, on="subject_id").query("anchor_year_group != '2020 - 2022'")
    lm = pd.read_csv(f"{P3}/landmark_dataset.csv", usecols=["stay_id", "note_era"])
    coh = coh[coh.stay_id.isin(set(lm[lm.note_era].stay_id))]

    det = pd.read_csv(f"{NOTE}/radiology_detail.csv.gz", usecols=["note_id", "field_name", "field_value"])
    ex = det[det.field_name == "exam_name"]
    tier_a = set(ex[ex.field_value.astype(str).str.match(TIER_A)].note_id)

    keep = []
    for ch in pd.read_csv(f"{NOTE}/radiology.csv.gz",
                          usecols=["note_id", "subject_id", "hadm_id", "charttime", "storetime", "text"],
                          chunksize=50_000):
        keep.append(ch[ch.note_id.isin(tier_a) & ch.subject_id.isin(set(coh.subject_id))])
    rad = pd.concat(keep)
    for c in ("charttime", "storetime"):
        rad[c] = pd.to_datetime(rad[c])
    d = rad.merge(coh[["subject_id", "stay_id", "hadm_id", "intime", "admittime"]]
                  .rename(columns={"hadm_id": "stay_hadm"}), on="subject_id")
    belongs = (d.hadm_id == d.stay_hadm) | (d.hadm_id.isna() & (d.charttime >= d.admittime))
    by48 = (d.storetime - d.intime).dt.total_seconds() / 3600 <= 48
    d = d[belongs & by48].drop_duplicates("note_id")
    d[["note_id", "text"]].to_csv(INPUT, index=False)
    print(f"analysis population: {len(d)} reports from {d.stay_id.nunique()} stays -> {INPUT}")


def done_ids():
    if not os.path.exists(OUTPUT):
        return set()
    with open(OUTPUT, encoding="utf-8") as fh:
        return {json.loads(l)["note_id"] for l in fh if l.strip() and not json.loads(l)["error"]}


def harvest_failures():
    """Record failed note_ids before the extractor's resume rewrite deletes their lines.

    Two reports (13 Sep 2026) put qwen2.5:7b into an unbounded repetition inside the `region`
    array — '"frontal", "frontal", "frontal", ...'. The schema sets no maxItems and the request
    no num_predict, so generation runs to the 900 s timeout; temperature 0 and seed 0 make it
    perfectly reproducible, so both attempts and every later segment fail the same way. The
    extractor is frozen and is NOT changed. Instead a report that has failed twice is
    quarantined here and not handed to the extractor again; it is reported as a named
    extraction-failure category (imaging features missing for that report), never as a success.
    Use --retry-failed to hand them over once more.
    """
    if not os.path.exists(OUTPUT):
        return
    new = {}
    with open(OUTPUT, encoding="utf-8") as fh:
        for l in fh:
            if not l.strip():
                continue
            r = json.loads(l)
            if r["error"]:
                new[r["note_id"]] = r["error"]
    if not new:
        return
    prev = (pd.read_csv(FAILED) if os.path.exists(FAILED)
            else pd.DataFrame(columns=["note_id", "error", "segments_failed"]))
    prev = prev.set_index("note_id")
    for nid, err in new.items():
        n = int(prev.loc[nid, "segments_failed"]) + 1 if nid in prev.index else 1
        prev.loc[nid] = {"error": err, "segments_failed": n}
    prev.reset_index().to_csv(FAILED, index=False)
    print(f"quarantined {len(new)} failed report(s) -> {os.path.basename(FAILED)}")


def failed_ids(retry):
    if retry or not os.path.exists(FAILED):
        return set()
    return set(pd.read_csv(FAILED).note_id)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--reports", type=int, default=150)
    ap.add_argument("--retry-failed", action="store_true",
                    help="hand the quarantined reports to the extractor once more")
    a = ap.parse_args()
    if not os.path.exists(INPUT):
        build_input()
    if a.build_only:
        return
    if not os.path.isdir(NOTE):
        print("note: the report text is not available, but the input file already exists — continuing")
    rows = pd.read_csv(INPUT)
    harvest_failures()
    done = done_ids()
    skip = failed_ids(a.retry_failed)
    todo = rows[~rows.note_id.isin(done | skip)]
    print(f"progress: {len(done)}/{len(rows)} done, {len(todo)} remaining"
          + (f", {len(skip)} quarantined" if skip else ""))
    if todo.empty:
        print("nothing left — the analysis population is fully extracted")
        return
    chunk = todo.head(a.reports)
    tmp = f"{P3}/_segment_input.csv"
    chunk.to_csv(tmp, index=False)
    try:
        subprocess.run([sys.executable, "extract_v12.py", "--input", tmp, "--output", OUTPUT],
                       cwd=f"{P3}/extractor", check=False)
    finally:
        os.remove(tmp)
    harvest_failures()
    left = len(rows) - len(done_ids()) - len(failed_ids(False))
    print(f"\nsegment finished. {left} reports still to do "
          f"(~{left * 27.5 / 3600:.1f} h at the validation-set rate)")


if __name__ == "__main__":
    main()
