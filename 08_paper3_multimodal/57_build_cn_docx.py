"""
Paper 3: build the Chinese manuscript .docx from its Markdown source.

pandoc with a reference document whose styles set SimSun/Times New Roman for body text and
SimHei/Arial for headings; then every text run gets w:rFonts w:hint="eastAsia", so characters shared
by Chinese and Western text (quotation marks, dashes) render full-width in the Chinese font.

Usage: python 57_build_cn_docx.py paper3_draft_v5_CN.md
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import re
import shutil
import subprocess
import sys
import xml.dom.minidom
import zipfile
from pathlib import Path

M = _REPO_ROOT + "/08_paper3_multimodal/manuscript"
REF = f"{M}/templates/reference_cn.docx"   # pandoc default reference.docx with Chinese fonts set in styles.xml


def pandoc():
    """pandoc may not be on PATH in every shell (Homebrew installs it outside the system path)."""
    import os
    found = shutil.which("pandoc")
    for candidate in [found, "/opt/homebrew/bin/pandoc", "/usr/local/bin/pandoc"]:
        if candidate and os.path.exists(candidate):
            return candidate
    sys.exit("pandoc not found: install it (brew install pandoc) or add it to PATH")


sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from docx_tables import format_tables  # noqa: E402


def main(src):
    dst = f"{M}/{src.rsplit('.', 1)[0]}.docx"
    md = open(f"{M}/{src}", encoding="utf-8").read()
    assert '"' not in md[md.index("\n---\n", 4) + 5:], "straight double quotes in the Chinese body"
    assert Path(REF).exists(), f"reference document missing: {REF}"
    subprocess.run([pandoc(), f"{M}/{src}", "--from", "markdown", "--to", "docx",
                    "--reference-doc", REF, "-o", dst], check=True)
    zin = zipfile.ZipFile(dst)
    x = zin.read("word/document.xml").decode("utf-8")
    x = re.sub(r"<w:r><w:rPr>(?!<w:rFonts)", '<w:r><w:rPr><w:rFonts w:hint="eastAsia"/>', x)
    x = re.sub(r"<w:r>(?=<w:(t|tab|br)[ >/])", '<w:r><w:rPr><w:rFonts w:hint="eastAsia"/></w:rPr>', x)
    x = format_tables(x)
    xml.dom.minidom.parseString(x.encode("utf-8"))
    tmp = dst + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            zout.writestr(item, x.encode("utf-8") if item.filename == "word/document.xml" else zin.read(item.filename))
    zin.close()
    shutil.move(tmp, dst)
    text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", x))
    print(f"{dst.rsplit('/', 1)[1]}: tables {len(re.findall(r'<w:tbl>', x))}, "
          f"runs hinted {x.count('w:hint=')}, [CHECK] {text.count('[CHECK')}, straight quotes {text.count(chr(34))}")


if __name__ == "__main__":
    main(sys.argv[1])
