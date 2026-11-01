"""
Paper 3 — local neuroimaging-report extractor. DEVELOPMENT VERSION, NOT FROZEN.

Runs a local open-weight model (qwen2.5:7b through Ollama on project hardware) over
head CT/MRI reports and returns the phenotype record defined by ontology v1.1.
Report text never leaves the machine (protocol v1.1 §8.4): the only network call is to
localhost, and that is asserted below.

The output structure follows ontology v1.1 and the model is held to it by a JSON schema
passed as Ollama's structured-output `format`. The enums make an out-of-scale answer
impossible — the first failure seen in the throughput probe was a location string
returned where an assertion level was required.

  assertion fields  Present / Absent / Uncertain / Not assessable, each with a change field
  multi-label lists infarct_territory, haemorrhage_location
  conditional number midline_shift_mm — null unless the report states a value

Phenotype-specific lexical rules are NOT in here yet. They come from guideline v1.1 §8
once it is frozen, and are read from RULES_FILE. Until then the prompt carries only the
v1.1 framework rules, plus the not-mentioned rule below (v1.2 item E).

DUA guard: nothing in this module prints report text. Logs carry note_ids and counts.

Usage
  python extract.py --fictional                          built-in FICTIONAL test set
  python extract.py --input reports.csv --output out.jsonl
                                                          CSV columns: note_id, text
Resumable: successful note_ids in the output file are skipped; failed ones are retried.
For long runs:  caffeinate -i python extract.py --input ... --output ...
"""
import argparse
import csv
import hashlib
import json
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = "qwen2.5:7b"
OLLAMA = "http://localhost:11434/api/generate"
assert OLLAMA.startswith("http://localhost"), "report text may only go to a local model"
RULES_FILE = os.path.join(HERE, "lexical_rules_frozen.md")     # written at guideline freeze

# What a finding the report never mentions is recorded as. v1.1's four-level scale did
# not say; decided 11 Sep 2026 (protocol v1.2 item E) from the study lead's practice on
# the 50 development reports: Absent — except a phenotype the examination cannot
# demonstrate (LVO on a non-vascular study), which is Not assessable; the prompt's LVO
# rule carries that exception.
NOT_MENTIONED = "Absent"

ASSERT = ["Present", "Absent", "Uncertain", "Not assessable"]
CHANGE = ["new", "increased", "stable", "decreased", "resolved", "not_stated"]
ASSERTION_FIELDS = [
    "acute_infarction", "large_territorial_infarct", "intracranial_haemorrhage",
    "intraventricular_haemorrhage", "cerebral_oedema", "midline_shift_present",
    "hydrocephalus", "mass_effect", "herniation", "chronic_ischaemic_change",
    "large_vessel_occlusion",
]
TERRITORY = ["ACA", "MCA", "PCA", "vertebrobasilar_brainstem", "cerebellar",
             "watershed", "deep_lacunar"]
LOCATION = ["lobar", "deep_basal_ganglia", "thalamic", "brainstem", "cerebellar",
            "subarachnoid", "subdural", "epidural"]


def build_schema():
    props = {}
    for f in ASSERTION_FIELDS:
        props[f] = {"type": "string", "enum": ASSERT}
        props[f + "_change"] = {"type": "string", "enum": CHANGE}
    props["infarct_territory"] = {"type": "array", "items": {"type": "string", "enum": TERRITORY}}
    props["haemorrhage_location"] = {"type": "array", "items": {"type": "string", "enum": LOCATION}}
    props["midline_shift_mm"] = {"type": ["number", "null"]}
    return {"type": "object", "properties": props, "required": list(props),
            "additionalProperties": False}


SCHEMA = build_schema()

