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
