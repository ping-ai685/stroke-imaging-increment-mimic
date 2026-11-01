"""
Paper 3 — local neuroimaging-report extractor, v1.2. FROZEN 12 September 2026.

Frozen version: prompt_version 0347237dd3f5 — see EXTRACTOR_FREEZE_v1.2.md. Do not edit this
file or rules_v1.2.md: their content is hashed into prompt_version, and a change would
invalidate the validation (protocol v1.2 B6, B9).

Implements ontology v1.2 and guideline v1.2 (frozen 11 Sep 2026). Runs qwen2.5:7b through
Ollama on project hardware; report text never leaves the machine (protocol v1.2 §8.4) — the
only network call is to localhost, asserted below. Supersedes extract.py (v0, v1.1 schema),
which is kept to reproduce the v0 development evaluation.

Changes from v0
- Output follows ontology v1.2, compacted so the model writes fewer tokens (output is the
  bottleneck at ~16 tok/s): herniation subtypes and change directions are LISTS of what the
  report mentions; anything not listed is Absent / not_stated by G1. Short keys are mapped
  back to ontology names; change fields become "<field>__change", which cannot collide with a
  phenotype name (v0's "_change" suffix collided with chronic_ischaemic_change).
- The prompt carries rules_v1.2.md — a condensation of the frozen guideline, with its
  generalised worked examples.
- Deterministic post-processing (part of the extractor, frozen with it):
    * Not-assessable guard, sentence-scoped: a non-LVO finding keeps "Not assessable" only if
      a sentence mentioning it also carries limitation wording; otherwise Absent (G1, G4).
    * LVO guard (§4.13): without any vessel-imaging wording, Present -> Uncertain and
      Absent -> Not assessable.
    * Change list cleaned: a change on an Absent finding is dropped unless it is "resolved".
    * Derived fields: overall herniation, intraventricular compartment, infratentorial site,
      multiple territories.
  Every guard application is recorded as a flag; nothing is changed silently.
- prompt_version hashes the template, the rules, the schema AND the post-processing source,
  so any change to a guard changes the version.

DUA guard: nothing in this module prints report text. Logs carry note_ids and counts.

Usage
  python extract_v12.py --fictional                         built-in FICTIONAL test set
  python extract_v12.py --input reports.csv --output out.jsonl   (CSV: note_id, text)
Resumable: successful note_ids are skipped; failed ones are retried.
"""
import argparse
import csv
import hashlib
import inspect
import json
import os
import re
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = "qwen2.5:7b"
OLLAMA = "http://localhost:11434/api/generate"
assert OLLAMA.startswith("http://localhost"), "report text may only go to a local model"
RULES_FILE = os.path.join(HERE, "rules_v1.2.md")

ASSERT = ["Present", "Absent", "Uncertain", "Not assessable"]
MAIN = ["infarct_acute", "infarct_large", "haem", "ivh", "oedema", "mls", "hydro",
        "mass_effect", "chronic_isch", "lvo"]
ONTO = {"infarct_acute": "acute_infarction", "infarct_large": "large_territorial_infarct",
        "haem": "intracranial_haemorrhage", "ivh": "intraventricular_haemorrhage",
        "oedema": "cerebral_oedema", "mls": "midline_shift_present", "hydro": "hydrocephalus",
        "mass_effect": "mass_effect", "chronic_isch": "chronic_ischaemic_change",
        "lvo": "large_vessel_occlusion"}
HERN = ["subfalcine", "uncal", "transtentorial", "tonsillar", "external", "unspecified"]
TERR = ["ACA", "MCA", "PCA", "vertebrobasilar", "watershed"]
REGION = ["frontal", "parietal", "temporal", "occipital", "insula", "basal_ganglia",
          "thalamus", "deep_white_matter", "brainstem", "cerebellum"]
COMP = ["intraparenchymal", "subarachnoid", "subdural", "epidural"]
IPH = ["lobar", "deep_basal_ganglia", "thalamic", "brainstem", "cerebellar"]
DIR = ["new", "increased", "stable", "decreased", "resolved"]


def enum_list(values):
    return {"type": "array", "items": {"type": "string", "enum": values}}


