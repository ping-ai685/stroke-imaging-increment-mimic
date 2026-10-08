"""
Paper 3: turn draft v2 into v3 by placing verified citations.

Each [REF: ...] placeholder in v2 is replaced by {cite:key,...} markers pointing at entries of
manuscript/references/references.json (built from the registries by 54). Sentences whose wording
had to change after the cited papers were read are rewritten here, each replacement asserted to
match exactly once. A final pass numbers citations in order of first appearance and appends the
reference list from references.json, so no bibliographic text is typed by hand.
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import json
import re

M = _REPO_ROOT + "/08_paper3_multimodal/manuscript"
refs = {r["key"]: r for r in json.load(open(f"{M}/references/references.json", encoding="utf-8"))}
s = open(f"{M}/paper3_draft_v2.md", encoding="utf-8").read()

EDITS = [
    # header note
    ("<!-- DRAFT v2, 16 September 2026. Revised after the study lead's review of v1. Journal not chosen.",
     "<!-- DRAFT v3, 16 September 2026. v2 with verified references placed (script 55). Journal not chosen."),
    ("Every number comes from manuscript/numbers.json. [REF: ...] = citation still to be found and\n     web-verified (none inserted from memory).",
     "Every number comes from manuscript/numbers.json. References are placed from\n     manuscript/references/references.json, built from PubMed/Crossref/DataCite/arXiv (script 54)."),
    ("Not ready for submission until every [REF]/[CHECK] is cleared", "Not ready for submission until every [CHECK] is cleared"),
    # Introduction, paragraph 1: Hacke describes deterioration over days, not hours
    ("Respiratory failure, haematoma expansion, oedema and herniation develop over hours, and a patient who is stable at one assessment may need airway support at the next [REF: early neurological and respiratory deterioration after stroke in ICU].",
     "Haematoma expansion, malignant oedema with herniation, and respiratory failure requiring ventilation develop over hours to days, and a patient who is stable at one assessment may need airway support at the next {cite:davis2006,hacke1996,robba2019}."),
    # Introduction, paragraph 2: Ropper is about consciousness; only two report-based studies; Liu has no imaging
    ("It defines the lesion, and findings such as midline shift and intraventricular haemorrhage are established markers of poor outcome [REF: midline shift / IVH and outcome after ICH].",
     "It defines the lesion: lateral displacement of the brain tracks depressed consciousness {cite:ropper1986}, and intraventricular haemorrhage is a marker of severity and poor outcome after intracerebral haemorrhage {cite:hanley2009}."),
    ("Prediction models increasingly add imaging information, often extracted from radiology reports, to structured clinical data, and several report gains in discrimination [REF: radiology NLP added to stroke outcome prediction, MIMIC-III head CT]; [REF: report-derived features in MIMIC-IV respiratory failure after stroke]. Most, however, compare against baselines built from admission variables, predict from a single time point, and do not ensure that the imaging used was available at the moment of prediction [CHECK: confirm this characterisation against the verified references].",
     "Prediction models increasingly add imaging information, often extracted from radiology reports, to structured clinical data, and some report gains in discrimination {cite:alotaibi2025,sun2026}. These models have predicted from a single time point against baselines of admission data, and one drew on reports from the whole hospital stay rather than those available when a prediction would be made {cite:alotaibi2025}; a recent intensive care model of respiratory failure after ischaemic stroke could not include imaging at all {cite:liu2025}."),
    # Introduction, paragraph 3: own work
    ("[REF: Lei et al., dynamic clinical states after acute stroke, Neurocritical Care — under review] and showed that they replicate in an independent multicentre database [REF: Lei et al., eICU external validation, JAMIA Open — under review; preprint doi:10.64898/2026.09.07.26362407].",
     "[CHECK: Paper 1 (Neurocritical Care) is under review — cite as unpublished only if the target journal allows; otherwise rely on the preprint] and showed that they replicate across 176 hospitals in an independent multicentre database {cite:lei2026preprint}."),
    # Methods
    ("reported following TRIPOD+AI [REF: TRIPOD+AI statement, BMJ 2024].", "reported following TRIPOD+AI {cite:tripodai2024}."),
    ("Beth Israel Deaconess Medical Center, Boston [REF: MIMIC-IV, Sci Data 2023]; radiology reports come from MIMIC-IV-Note [REF: MIMIC-IV-Note, PhysioNet].",
     "Beth Israel Deaconess Medical Center, Boston {cite:johnson2023,mimiciv31,goldberger2000}; radiology reports come from MIMIC-IV-Note, version 2.2 {cite:mimicivnote22}."),
    ("as defined previously [REF: Lei et al., Neurocritical Care — under review].",
     "as defined previously {cite:lei2026preprint} [CHECK: add Paper 1 if citable]."),
    ("so that no report text left the study computer [REF: Qwen2.5 technical report].",
     "so that no report text left the study computer {cite:qwen2024}."),
    ("threshold probabilities of 1% to 30% [REF: Vickers decision curve analysis].",
     "threshold probabilities of 1% to 30% {cite:vickers2006}."),
    ("Analyses used Python 3.9 and scikit-learn [CHECK: versions].",
     "Analyses used Python 3.9.6 with scikit-learn 1.6.1, pandas 2.3.3, NumPy 2.0.2 and SciPy 1.13.1; extraction ran on Ollama 0.13.1."),
    # Discussion
    ("Midline shift and intraventricular haemorrhage were strongly associated with deterioration here, but a lesion that is about to cause deterioration may already be affecting the measurements from which the state is built.",
     "Midline shift and intraventricular haemorrhage were strongly associated with deterioration here, but brain displacement is itself associated with depressed consciousness {cite:ropper1986}, and a lesion that is about to cause deterioration may already be affecting the measurements from which the state is built."),
    ("Earlier studies reported gains from adding report-derived imaging features to stroke outcome models [REF: radiology NLP added to stroke prediction]; [REF: report features in MIMIC-IV respiratory failure]. Those gains were measured largely against admission-based baselines, and the first step of our redundancy analysis reproduces them.",
     "Earlier studies reported gains from adding report-derived imaging information to stroke outcome models, from an AUROC of 0.558 to 0.616 for in-hospital mortality and from 0.720 to 0.771 for early neurological deterioration {cite:alotaibi2025,sun2026}. Both were measured against baselines built from admission data, and the first step of our redundancy analysis reproduces that pattern."),
]
for a, b in EDITS:
    assert s.count(a) == 1, f"not found exactly once: {a[:70]}"
    s = s.replace(a, b)
assert "[REF:" not in s, re.findall(r"\[REF:[^\]]*\]", s)

order = []
for keys in re.findall(r"\{cite:([^}]+)\}", s):
    for k in keys.split(","):
        assert k in refs, k
        if k not in order:
            order.append(k)
num = {k: i + 1 for i, k in enumerate(order)}


def compress(ns):
    ns, out, i = sorted(ns), [], 0
    while i < len(ns):
        j = i
        while j + 1 < len(ns) and ns[j + 1] == ns[j] + 1:
            j += 1
        out.append(f"{ns[i]}" if j == i else f"{ns[i]},{ns[j]}" if j == i + 1 else f"{ns[i]}–{ns[j]}")
        i = j + 1
    return ",".join(out)


s = re.sub(r"\{cite:([^}]+)\}", lambda m: "[" + compress([num[k] for k in m.group(1).split(",")]) + "]", s)
unused = sorted(set(refs) - set(order))
reflist = "\n## References\n\n" + "\n".join(f"{num[k]}. {refs[k]['formatted']}" for k in order) + "\n"
s = s.replace("\n---\n\n## Tables", "\n---\n" + reflist + "\n---\n\n## Tables", 1)
open(f"{M}/paper3_draft_v3.md", "w", encoding="utf-8").write(s)
print(f"{len(order)} references cited, numbered by first appearance; unused in references.json: {unused}")
print("remaining [CHECK] markers:", len(re.findall(r"\[CHECK:", s)))
