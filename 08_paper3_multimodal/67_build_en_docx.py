"""
Paper 3: build an English .docx from a Markdown file in manuscript/ with pandoc (located without relying on PATH).
Usage: python 67_build_en_docx.py supplement_v1.md
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import os
import re
import shutil
import subprocess
import sys
import zipfile

M = _REPO_ROOT + "/08_paper3_multimodal/manuscript"


def pandoc():
    for c in [shutil.which("pandoc"), "/opt/homebrew/bin/pandoc", "/usr/local/bin/pandoc"]:
        if c and os.path.exists(c):
            return c
    sys.exit("pandoc not found")


sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from docx_tables import format_tables  # noqa: E402


src = sys.argv[1]
dst = f"{M}/{src.rsplit('.', 1)[0]}.docx"
subprocess.run([pandoc(), f"{M}/{src}", "--from", "markdown", "--to", "docx",
                "--reference-doc", f"{M}/templates/reference_en.docx", "-o", dst], check=True)
zin = zipfile.ZipFile(dst)
x = format_tables(zin.read("word/document.xml").decode("utf-8"))

# Tables (4 Oct 2026, study lead: tables broke across pages). Each table starts on a new page together with its
# title; rows never split across pages and the header row repeats; table text and the note under each table are
# 9 pt and single-spaced, so every table fits on one page.
SZ = '<w:sz w:val="18"/><w:szCs w:val="18"/>'
_AFTER_SZ = r"<w:(?:highlight|u|effect|bdr|shd|fitText|vertAlign|rtl|cs|em|lang|eastAsianLayout|specVanish|oMath)\b"


def _small(run):
    run = re.sub(r"<w:sz [^>]*/>|<w:szCs [^>]*/>", "", run)
    if "<w:rPr>" in run:
        head, rest = run.split("<w:rPr>", 1)
        body, tail = rest.split("</w:rPr>", 1)
        m = re.search(_AFTER_SZ, body)
        body = body[:m.start()] + SZ + body[m.start():] if m else body + SZ
        return f"{head}<w:rPr>{body}</w:rPr>{tail}"
    return re.sub(r"<w:r>", f"<w:r><w:rPr>{SZ}</w:rPr>", run, count=1)


def _single(ppr_par):
    """Single spacing, small space after, for the note paragraph under a table."""
    if "<w:pPr>" in ppr_par:
        ppr_par = re.sub(r"<w:spacing [^>]*/>", "", ppr_par)
        ppr_par = re.sub(r"(<w:pPr>(?:<w:pStyle [^>]*/>)?)", r'\1<w:spacing w:before="60" w:after="0" w:line="240" w:lineRule="auto"/>', ppr_par, count=1)
    return re.sub(r"<w:r>.*?</w:r>", lambda m: _small(m.group(0)), ppr_par, flags=re.S)


def _tables(xml):
    def tbl(m):
        t = re.sub(r"<w:r>.*?</w:r>", lambda r: _small(r.group(0)), m.group(0), flags=re.S)
        # Pages (the only office app on the M5) ignores the Compact style's single spacing and sizes each row from
        # the 12-pt paragraph mark, so rows came out nearly twice as tall as in Word. Spacing and mark size are
        # therefore set on every cell paragraph directly.
        t = t.replace('<w:pPr><w:pStyle w:val="Compact" /></w:pPr>',
                      '<w:pPr><w:pStyle w:val="Compact" /><w:spacing w:before="20" w:after="20" w:line="240" w:lineRule="auto"/>'
                      f'<w:rPr>{SZ}</w:rPr></w:pPr>')
        def tr(rm):
            row = rm.group(0)
            if "<w:trPr>" in row:
                return row if "<w:cantSplit" in row else row.replace("<w:trPr>", "<w:trPr><w:cantSplit/>", 1)
            return re.sub(r"(<w:tr[^>]*>)", r"\1<w:trPr><w:cantSplit/></w:trPr>", row, count=1)
        return re.sub(r"<w:tr[ >].*?</w:tr>", tr, t, flags=re.S)
    xml = re.sub(r"<w:tbl>.*?</w:tbl>", tbl, xml, flags=re.S)
    # notes: the paragraphs between a table's end and the next heading
    def note(m):
        seg = m.group(2)
        out, pos = [], 0
        for pm in re.finditer(r"<w:p>.*?</w:p>", seg, flags=re.S):
            if re.search(r'<w:pStyle w:val="Heading', pm.group(0)):
                break
            out.append(seg[pos:pm.start()] + _single(pm.group(0)))
            pos = pm.end()
        return m.group(1) + "".join(out) + seg[pos:]
    xml = re.sub(r"(</w:tbl>)(.*?)(?=<w:tbl>|<w:p><w:pPr><w:pStyle w:val=\"Heading[12]|<w:sectPr)", note, xml, flags=re.S)
    # Table titles (4 Oct 2026, second pass): each table starts a new page with its title. "Page break before" on the
    # title made Pages put the title alone on one page and the table on the next, so the break is an ordinary page
    # break run at the start of the title, 1 pt high so that it never needs a line of its own on a full page. Titles
    # are 11-pt bold and single-spaced, so the longest table (Table 4) fits under its title. Table 1 shares its page
    # with the "Tables" heading, which carries the break instead.
    BR = '<w:r><w:rPr><w:sz w:val="2"/><w:szCs w:val="2"/></w:rPr><w:br w:type="page"/></w:r>'
    TITLE_RPR = '<w:rPr><w:b/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr>'
    def title(m):
        runs = re.sub(r"<w:r>(?:<w:rPr>.*?</w:rPr>)?", f"<w:r>{TITLE_RPR}", m.group(2), flags=re.S)
        brk = "" if m.group(4) == "1" else BR
        return (f'<w:p><w:pPr><w:pStyle w:val="Heading3" /><w:spacing w:before="0" w:after="120" w:line="240" '
                f'w:lineRule="auto"/></w:pPr>{brk}{runs}')
    xml, n = re.subn(r'(<w:p><w:pPr><w:pStyle w:val="Heading3" /></w:pPr>)((<w:r><w:t xml:space="preserve">Table (\d+)\.).*?)(?=</w:p>)',
                     title, xml, flags=re.S)
    if n:
        xml, k = re.subn(r'<w:p><w:pPr><w:pStyle w:val="Heading2" /></w:pPr>(<w:r><w:t xml:space="preserve">Tables</w:t></w:r>)',
                         rf'<w:p><w:pPr><w:pStyle w:val="Heading2" /></w:pPr>{BR}\1', xml)
        assert k == 1, "Tables heading not found"
    return xml


x = _tables(x)

# Diagnostic and Prognostic Research (4 Oct 2026): double line spacing, continuous line numbers, page numbers.
FOOTER = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
          '<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
          '<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r>'
          '<w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>')
RID = "rIdPageFooter"
x = re.sub(r"<w:sectPr>", f'<w:sectPr><w:footerReference w:type="default" r:id="{RID}"/>', x, count=1)
x = re.sub(r"(<w:sectPr>.*?)(</w:sectPr>)", r'\1<w:lnNumType w:countBy="1" w:restart="continuous"/>\2', x, count=1, flags=re.S)
if 'xmlns:r=' not in x[:2000]:
    x = x.replace("<w:document ", '<w:document xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" ', 1)
rels = zin.read("word/_rels/document.xml.rels").decode("utf-8").replace(
    "</Relationships>", f'<Relationship Id="{RID}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer_page.xml"/></Relationships>')
ctypes = zin.read("[Content_Types].xml").decode("utf-8").replace(
    "</Types>", '<Override PartName="/word/footer_page.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>')
styles = zin.read("word/styles.xml").decode("utf-8")
def _double(ppr):
    """Set double spacing in a <w:pPr> block, keeping any spacing-after it already has; one <w:spacing> only."""
    m = re.search(r"<w:spacing ([^>]*)/>", ppr)
    attrs = re.sub(r'\s*w:line(Rule)?="[^"]*"', "", m.group(1)) if m else ""
    new = f'<w:spacing {attrs.strip()} w:line="480" w:lineRule="auto"/>'.replace("  ", " ")
    return ppr.replace(m.group(0), new, 1) if m else ppr.replace("<w:pPr>", "<w:pPr>" + new, 1)


styles = re.sub(r"(<w:pPrDefault>\s*)(<w:pPr>.*?</w:pPr>)", lambda m: m.group(1) + _double(m.group(2)), styles, count=1, flags=re.S)
# tables (pandoc's "Compact" style) stay single-spaced so that they remain readable
styles = re.sub(r'(<w:style [^>]*w:styleId="Compact"[^>]*>(?:(?!</w:style>).)*?<w:pPr>)(.*?</w:pPr>)',
                lambda m: m.group(1) + re.sub(r"<w:spacing ([^>]*)/>", lambda n: "<w:spacing " + re.sub(r'\s*w:line(Rule)?="[^"]*"', "", n.group(1)) + ' w:line="240" w:lineRule="auto"/>', m.group(2), count=1),
                styles, count=1, flags=re.S)
for sid in ("BodyText",):   # prose paragraphs: no extra space between double-spaced paragraphs
    styles = re.sub(rf'(<w:style [^>]*w:styleId="{sid}"[^>]*>(?:(?!</w:style>).)*?)(<w:pPr>)(.*?</w:pPr>)',
                    lambda m: m.group(1) + m.group(2) + re.sub(r"<w:spacing [^>]*/>", "", m.group(3)).replace("</w:pPr>", '<w:spacing w:before="0" w:after="240" w:line="480" w:lineRule="auto"/></w:pPr>', 1),
                    styles, count=1, flags=re.S)
with zipfile.ZipFile(dst + ".tmp", "w", zipfile.ZIP_DEFLATED) as zout:
    for it in zin.infolist():
        data = {"word/document.xml": x, "word/_rels/document.xml.rels": rels, "[Content_Types].xml": ctypes,
                "word/styles.xml": styles}.get(it.filename)
        zout.writestr(it, data.encode("utf-8") if data is not None else zin.read(it.filename))
    zout.writestr("word/footer_page.xml", FOOTER)
zin.close()
shutil.move(dst + ".tmp", dst)
text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", x))
print(f"{os.path.basename(dst)}: tables {len(re.findall(r'<w:tbl>', x))}, [CHECK] {text.count('[CHECK')}, "
      f"pipes outside tables {''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', re.sub(r'<w:tbl>.*?</w:tbl>', '', x, flags=re.S))).count('|')}")