TEMPLATE = """You are extracting structured findings from ONE head CT or MRI radiology report.
Use only what the report states.

ASSERTION VALUES. Every assertion field takes exactly one value:
- Present: the finding is asserted.
- Absent: the finding is explicitly excluded ("no", "without", "negative for", "no evidence of").
- Uncertain: hedged, neither asserted nor excluded ("cannot exclude", "possible", "possibly",
  "suspicious for", "equivocal", "questionable").
- Not assessable: this examination cannot demonstrate the finding, or the report says the
  relevant region could not be evaluated.
A finding the report does not mention at all: answer NOT_MENTIONED_VALUE.

RULES.
- A finding that has decreased but is still there is Present, with change "decreased".
  Only "resolved" or "no residual" makes it Absent.
- Negation applies only to what is negated. "No large territorial infarct" makes
  large_territorial_infarct Absent; it says nothing about acute_infarction.
- A specific, localised positive description in the findings outranks a general summary
  such as "no acute intracranial process". If findings and impression truly contradict
  each other, answer Uncertain.
- large_vessel_occlusion is Not assessable unless the report describes vessel imaging
  (CTA or MRA) or explicitly comments on vessel patency.
- mass_effect means displacement or compression of brain structures by a lesion
  (effacement, compression, shift). A "mass" (tumour) is NOT mass effect:
  "cannot exclude an underlying mass" says nothing about mass_effect.
- chronic_ischaemic_change covers chronic small-vessel disease, old infarcts,
  encephalomalacia and gliosis. It is independent of acute_infarction; both may be Present.
- midline_shift_present is about any shift of midline structures.

CHANGE FIELDS. For each <field>_change: new, increased, stable, decreased, resolved or
not_stated — only from an explicit comparison with a prior study; otherwise not_stated.

LISTS. infarct_territory: territories of ACUTE infarction only; several allowed; [] if none.
haemorrhage_location: locations of haemorrhage; several allowed; [] if none.

midline_shift_mm: the number of millimetres only if the report states a measurement
(convert cm to mm); otherwise null. Never estimate.
RULES_BLOCK
REPORT:
<<<
REPORT_TEXT
>>>"""


def load_rules():
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, encoding="utf-8") as fh:
            return "\nPHENOTYPE-SPECIFIC RULES (frozen guideline):\n" + fh.read().strip() + "\n"
    return ""


RULES = load_rules()
PROMPT_VERSION = hashlib.sha256(
    (TEMPLATE + NOT_MENTIONED + RULES + MODEL + json.dumps(SCHEMA, sort_keys=True)).encode()
).hexdigest()[:12]


def build_prompt(text):
    return (TEMPLATE.replace("NOT_MENTIONED_VALUE", NOT_MENTIONED)
                    .replace("RULES_BLOCK", RULES)
                    .replace("REPORT_TEXT", text))


