"""
Paper 3: resolve {cite:key} markers in a manuscript source into numbered citations.

Numbers follow first appearance; the reference list is written from
manuscript/references/references.json (built from the registries by 54), inserted before the Tables.
Fails if a key is unknown, if any [REF: placeholder remains, or if a registry entry goes uncited.

Usage: python 56_number_citations.py paper3_draft_v4_src.md paper3_draft_v4.md
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import json
import re
import sys

M = _REPO_ROOT + "/08_paper3_multimodal/manuscript"


def compress(ns):
    ns, out, i = sorted(set(ns)), [], 0
    while i < len(ns):
        j = i
        while j + 1 < len(ns) and ns[j + 1] == ns[j] + 1:
            j += 1
        out.append(f"{ns[i]}" if j == i else f"{ns[i]},{ns[j]}" if j == i + 1 else f"{ns[i]}–{ns[j]}")
        i = j + 1
    return ",".join(out)


def main(src, dst):
    refs = {r["key"]: r for r in json.load(open(f"{M}/references/references.json", encoding="utf-8"))}
    s = open(f"{M}/{src}", encoding="utf-8").read()
    assert "[REF:" not in s, re.findall(r"\[REF:[^\]]*\]", s)
    order = []
    for keys in re.findall(r"\{cite:([^}]+)\}", s):
        for k in keys.split(","):
            assert k in refs, f"unknown reference key {k}"
            if k not in order:
                order.append(k)
    unused = sorted(set(refs) - set(order))
    assert not unused, f"verified references not cited: {unused}"
    num = {k: i + 1 for i, k in enumerate(order)}
    s = re.sub(r"\{cite:([^}]+)\}", lambda m: "[" + compress([num[k] for k in m.group(1).split(",")]) + "]", s)
    s = re.sub(r"DRAFT (v\d+) SOURCE", r"DRAFT \1", s, count=1)
    reflist = "\n## References\n\n" + "\n".join(f"{num[k]}. {refs[k]['formatted']}" for k in order) + "\n"
    assert s.count("\n---\n\n## Tables") == 1
    s = s.replace("\n---\n\n## Tables", "\n---\n" + reflist + "\n---\n\n## Tables", 1)
    open(f"{M}/{dst}", "w", encoding="utf-8").write(s)
    checks = len(re.findall(r"\[CHECK", s))
    print(f"{dst}: {len(order)} references, numbered by first appearance; [CHECK] left: {checks}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
