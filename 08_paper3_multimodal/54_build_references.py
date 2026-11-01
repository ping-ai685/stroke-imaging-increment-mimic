"""
Paper 3: build the reference list from the DOI registries, never from memory.

Every reference is a DOI (or arXiv identifier) that was checked on 16 Sep 2026 against Crossref,
DataCite, PubMed or arXiv, together with the claim it supports in the manuscript. This script
fetches the registry record for each and formats it (Vancouver, up to six authors then et al.), so
no bibliographic field is typed by hand. The raw registry responses are cached next to the output
so the list can be rebuilt offline and audited.

Writes manuscript/references/references.json (raw + formatted) and references.md.
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import json
import os
import time
import urllib.parse
import urllib.request

OUT = _REPO_ROOT + "/08_paper3_multimodal/manuscript/references"

REFS = [  # key, registry, identifier, what it supports in the manuscript
    ("robba2019", "crossref", "10.1186/s13054-019-2662-8", "Intro: respiratory failure / ventilation after ischaemic stroke"),
    ("davis2006", "crossref", "10.1212/01.wnl.0000208408.98482.99", "Intro: haematoma expansion early after ICH, outcome"),
    ("hacke1996", "crossref", "10.1001/archneur.1996.00550040037012", "Intro: malignant oedema / herniation course"),
    ("liu2025", "crossref", "10.1002/brb3.71146", "Intro: MIMIC-IV ICU respiratory-failure model without imaging data"),
    ("hanley2009", "crossref", "10.1161/STROKEAHA.108.535419", "Intro/Discussion: intraventricular haemorrhage and outcome"),
    ("ropper1986", "crossref", "10.1056/NEJM198604103141504", "Intro/Discussion: midline shift and level of consciousness"),
    ("alotaibi2025", "crossref", "10.3389/fneur.2025.1722965", "Intro/Discussion: report-derived phenotypes added to stroke mortality model (MIMIC-III)"),
    ("sun2026", "crossref", "10.3389/fneur.2026.1787921", "Intro/Discussion: report text + clinical data, END after AIS, admission time point"),
    ("tripodai2024", "crossref", "10.1136/bmj-2023-078378", "Methods: reporting guideline"),
    ("johnson2023", "crossref", "10.1038/s41597-022-01899-x", "Methods: MIMIC-IV description"),
    ("mimiciv31", "datacite", "10.13026/kpb9-mt58", "Methods: MIMIC-IV v3.1 dataset"),
    ("mimicivnote22", "datacite", "10.13026/1n74-ne17", "Methods: MIMIC-IV-Note v2.2 dataset"),
    ("goldberger2000", "crossref", "10.1161/01.CIR.101.23.e215", "Methods: PhysioNet (required citation)"),
    ("qwen2024", "arxiv", "2412.15115", "Methods: extraction model"),
    ("vickers2006", "crossref", "10.1177/0272989X06295361", "Methods: decision curve analysis"),
    ("lei2026p1preprint", "crossref", "10.64898/2026.08.30.26361738", "Intro/Methods: the four dynamic states; cohort definition (preprint; Neurocritical Care under review)"),
    ("lei2026preprint", "crossref", "10.64898/2026.09.07.26362407", "Intro: external validation of the dynamic states (preprint; JAMIA Open under review)"),
    ("qwen38_2026", "huggingface", "Qwen/Qwen3.8-27B", "Methods/Results: second extraction model, protocol v1.3 C1 (official model card; verified 4 Oct 2026)"),
]
ACCESSED = "4 Oct 2026"                      # date the web-page references were checked


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "paper3-reference-builder (mailto:your.name@example.org)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def authors_vancouver(names):
    """names: list of (family, given). Vancouver: Family Initials, up to 6 then et al."""
    fmt = []
    for fam, giv in names:
        initials = "".join(p[0] for p in giv.replace("-", " ").replace(".", " ").split() if p) if giv else ""
        fmt.append(f"{fam} {initials}".strip())
    return ", ".join(fmt[:6]) + (", et al" if len(fmt) > 6 else "")


def pubmed(doi):
    """PubMed record for a DOI, or None. NLM journal abbreviations are what Vancouver uses."""
    ids = json.loads(get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json"
                         f"&term={urllib.parse.quote(doi)}[doi]"))["esearchresult"]["idlist"]
    if len(ids) != 1:
        return None
    m = json.loads(get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json"
                       f"&id={ids[0]}"))["result"][ids[0]]
    return ids[0], m


def crossref(doi):
    m = json.loads(get(f"https://api.crossref.org/works/{doi}"))["message"]
    pm = pubmed(doi) if m.get("type") != "posted-content" else None
    if pm:
        pmid, r = pm
        names = [a["name"] for a in r["authors"] if a.get("authtype") == "Author"]
        auth = ", ".join(names[:6]) + (", et al" if len(names) > 6 else "")
        year = r["pubdate"][:4]
        loc = f"{year};{r['volume']}" + (f"({r['issue']})" if r["issue"] else "") + (f":{r['pages']}" if r["pages"] else "")
        text = f"{auth}. {r['title'].rstrip('.')}. {r['source'].replace('.', '')}. {loc}. doi:{doi}"
        return {"crossref": m, "pubmed": r, "pmid": pmid}, text, len(names)
    names = [(a.get("family", a.get("name", "")), a.get("given", "")) for a in m.get("author", [])]
    year = (m.get("published-print") or m.get("published-online") or m.get("issued") or m.get("posted"))["date-parts"][0][0]
    title = m["title"][0].rstrip(".") + (f": {m['subtitle'][0]}" if m.get("subtitle") else "")
    journal = (m.get("short-container-title") or m.get("container-title") or [""])[0].replace(".", "")
    if m.get("type") == "posted-content":
        journal = m.get("institution", [{}])[0].get("name", "") or "Preprint"
    vol, iss, page = m.get("volume", ""), m.get("issue", ""), m.get("page", m.get("article-number", ""))
    loc = f"{year}" + (f";{vol}" if vol else "") + (f"({iss})" if iss else "") + (f":{page}" if page else "")
    return {"crossref": m}, f"{authors_vancouver(names)}. {title}. {journal}. {loc}. doi:{doi}", len(names)


def datacite(doi):
    a = json.loads(get(f"https://api.datacite.org/dois/{doi}"))["data"]["attributes"]
    names = [(c.get("familyName", c["name"]), c.get("givenName", "")) for c in a["creators"]]
    text = (f"{authors_vancouver(names)}. {a['titles'][0]['title']} (version {a['version']}). "
            f"{a['publisher'] if isinstance(a['publisher'], str) else a['publisher']['name']}; {a['publicationYear']}. doi:{a['doi']}")
    return a, text, len(names)


def arxiv(aid):
    import re
    x = get(f"https://export.arxiv.org/api/query?id_list={aid}")
    entry = x[x.index("<entry>"):]
    title = re.sub(r"\s+", " ", re.findall(r"<title>(.*?)</title>", entry, re.S)[0]).strip()
    year = re.findall(r"<published>(\d{4})", entry)[0]
    full = [re.sub(r"\s+", " ", n).strip() for n in re.findall(r"<name>(.*?)</name>", entry, re.S)]
    group = None
    if ":" in full[:3]:                              # arXiv lists a group author as "Qwen", ":", names...
        i = full.index(":")
        group, full = " ".join(full[:i]), full[i + 1:]
    names = []
    for n in full:                                   # "An Yang" -> ("Yang", "An")
        parts = n.split()
        names.append((parts[-1], " ".join(parts[:-1])))
    auth = (f"{group}; " if group else "") + authors_vancouver(names)
    text = f"{auth}. {title}. arXiv:{aid} [Preprint]. {year}. doi:10.48550/arXiv.{aid}"
    return {"arxiv_entry": entry[:6000]}, text, len(names)


def huggingface(repo):
    """An official model card on Hugging Face (no DOI or preprint exists for the model itself).
    Vancouver web-page form, with the access date the journal requires."""
    m = json.loads(get(f"https://huggingface.co/api/models/{repo}"))
    assert m["id"] == repo
    author = {"Qwen": "Qwen Team"}.get(m["author"], m["author"])
    year = m["lastModified"][:4]
    text = f"{author}. {repo.split('/')[-1]} [model card]. Hugging Face; {year}. https://huggingface.co/{repo}. Accessed {ACCESSED}"
    return {"id": m["id"], "author": m["author"], "createdAt": m.get("createdAt"), "lastModified": m["lastModified"],
            "sha": m.get("sha")}, text, 0


def main():
    import sys
    os.makedirs(OUT, exist_ok=True)
    only = set(sys.argv[sys.argv.index("--only") + 1:]) if "--only" in sys.argv else None
    cached = {r["key"]: r for r in json.load(open(f"{OUT}/references.json"))} if only else {}
    rows = []
    for key, reg, ident, supports in REFS:
        if only is not None and key not in only:      # --only KEY ...: refetch these, keep the rest from cache
            rows.append(cached[key])
            continue
        raw, text, n = {"crossref": crossref, "datacite": datacite, "arxiv": arxiv, "huggingface": huggingface}[reg](ident)
        rows.append({"key": key, "registry": reg, "id": ident, "supports": supports, "n_authors": n,
                     "formatted": text, "raw": raw})
        print(f"[{key}] {text}")
        time.sleep(0.3)
    json.dump(rows, open(f"{OUT}/references.json", "w"), indent=1, ensure_ascii=False, default=str)
    with open(f"{OUT}/references.md", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(f"- **{r['key']}** — {r['formatted']}  \n  _supports:_ {r['supports']}\n")
    print(f"\n{len(rows)} references -> {OUT}/references.json, references.md")


if __name__ == "__main__":
    main()