def call_model(text, timeout=900):
    body = {"model": MODEL, "prompt": build_prompt(text), "stream": False, "format": SCHEMA,
            "options": {"temperature": 0, "seed": 0, "num_ctx": 4096}}
    req = urllib.request.Request(OLLAMA, json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def schema_errors(rec):
    """Hard errors: the record does not match the schema. Triggers one retry."""
    errs = []
    missing = set(SCHEMA["properties"]) - set(rec)
    extra = set(rec) - set(SCHEMA["properties"])
    if missing:
        errs.append(f"missing:{sorted(missing)}")
    if extra:
        errs.append(f"extra:{sorted(extra)}")
    for f in ASSERTION_FIELDS:
        if rec.get(f) not in ASSERT:
            errs.append(f"enum:{f}")
        if rec.get(f + "_change") not in CHANGE:
            errs.append(f"enum:{f}_change")
    for f, allowed in (("infarct_territory", TERRITORY), ("haemorrhage_location", LOCATION)):
        v = rec.get(f)
        if not isinstance(v, list) or any(x not in allowed for x in v):
            errs.append(f"list:{f}")
    mm = rec.get("midline_shift_mm")
    if mm is not None and not isinstance(mm, (int, float)):
        errs.append("type:midline_shift_mm")
    return errs


def consistency_flags(rec):
    """Soft flags: internally inconsistent but schema-valid. Recorded, never 'fixed'."""
    flags = []
    if rec["midline_shift_mm"] is not None and rec["midline_shift_present"] != "Present":
        flags.append("mm_without_shift")
    if rec["midline_shift_mm"] is not None and not (0 < rec["midline_shift_mm"] <= 30):
        flags.append("mm_out_of_range")
    if rec["haemorrhage_location"] and rec["intracranial_haemorrhage"] in ("Absent", "Not assessable"):
        flags.append("location_without_haemorrhage")
    if rec["infarct_territory"] and rec["acute_infarction"] in ("Absent", "Not assessable"):
        flags.append("territory_without_infarction")
    for f in ASSERTION_FIELDS:
        if rec[f + "_change"] != "not_stated" and rec[f] == "Absent" and rec[f + "_change"] != "resolved":
            flags.append(f"change_on_absent:{f}")
    return flags


def extract_one(text):
    last = None
    for attempt in (1, 2):
        t0 = time.time()
        try:
            r = call_model(text)
            rec = json.loads(r["response"])
            errs = schema_errors(rec)
            if not errs:
                return {"record": rec, "flags": consistency_flags(rec), "error": None,
                        "attempts": attempt, "seconds": round(time.time() - t0, 1),
                        "prompt_eval_count": r.get("prompt_eval_count"),
                        "eval_count": r.get("eval_count")}
            last = "schema:" + ";".join(errs)
        except Exception as e:                      # network, timeout, JSON parse
            last = f"{type(e).__name__}"
    return {"record": None, "flags": [], "error": last, "attempts": 2, "seconds": None,
            "prompt_eval_count": None, "eval_count": None}


def load_inputs(args):
    if args.fictional:
        with open(os.path.join(HERE, "fictional_test_reports.json"), encoding="utf-8") as fh:
            d = json.load(fh)
        return [(r["id"], r["text"]) for r in d["reports"]], os.path.join(HERE, "fictional_out.jsonl")
    csv.field_size_limit(10 ** 7)
    with open(args.input, newline="", encoding="utf-8") as fh:
        rows = [(r["note_id"], r["text"]) for r in csv.DictReader(fh)]
    return rows, args.output


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
        # Resume: keep successful records, drop failed ones so they are retried, and
        # rewrite the file so a note_id never appears twice.
        with open(out, encoding="utf-8") as fh:
            prev = [json.loads(line) for line in fh if line.strip()]
        kept = [r for r in prev if not r["error"]]
        if len(kept) < len(prev):
            tmp = out + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                for r in kept:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            os.replace(tmp, out)
            print(f"resume: {len(prev) - len(kept)} failed record(s) removed for retry")
        done = {r["note_id"] for r in kept}
    todo = [(n, t) for n, t in rows if n not in done]
    print(f"model {MODEL} | prompt_version {PROMPT_VERSION} | not-mentioned default "
          f"'{NOT_MENTIONED}' (v1.2 item E) | frozen rules loaded: {bool(RULES)}")
    print(f"{len(rows)} reports, {len(done)} already done, {len(todo)} to run")

    n_ok = n_err = n_flag = 0
    secs = []
    with open(out, "a", encoding="utf-8") as fh:
        for i, (note_id, text) in enumerate(todo, 1):
            res = extract_one(text)
            res.update({"note_id": note_id, "model": MODEL, "prompt_version": PROMPT_VERSION})
            fh.write(json.dumps(res, ensure_ascii=False) + "\n")
            fh.flush()
            if res["error"]:
                n_err += 1
            else:
                n_ok += 1
                secs.append(res["seconds"])
                n_flag += bool(res["flags"])
            if i % 25 == 0 or i == len(todo):
                mean = sum(secs) / len(secs) if secs else float("nan")
                print(f"  {i}/{len(todo)} | ok {n_ok} | failed {n_err} | flagged {n_flag} | "
                      f"mean {mean:.1f} s/report")
    print(f"written: {out}")


if __name__ == "__main__":
    main()
