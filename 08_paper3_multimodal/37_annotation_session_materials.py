"""
Paper 3, Phase 4 preparation: material for the session at which a clinician fixes
the annotation conventions.

The eight open items in radiology_annotation_guideline_v1.0.md cannot be settled in
the abstract. They need real reports: how findings are actually phrased here, how
often they are negated, how often they are hedged, and how often they are stated
only as a change from a previous study.

This script produces two things.

1. Aggregate counts, safe to discuss anywhere: per-feature candidate frequency and
   the frequency of the constructions that make the rules hard.
2. A working packet of report text, written to disk only, for the session itself.
   That packet is MIMIC data under the DUA. It stays on this machine, is not
   pasted into any external service, and is not committed anywhere public.

Writes to 08_paper3_multimodal/annotation_session/
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import os
import re
import pandas as pd

ROOT = _REPO_ROOT
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import project_paths  # noqa: E402  数据位置在项目根目录的 data_paths.cfg 里设置
BASE = project_paths.MIMIC_IV
MOD = project_paths.MIMIC_VMAC
SCR = ("/private/tmp/claude-501/-Users-pinglei-de-coach-claude-playground-mini-translator/"
       "e0533350-af3c-4a6e-9d51-2ad78c46ba33/scratchpad")
DEST = f"{ROOT}/08_paper3_multimodal/annotation_session"
os.makedirs(DEST, exist_ok=True)
SEED = 20260911

coh = pd.read_csv(f"{ROOT}/04_outputs/tables/patient_level_cohort.csv")
yr = pd.read_csv(f"{BASE}/hosp/patients.csv.gz", usecols=["subject_id", "anchor_year_group"])
coh = coh.merge(yr, on="subject_id").query("anchor_year_group != '2020 - 2022'")
sub = dict(zip(coh.subject_id, coh.stroke_subtype))
A = set(pd.read_csv(f"{SCR}/tierA_notes.csv").note_id)

rows = []
for ch in pd.read_csv(f"{MOD}/note_unzip/note/radiology.csv.gz",
                      usecols=["note_id", "subject_id", "charttime", "storetime", "text"],
                      chunksize=50_000):
    rows.append(ch[ch.note_id.isin(A) & ch.subject_id.isin(set(coh.subject_id))])
r = pd.concat(rows, ignore_index=True)
r["stroke_subtype"] = r.subject_id.map(sub)
r["low"] = r.text.str.lower()
print(f"tier-A head CT/MRI reports, note-era cohort: {len(r)} from {r.subject_id.nunique()} patients")
print(r.stroke_subtype.value_counts().to_string())

# ---- feature keyword patterns (candidate detection only, NOT the final extractor)
FEATURES = {
    "infarct":            r"infarct|ischemi[ac]|ischaemi[ac]",
    "infarct_territory":  r"\b(?:aca|mca|pca|anterior cerebral|middle cerebral|posterior cerebral|"
                          r"vertebrobasilar|basilar|watershed|borderzone)\b",
    "large_territorial":  r"large (?:territorial|vascular) |holohemispher|entire (mca|territory)",
    "hemorrhage":         r"h(?:a)?emorrhag|hematoma|haematoma|bleed",
    "hemorrhage_location":r"lobar|basal ganglia|thalam|pontine|brainstem|cerebell|subdural|"
                          r"subarachnoid|epidural",
    "ivh":                r"intraventricular (?:h(?:a)?emorrhag|blood|extension)|\bivh\b|"
                          r"blood (in|within) the ventric",
    "edema":              r"[oe]dema|swelling",
    "midline_shift":      r"midline shift|shift of (the )?midline|septum pellucidum .{0,20}shift",
    "hydrocephalus":      r"hydrocephalus|ventriculomegaly|ventricular (?:dilat|enlarge)",
    "mass_effect":        r"mass effect|effacement|compress",
    "herniation":         r"herniation|uncal|tonsillar|transtentorial|subfalcine",
    "chronic_change":     r"chronic (?:infarct|ischemic|ischaemic|microvascular)|old infarct|"
                          r"encephalomalacia|gliosis",
    "lvo":                r"occlusion|thrombus|clot|filling defect",
}

# ---- constructions that make the rules hard
CONTEXT = {
    "negation":    r"\bno (?:evidence of |acute |significant )?|without |negative for |"
                   r"absen(?:t|ce)|\bnot\b",
    "uncertainty": r"cannot (?:be )?exclude|cannot (?:be )?entirely exclude|possible|possibly|"
                   r"may represent|suspicious for|question of|equivocal|indeterminate|"
                   r"less likely|favor|suggest",
    "comparative": r"unchanged|stable|compared (?:to|with)|prior (?:study|exam)|previous (?:study|exam)|"
                   r"interval (?:increase|decrease|change|development)|new (?:since|compared)|"
                   r"increase[d]? in|decrease[d]? in|progress",
    "quantified":  r"\d+(?:\.\d+)?\s?(?:mm|cm)\b",
}

# Context must be scored in the SENTENCE carrying the mention, not anywhere in the
# report: "no" and "not" appear in virtually every radiology report, so a
# whole-report scan marks almost every mention as negated and tells you nothing.
SENT = re.compile(r"[^.;\n]+")
sentences = [(i, m.group(0)) for i, t in zip(r.index, r.low) for m in SENT.finditer(t)]
sdf = pd.DataFrame(sentences, columns=["ridx", "sent"])
print(f"\nsentences parsed: {len(sdf)}")

print("\n=== per-feature: reports mentioning it, and the context of those SENTENCES ===")
print(f"{'feature':22s} {'reports':>8} {'%rep':>6} | {'sentences':>9} "
      f"{'negated':>8} {'hedged':>7} {'compar.':>8} {'mm/cm':>7}")
summary = []
for name, pat in FEATURES.items():
    hitrep = r[r.low.str.contains(pat, regex=True, na=False)]
    hs = sdf[sdf.sent.str.contains(pat, regex=True, na=False)]
    row = {"feature": name, "reports": len(hitrep),
           "pct_reports": round(100 * len(hitrep) / len(r), 1), "sentences": len(hs)}
    for cname, cpat in CONTEXT.items():
        n = int(hs.sent.str.contains(cpat, regex=True, na=False).sum())
        row[cname + "_n"] = n
        row[cname + "_pct"] = round(100 * n / len(hs), 1) if len(hs) else None
    summary.append(row)
    print(f"{name:22s} {row['reports']:8d} {row['pct_reports']:6.1f} | {len(hs):9d} "
          f"{row['negation_pct']:7.1f}% {row['uncertainty_pct']:6.1f}% "
          f"{row['comparative_pct']:7.1f}% {row['quantified_pct']:6.1f}%")
pd.DataFrame(summary).to_csv(f"{DEST}/feature_candidate_counts.csv", index=False)

# ---- midline shift, the feature whose representation is still undecided
msent = sdf[sdf.sent.str.contains(FEATURES["midline_shift"], regex=True, na=False)]
mm = msent.sent.str.extract(r"(\d+(?:\.\d+)?)\s?(?:mm|cm)")
print(f"\n=== midline shift: {len(msent)} sentences in "
      f"{r.low.str.contains(FEATURES['midline_shift'], regex=True, na=False).sum()} reports ===")
print(f"  sentence carries a mm/cm value:  {int(mm[0].notna().sum())} "
      f"({100*mm[0].notna().mean():.1f}%)")
print(f"  sentence is negated:             {int(msent.sent.str.contains(CONTEXT['negation'], regex=True, na=False).sum())} "
      f"({100*msent.sent.str.contains(CONTEXT['negation'], regex=True, na=False).mean():.1f}%)")
print(f"  sentence is comparative only:    {int(msent.sent.str.contains(CONTEXT['comparative'], regex=True, na=False).sum())} "
      f"({100*msent.sent.str.contains(CONTEXT['comparative'], regex=True, na=False).mean():.1f}%)")

# ---- sampling for the session: 5 reports per subtype, plus 5 per low-frequency finding
rs = []
for st, g in r.groupby("stroke_subtype"):
    rs.append(g.sample(min(5, len(g)), random_state=SEED).assign(reason=f"random:{st}"))
for f in ["ivh", "edema", "midline_shift", "hydrocephalus", "mass_effect", "herniation"]:
    g = r[r.low.str.contains(FEATURES[f], regex=True, na=False)]
    if len(g):
        rs.append(g.sample(min(5, len(g)), random_state=SEED).assign(reason=f"candidate:{f}"))
pk = pd.concat(rs).drop_duplicates(subset="note_id")
pk[["note_id", "subject_id", "stroke_subtype", "charttime", "storetime", "reason", "text"]] \
    .to_csv(f"{DEST}/session_packet_REPORT_TEXT.csv", index=False)
pk[["note_id", "subject_id", "stroke_subtype", "reason"]] \
    .to_csv(f"{DEST}/session_packet_index.csv", index=False)

with open(f"{DEST}/README.md", "w") as fh:
    fh.write(
        "# Annotation-rules session packet\n\n"
        "`session_packet_REPORT_TEXT.csv` contains MIMIC-IV-Note report text and is "
        "**data under the PhysioNet DUA**. It stays on this machine. Do not paste it "
        "into any external service, LLM API, cloud document or email, and do not "
        "commit it to any repository.\n\n"
        f"{len(pk)} reports: 5 random per stroke subtype, plus 5 candidates for each "
        "low-frequency finding (IVH, oedema, midline shift, hydrocephalus, mass effect, "
        "herniation).\n\n"
        "`feature_candidate_counts.csv` and `session_packet_index.csv` carry no report "
        "text and are safe to circulate within the credentialed team.\n\n"
        "Purpose: settle the eight open items in "
        "`protocol_v1.0/radiology_annotation_guideline_v1.0.md` §2.\n")

print(f"\nsession packet: {len(pk)} reports -> {DEST}/")