def build_schema():
    props = {k: {"type": "string", "enum": ASSERT} for k in MAIN}
    props["herniation"] = {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["subtype", "level"],
        "properties": {"subtype": {"type": "string", "enum": HERN},
                       "level": {"type": "string", "enum": ["Present", "Uncertain", "Not assessable"]}}}}
    props["territory"] = enum_list(TERR)
    props["region"] = enum_list(REGION)
    props["haem_compartment"] = enum_list(COMP)
    props["iph_site"] = enum_list(IPH)
    props["mls_mm"] = {"type": ["number", "null"]}
    props["changes"] = {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["field", "direction"],
        "properties": {"field": {"type": "string", "enum": MAIN},
                       "direction": {"type": "string", "enum": DIR}}}}
    return {"type": "object", "properties": props, "required": list(props),
            "additionalProperties": False}


SCHEMA = build_schema()

TEMPLATE = """You extract findings from ONE head CT or MRI radiology report into JSON.
Use only what the report states, and follow the rules exactly.

RULES_BLOCK

OUTPUT FIELDS
- infarct_acute, infarct_large, haem, ivh, oedema, mls, hydro, mass_effect, chronic_isch, lvo:
  exactly one of Present / Absent / Uncertain / Not assessable.
- herniation: a list of {subtype, level} for herniation subtypes the report mentions as present,
  uncertain or not assessable; [] if none.
- territory, region, haem_compartment, iph_site: lists; [] if none.
- mls_mm: millimetres only if the report states a number; otherwise null.
- changes: a list of {field, direction} only for explicit comparisons with a prior study; [] if none.

REPORT:
<<<
REPORT_TEXT
>>>"""

with open(RULES_FILE, encoding="utf-8") as _fh:
    RULES = _fh.read().strip()

# --- deterministic post-processing ------------------------------------------------------
KW = {"infarct_acute": r"infarct|ischemi|ischaemi", "infarct_large": r"infarct|territor",
      "haem": r"h(?:a)?emorrhag|hematoma|haematoma|bleed|blood", "ivh": r"ventric",
      "oedema": r"[oe]dema|swelling", "mls": r"midline|shift", "hydro": r"hydroceph|ventric",
      "mass_effect": r"mass effect|effac|compress",
      "chronic_isch": r"chronic|\bold\b|encephalomalacia|gliosis|white matter|small vessel|microvascular"}
HERN_KW = r"herniat|tonsil|uncal|subfalcine|transtentorial|foramen magnum"
LIMIT = (r"limited|not well (?:seen|evaluated|assessed|visuali[sz]ed)|cannot be "
         r"(?:evaluated|assessed)|motion|artifact|artefact|suboptimal|non-?diagnostic|obscured|degraded")
VESSEL_IMAGING = r"\bcta\b|\bmra\b|angiogra|\bdsa\b|ct angio|mr angio|flow void|patent|patency"
# Wording that must appear in the report before a list item may be recorded (mention guard).
TERM = {"ACA": r"\baca\b|anterior cerebral", "MCA": r"\bmca\b|middle cerebral",
        "PCA": r"\bpca\b|posterior cerebral", "vertebrobasilar": r"vertebro|basilar",
        "watershed": r"watershed|border ?zone", "frontal": "frontal", "parietal": "parietal",
        "temporal": "temporal", "occipital": "occipital", "insula": "insula",
        "basal_ganglia": r"basal ganglia|putamen|caudate|lentiform", "thalamus": "thalam",
        "deep_white_matter": r"white matter|corona radiata|centrum semiovale",
        "brainstem": r"brainstem|pons|pontine|midbrain|medulla", "cerebellum": r"cerebell",
        "lobar": r"lobar|\blobe\b|frontal|parietal|temporal|occipital", "deep_basal_ganglia": r"basal ganglia|putamen|caudate|lentiform|internal capsule",
        "thalamic": "thalam", "cerebellar": r"cerebell",
        "intraparenchymal": r"intraparenchymal|parenchymal|hematoma|haematoma",
        "subarachnoid": "subarachnoid", "subdural": "subdural", "epidural": r"epidural|extradural"}


