"""
Paper 3: check citations in both drafts.

  * every citation number resolves to a list entry, and numbers first appear in order 1, 2, 3, …
  * the list is exactly references.json in citation order (EN and CN identical)
  * the Chinese draft cites the same numbers in the same order as the English draft
  * each citation sits in a sentence about what the cited paper is cited for — so a sentence edited or
    moved after numbering cannot keep a citation that no longer fits
  * each DOI/arXiv record is fetched again and its title compared with the cached one (--offline skips)
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
MS = HERE / "manuscript"
REFS = json.load(open(MS / "references" / "references.json", encoding="utf-8"))
DOCS = {"EN": (MS / "paper3_draft_v5.md").read_text(encoding="utf-8"),
        "CN": (MS / "paper3_draft_v5_CN.md").read_text(encoding="utf-8")}
R = []

# what each reference must be cited for: a pattern the citing sentence has to contain (EN | CN)
CONTEXT = {
    "davis2006": r"[Hh]aematoma expansion|血肿扩大", "hacke1996": r"oedema|脑水肿", "robba2019": r"ventilation|机械通气",
    "ropper1986": r"displacement|移位", "hanley2009": r"[Ii]ntraventricular|脑室内出血",
    "alotaibi2025": r"report|报告", "sun2026": r"report|报告|deterioration|恶化", "liu2025": r"respiratory failure|呼吸衰竭",
    "lei2026preprint": r"176|as defined previously|前期研究",
    "lei2026p1preprint": r"72 hours|as defined previously|72 小时|前期研究", "tripodai2024": r"TRIPOD", "johnson2023": r"MIMIC-IV",
    "mimiciv31": r"MIMIC-IV", "goldberger2000": r"MIMIC-IV", "mimicivnote22": r"MIMIC-IV-Note",
    "qwen2024": r"Qwen2\.5|Qwen", "vickers2006": r"[Dd]ecision curve|决策曲线", "qwen38_2026": r"Qwen3\.8",
}


def claim(text, ok, detail=""):
    R.append(bool(ok))
    print(f"  {'OK ' if ok else 'BAD'}  {text}" + (f"\n         {detail}" if detail else ""))


def expand(group):
    out = []
    for part in group.split(","):
        if "–" in part:
            a, b = map(int, part.split("–"))
            out += list(range(a, b + 1))
        else:
            out.append(int(part))
    return out


def body_and_list(text, lang):
    head = "## References" if lang == "EN" else "# 参考文献"
    body, rest = text.split(head)
    lst = rest.split("\n---")[0].strip().splitlines()
    return body, [l for l in lst if re.match(r"^\d+\. ", l)]


seqs = {}
for lang, text in DOCS.items():
    print(f"\n{lang}\n")
    body, lst = body_and_list(text, lang)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    claim("no unresolved placeholders ({cite:…} or [REF: …])", "{cite:" not in body and "[REF:" not in body)
    groups = re.findall(r"\[(\d[\d,–]*)\]", body)
    seq = [n for g in groups for n in expand(g)]
    seqs[lang] = groups
    first = []
    for n in seq:
        if n not in first:
            first.append(n)
    claim("citation numbers first appear in order 1, 2, 3, …", first == list(range(1, len(first) + 1)), first)
    claim(f"all {len(REFS)} references are cited and no number exceeds the list",
          sorted(set(seq)) == list(range(1, len(REFS) + 1)) and len(lst) == len(REFS))
    # the list must equal references.json entries, and entry i must be the i-th first-cited key
    fmt = {r["formatted"]: r["key"] for r in REFS}
    keys = [fmt.get(re.sub(r"^\d+\. ", "", l)) for l in lst]
    claim("every list entry is a references.json record, verbatim", None not in keys)
    claim("list numbering is 1…N in order", [int(l.split(".")[0]) for l in lst] == list(range(1, len(lst) + 1)))
    num2key = dict(zip(range(1, len(keys) + 1), keys))
    sentences = re.split(r"(?<=[.。;；])\s+|\n", body)
    misplaced = []
    for s in sentences:
        for g in re.findall(r"\[(\d[\d,–]*)\]", s):
            for n in expand(g):
                k = num2key.get(n)
                if k and not re.search(CONTEXT[k], s):
                    misplaced.append((n, k, s.strip()[:90]))
    claim("each citation sits in a sentence about what the reference is cited for", not misplaced, misplaced)
    if lang == "CN":
        en_list = body_and_list(DOCS["EN"], "EN")[1]
        claim("Chinese reference list identical to the English list", lst == en_list)

print("\nEN / CN parity\n")
claim("Chinese draft cites the same numbers in the same order as the English draft", seqs["EN"] == seqs["CN"],
      f"EN {seqs['EN']}\n         CN {seqs['CN']}")

if "--offline" not in sys.argv:
    print("\nRegistry titles (live)\n")

    def get(url):
        req = urllib.request.Request(url, headers={"User-Agent": "paper3-citation-check (mailto:your.name@example.org)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8")

    norm = lambda t: re.sub(r"[^a-z0-9]", "", t.lower())
    for r in REFS:
        try:
            if r["registry"] == "crossref":
                live = json.loads(get(f"https://api.crossref.org/works/{r['id']}"))["message"]["title"][0]
                cached = r["raw"]["crossref"]["title"][0]
            elif r["registry"] == "datacite":
                live = json.loads(get(f"https://api.datacite.org/dois/{r['id']}"))["data"]["attributes"]["titles"][0]["title"]
                cached = r["raw"]["titles"][0]["title"]
            elif r["registry"] == "huggingface":
                live = json.loads(get(f"https://huggingface.co/api/models/{r['id']}"))["id"]
                cached = r["raw"]["id"]
            else:
                x = get(f"https://export.arxiv.org/api/query?id_list={r['id']}")
                live = re.findall(r"<title>(.*?)</title>", x[x.index("<entry>"):], re.S)[0]
                cached = re.findall(r"<title>(.*?)</title>", r["raw"]["arxiv_entry"], re.S)[0]
            claim(f"{r['key']}: registry title unchanged", norm(live) == norm(cached), live[:80])
        except Exception as e:
            claim(f"{r['key']}: registry reachable", False, repr(e)[:100])

print(f"\n{len(R)} citation checks, {R.count(False)} failed")
sys.exit(1 if R.count(False) else 0)
