"""
Paper 3, C1.5 — run the second extractor over the analysis population (6,994 reports).

The counterpart of 44_run_extraction_segment.py, with the same failure handling (C1.3): the
extractor makes two attempts at a report; a report that still fails is quarantined, recorded in
analysis_population_c1_failed.csv, and not handed over again. It is reported as an extraction
failure and never read as a negative finding. --retry-failed hands the quarantined reports over
once more.

It only decides which reports to hand to extract_c1.py next, in chunks, and can be stopped and
restarted at any time: finished reports are kept, and nothing is extracted twice.

Prints progress counts only. The chunk file holds report text; it is written inside the project
folder and removed after each chunk.

Usage
  caffeinate -i python run_c1_full.py --model qwen3.8:27b-q4_K_M
  python run_c1_full.py --model qwen3.8:27b-q4_K_M --retry-failed
"""
import argparse
import json
import os
import subprocess
import sys
import time

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
P3 = os.path.dirname(HERE)
INPUT = f"{P3}/analysis_population_input.csv"
OUTPUT = f"{HERE}/analysis_population_c1_out.jsonl"
FAILED = f"{HERE}/analysis_population_c1_failed.csv"
CHUNK = 100


def records():
    if not os.path.exists(OUTPUT):
        return []
    with open(OUTPUT, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def harvest_failures():
    """Record failed note_ids before the extractor's resume step deletes their lines."""
    new = {r["note_id"]: r["error"] for r in records() if r["error"]}
    if not new:
        return
    prev = (pd.read_csv(FAILED) if os.path.exists(FAILED)
            else pd.DataFrame(columns=["note_id", "error", "times_failed"])).set_index("note_id")
    for nid, err in new.items():
        n = int(prev.loc[nid, "times_failed"]) + 1 if nid in prev.index else 1
        prev.loc[nid] = {"error": err, "times_failed": n}
    prev.reset_index().to_csv(FAILED, index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--retry-failed", action="store_true")
    a = ap.parse_args()
    rows = pd.read_csv(INPUT)
    t0 = time.time()
    retried = False
    while True:
        harvest_failures()
        done = {r["note_id"] for r in records() if not r["error"]}
        skip = set() if (a.retry_failed and not retried) or not os.path.exists(FAILED) \
            else set(pd.read_csv(FAILED).note_id)
        todo = rows[~rows.note_id.isin(done | skip)]
        print(f"[{time.strftime('%m-%d %H:%M')}] done {len(done)}/{len(rows)} | quarantined "
              f"{len(skip)} | remaining {len(todo)} | elapsed {(time.time() - t0) / 3600:.1f} h",
              flush=True)
        if todo.empty:
            break
        retried = True
        tmp = f"{HERE}/_c1_chunk_input.csv"
        todo.head(CHUNK).to_csv(tmp, index=False)
        try:
            subprocess.run([sys.executable, "extract_c1.py", "--model", a.model,
                            "--input", tmp, "--output", OUTPUT],
                           cwd=HERE, check=False, stdout=subprocess.DEVNULL)
        finally:
            os.remove(tmp)
    harvest_failures()
    print("COMPLETE: the analysis population is fully extracted (quarantined reports excepted)",
          flush=True)


if __name__ == "__main__":
    main()