def postprocess(raw, text):
    """Turn the model's compact answer into an ontology-v1.2 record. Every rule applied is
    logged in flags; nothing is changed silently."""
    flags = []
    low = text.lower()
    sents = [s for s in re.split(r"[.;\n]+", low) if s.strip()]
    a = {k: raw[k] for k in MAIN}

    for k in MAIN:                                     # sentence-scoped NA guard (G1, G4)
        if k == "lvo" or a[k] != "Not assessable":
            continue
        if not any(re.search(KW[k], s) and re.search(LIMIT, s) for s in sents):
            a[k] = "Absent"
            flags.append(f"na_guard:{k}")

    for k in MAIN:                                     # mention guard, the mirror of the NA
        if k == "lvo" or a[k] not in ("Present", "Uncertain"):   # guard: a finding the report
            continue                                             # never mentions cannot be
        if not re.search(KW[k], low):                            # Present or Uncertain (G1, G7)
            a[k] = "Absent"
            flags.append(f"mention_guard:{k}")

    has_vessel = bool(re.search(VESSEL_IMAGING, low))  # LVO guard (§4.13)
    if not has_vessel and a["lvo"] == "Present":
        a["lvo"] = "Uncertain"; flags.append("lvo_present_without_vessel_imaging")
    if not has_vessel and a["lvo"] == "Absent":
        a["lvo"] = "Not assessable"; flags.append("lvo_absent_without_vessel_imaging")

    hern = {h: "Absent" for h in HERN}
    for item in raw["herniation"]:
        lvl = item["level"]
        if lvl == "Not assessable" and not any(re.search(HERN_KW, s) and re.search(LIMIT, s) for s in sents):
            flags.append(f"na_guard:herniation_{item['subtype']}")
            continue
        if lvl in ("Present", "Uncertain") and not re.search(HERN_KW, low):
            flags.append(f"mention_guard:herniation_{item['subtype']}")
            continue
        order = ["Absent", "Not assessable", "Uncertain", "Present"]
        if order.index(lvl) > order.index(hern[item["subtype"]]):
            hern[item["subtype"]] = lvl

    change = {k: "not_stated" for k in MAIN}
    for c in raw["changes"]:
        f, d = c["field"], c["direction"]
        if a[f] == "Absent" and d != "resolved":
            flags.append(f"change_dropped:{f}")
            continue
        if a[f] == "Present" and d == "resolved":
            flags.append(f"resolved_but_present:{f}")
        change[f] = d

    rec = {ONTO[k]: a[k] for k in MAIN}
    rec.update({ONTO[k] + "__change": change[k] for k in MAIN})
    rec.update({f"herniation_{h}": hern[h] for h in HERN})
    lv = set(hern.values())
    rec["herniation"] = ("Present" if "Present" in lv else "Uncertain" if "Uncertain" in lv
                         else "Absent")
    comp = sorted(set(raw["haem_compartment"]))
    if a["ivh"] == "Present":
        comp.append("intraventricular")
    rec["infratentorial_iph"] = bool({"brainstem", "cerebellar"} & set(raw["iph_site"]))
    def mentioned(items):                              # list items must appear in the report
        keep = [x for x in items if x == "intraventricular" or re.search(TERM[x], low)]
        if len(keep) < len(set(items)):
            flags.append("mention_guard:list")
        return sorted(set(keep))
    rec["haemorrhage_compartment"] = mentioned(comp)
    rec["iph_location"] = mentioned(raw["iph_site"])
    rec["infarct_territory"] = mentioned(raw["territory"])
    rec["infarct_region"] = mentioned(raw["region"])
    rec["multiple_territories"] = len(set(raw["territory"])) >= 2
    rec["midline_shift_mm"] = raw["mls_mm"]

    if raw["iph_site"] and "intraparenchymal" not in raw["haem_compartment"]:
        flags.append("iph_site_without_intraparenchymal")
    if raw["haem_compartment"] and a["haem"] in ("Absent", "Not assessable"):
        flags.append("compartment_without_haemorrhage")
    if (raw["territory"] or raw["region"]) and a["infarct_acute"] == "Absent" and a["chronic_isch"] == "Absent":
        flags.append("location_without_infarct")
    mm = raw["mls_mm"]
    if mm is not None and a["mls"] != "Present":
        flags.append("mm_without_shift")
    if mm is not None and not (0 < mm <= 30):
        flags.append("mm_out_of_range")
    return rec, flags


PROMPT_VERSION = hashlib.sha256((TEMPLATE + RULES + MODEL + json.dumps(SCHEMA, sort_keys=True)
                                 + inspect.getsource(postprocess) + KW.__repr__() + TERM.__repr__() + LIMIT
                                 + VESSEL_IMAGING + HERN_KW).encode()).hexdigest()[:12]


def build_prompt(text):
    return TEMPLATE.replace("RULES_BLOCK", RULES).replace("REPORT_TEXT", text)


