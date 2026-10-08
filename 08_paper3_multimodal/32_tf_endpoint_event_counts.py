"""
Paper 3, Phase 1: incident-transition event supply for the treatment-free endpoint.

Endpoint (per the protocol): among patients NOT currently in the adverse
treatment-free physiological state, the first transition INTO it within the next
12 h / 24 h. Landmarks whose horizon runs past the 72 h observation window are
dropped -- their event rate collapses artefactually.

Competing events are counted, not discarded: a patient can leave the risk set by
dying or by leaving the ICU, and ICU discharge outnumbers the event of interest
several-fold precisely because discharge means the patient improved.

Cohort: the 2008-2019 note-eligible era (MIMIC-IV-Note stops at 2019), with the
full 6368 shown alongside for reference.
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import pandas as pd

ROOT = _REPO_ROOT
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import project_paths  # noqa: E402  数据位置在项目根目录的 data_paths.cfg 里设置
BASE = project_paths.MIMIC_IV
DEST = f"{ROOT}/08_paper3_multimodal"
TARGET = 0   # tf_state 0 = neurological impairment-respiratory support analogue

a = pd.read_csv(f"{DEST}/tf_state_assignments_all.csv")
coh = pd.read_csv(f"{ROOT}/04_outputs/tables/patient_level_cohort.csv")
pat = pd.read_csv(f"{BASE}/hosp/patients.csv.gz", usecols=["subject_id", "anchor_year_group"])
coh = coh.merge(pat, on="subject_id", how="left")
coh["note_era"] = coh.anchor_year_group != "2020 - 2022"

S = {sid: dict(zip(g.window_idx, g.tf_state)) for sid, g in a.groupby("stay_id")}
last = {sid: max(w) for sid, w in S.items()}
mort = dict(zip(coh.stay_id, coh.icu_mortality))
sub = dict(zip(coh.stay_id, coh.stroke_subtype))
era = dict(zip(coh.stay_id, coh.note_era))

def table(stays, horizon, landmarks):
    rows = []
    for L in landmarks:
        atrisk = ev = cd = cx = 0
        for sid in stays:
            w = S[sid]
            if w.get(L) is None or w[L] == TARGET:
                continue
            atrisk += 1
            fut = [w[k] for k in range(L + 1, L + 1 + horizon) if k in w]
            if TARGET in fut:
                ev += 1
            elif last[sid] < L + horizon:
                cd += 1 if mort.get(sid) == 1 else 0
                cx += 0 if mort.get(sid) == 1 else 1
        rows.append((L, L * 6, atrisk, ev, 100 * ev / atrisk if atrisk else 0, cd, cx))
    return pd.DataFrame(rows, columns=["landmark", "hours", "at_risk", "events",
                                       "event_%", "cens_died", "cens_left_icu"])

for label, stays in [("full cohort", list(S)), ("note era 2008-2019", [s for s in S if era.get(s)])]:
    n = len(stays)
    w0 = sum(1 for s in stays if S[s].get(0) == TARGET)
    ever = sum(1 for s in stays if TARGET in S[s].values())
    print(f"\n{'='*72}\n{label}: {n} stays")
    print(f"  already in the adverse state at window 0: {w0} ({100*w0/n:.1f}%)")
    print(f"  ever in it during 72 h:                   {ever} ({100*ever/n:.1f}%)")
    for h, lm in [(2, range(0, 10)), (4, range(0, 8))]:
        t = table(stays, h, lm)
        pts = set()
        for sid in stays:
            w = S[sid]
            for L in lm:
                if w.get(L) is None or w[L] == TARGET:
                    continue
                if TARGET in [w[k] for k in range(L + 1, L + 1 + h) if k in w]:
                    pts.add(sid); break
        print(f"\n  --- horizon {h*6} h, landmarks {lm.start}-{lm.stop-1} ---")
        print(t.to_string(index=False, float_format=lambda x: f"{x:.1f}"))
        print(f"  POOLED at_risk={t.at_risk.sum()} events={t.events.sum()} "
              f"({100*t.events.sum()/t.at_risk.sum():.1f}%) unique patients={len(pts)}")
        if label.startswith("note"):
            t.to_csv(f"{DEST}/tf_events_{h*6}h_noteera.csv", index=False)

print(f"\n{'='*72}\nnote era, 24 h horizon, by stroke subtype")
stays = [s for s in S if era.get(s)]
for st in sorted({sub[s] for s in stays}):
    ss = [s for s in stays if sub[s] == st]
    t = table(ss, 4, range(0, 8))
    print(f"  {st:>8}: patients {len(ss):5d}  at_risk {t.at_risk.sum():6d}  "
          f"events {t.events.sum():5d}  ({100*t.events.sum()/t.at_risk.sum():.1f}%)")
