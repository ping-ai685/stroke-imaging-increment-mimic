"""Paper 3: build the extractor input for the 200 random validation reports.

Reads the sampled note_ids from random200_index.csv and pulls their text from
radiology.csv.gz on the project drive. Output is DUA data and stays on this machine;
nothing here prints report text.

Writes: annotation_validation/validation200_input.csv  (note_id, text)
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import pandas as pd

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import project_paths  # noqa: E402  数据位置在项目根目录的 data_paths.cfg 里设置
NOTE = project_paths.MIMIC_NOTE
D = _REPO_ROOT + "/08_paper3_multimodal/annotation_validation"

idx = pd.read_csv(f"{D}/random200_index.csv").sort_values("order")
want = set(idx.note_id)
parts = [ch[ch.note_id.isin(want)] for ch in
         pd.read_csv(f"{NOTE}/radiology.csv.gz", usecols=["note_id", "text"], chunksize=100_000)]
t = pd.concat(parts)
assert set(t.note_id) == want, f"missing {len(want - set(t.note_id))} reports"
out = idx[["note_id"]].merge(t, on="note_id")          # keep the randomised order
out.to_csv(f"{D}/validation200_input.csv", index=False)
print(f"{len(out)} reports written to validation200_input.csv (DUA data, stays local)")