def call_model(text, timeout=900):
    body = {"model": MODEL, "prompt": build_prompt(text), "stream": False, "format": SCHEMA,
            "options": {"temperature": 0, "seed": 0, "num_ctx": 6144}}
    req = urllib.request.Request(OLLAMA, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def schema_errors(raw):
    errs = []
    if set(raw) != set(SCHEMA["properties"]):
        errs.append("keys")
    for k in MAIN:
        if raw.get(k) not in ASSERT:
            errs.append(f"enum:{k}")
    for k, allowed in (("territory", TERR), ("region", REGION), ("haem_compartment", COMP), ("iph_site", IPH)):
        v = raw.get(k)
        if not isinstance(v, list) or any(x not in allowed for x in v):
            errs.append(f"list:{k}")
    for item in raw.get("herniation", []) or []:
        if item.get("subtype") not in HERN or item.get("level") not in ("Present", "Uncertain", "Not assessable"):
            errs.append("herniation")
    for c in raw.get("changes", []) or []:
        if c.get("field") not in MAIN or c.get("direction") not in DIR:
            errs.append("changes")
    mm = raw.get("mls_mm")
    if mm is not None and not isinstance(mm, (int, float)):
        errs.append("mls_mm")
    return errs


def extract_one(text):
    last = None
    for attempt in (1, 2):
        t0 = time.time()
        try:
            r = call_model(text)
            raw = json.loads(r["response"])
            errs = schema_errors(raw)
            if not errs:
                rec, flags = postprocess(raw, text)
                return {"record": rec, "raw": raw, "flags": flags, "error": None, "attempts": attempt,
                        "seconds": round(time.time() - t0, 1),
                        "prompt_eval_count": r.get("prompt_eval_count"), "eval_count": r.get("eval_count")}
            last = "schema:" + ";".join(errs)
        except Exception as e:
            last = type(e).__name__
    return {"record": None, "raw": None, "flags": [], "error": last, "attempts": 2, "seconds": None,
            "prompt_eval_count": None, "eval_count": None}


def load_inputs(args):
    if args.fictional:
        with open(os.path.join(HERE, "fictional_test_reports.json"), encoding="utf-8") as fh:
            d = json.load(fh)
        return [(r["id"], r["text"]) for r in d["reports"]], os.path.join(HERE, "fictional_v12_out.jsonl")
    csv.field_size_limit(10 ** 7)
    with open(args.input, newline="", encoding="utf-8") as fh:
        return [(r["note_id"], r["text"]) for r in csv.DictReader(fh)], args.output


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fictional", action="store_true")
    ap.add_argument("--input")
    ap.add_argument("--output")
    args = ap.parse_args()
    if not args.fictional and not (args.input and args.output):
        ap.error("give --fictional, or both --input and --output")
    rows, out = load_inputs(args)
    done = set()
    if os.path.exists(out):
        with open(out, encoding="utf-8") as fh:
            prev = [json.loads(l) for l in fh if l.strip()]
        kept = [r for r in prev if not r["error"] and r["prompt_version"] == PROMPT_VERSION]
        if len(kept) < len(prev):
            with open(out + ".tmp", "w", encoding="utf-8") as fh:
                fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in kept)
            os.replace(out + ".tmp", out)
            print(f"resume: dropped {len(prev) - len(kept)} failed or other-version record(s)")
        done = {r["note_id"] for r in kept}
    todo = [(n, t) for n, t in rows if n not in done]
    print(f"model {MODEL} | prompt_version {PROMPT_VERSION} | {len(rows)} reports, "
          f"{len(done)} done, {len(todo)} to run")
    ok = err = flagged = 0
    secs = []
    with open(out, "a", encoding="utf-8") as fh:
        for i, (nid, text) in enumerate(todo, 1):
            res = extract_one(text)
            res.update({"note_id": nid, "model": MODEL, "prompt_version": PROMPT_VERSION})
            fh.write(json.dumps(res, ensure_ascii=False) + "\n")
            fh.flush()
            if res["error"]:
                err += 1
            else:
                ok += 1; secs.append(res["seconds"]); flagged += bool(res["flags"])
            if i % 10 == 0 or i == len(todo):
                m = sum(secs) / len(secs) if secs else float("nan")
                print(f"  {i}/{len(todo)} | ok {ok} | failed {err} | flagged {flagged} | mean {m:.1f} s/report")
    print(f"written: {out}")


if __name__ == "__main__":
    main()
