"""
Shared by 57 and 67: give every table in a pandoc-built .docx explicit column widths, rules and padding.

pandoc writes tables with auto width and narrow grid columns, which several renderers lay out by content,
so adjacent numeric columns run together. Here each column's width is allocated from the longest cell
text in that column (East Asian characters count double), the table is fixed at the text width, and
top/bottom rules with light row separators and cell padding are written as direct formatting.
"""
import re
import unicodedata

TEXT_WIDTH_DXA = 9000        # A4/Letter text block with ~1-inch margins
MIN_SHARE = 0.08
GUTTER = 5


def _display_len(s):
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in s)


def _cell_text(tc):
    paras = re.findall(r"<w:p[ >].*?</w:p>", tc, flags=re.S)
    return max((_display_len("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))) for p in paras), default=0)


PROPS = ('<w:tblBorders><w:top w:val="single" w:sz="8" w:space="0" w:color="52514E"/>'
         '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="52514E"/>'
         '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="D6D5D0"/></w:tblBorders>'
         '<w:tblLayout w:type="fixed"/>'
         '<w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="100" w:type="dxa"/>'
         '<w:bottom w:w="40" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tblCellMar>')


def _one_table(tbl):
    rows = re.findall(r"<w:tr[ >].*?</w:tr>", tbl, flags=re.S)
    grid = [re.findall(r"<w:tc>.*?</w:tc>", r, flags=re.S) for r in rows]
    ncol = max(len(g) for g in grid)
    longest = [0] * ncol
    for g in grid:
        for j, tc in enumerate(g):
            longest[j] = max(longest[j], min(_cell_text(tc), 60))   # very long cells wrap
    raw = [max(l, 4) + GUTTER for l in longest]          # a fixed gutter, since some renderers ignore cell padding
    share = [max(r / sum(raw), MIN_SHARE) for r in raw]
    widths = [int(TEXT_WIDTH_DXA * s / sum(share)) for s in share]

    tbl = re.sub(r"<w:tblGrid>.*?</w:tblGrid>",
                 "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths) + "</w:tblGrid>", tbl, flags=re.S)

    def tblpr(m):
        # CT_TblPr children must follow the schema order; rebuild the block rather than splice into it
        body = m.group(0)[len("<w:tblPr>"):-len("</w:tblPr>")]
        style = re.search(r"<w:tblStyle [^>]*/>", body)
        look = re.search(r"<w:tblLook [^>]*/>", body)
        return ("<w:tblPr>" + (style.group(0) if style else "") + f'<w:tblW w:w="{sum(widths)}" w:type="dxa"/>'
                + PROPS + (look.group(0) if look else "") + "</w:tblPr>")
    tbl = re.sub(r"<w:tblPr>.*?</w:tblPr>", tblpr, tbl, count=1, flags=re.S)

    def row(rm):
        j = [0]
        def cell(cm):
            tc = cm.group(0)
            w = widths[min(j[0], ncol - 1)]; j[0] += 1
            tc = re.sub(r"<w:tcW [^>]*/>", "", tc)
            tcw = f'<w:tcW w:w="{w}" w:type="dxa"/>'
            # pandoc writes an empty self-closing <w:tcPr />; tcPr must stay the single first child of w:tc
            if re.search(r"<w:tcPr\s*/>", tc):
                return re.sub(r"<w:tcPr\s*/>", f"<w:tcPr>{tcw}</w:tcPr>", tc, count=1)
            if "<w:tcPr>" in tc:
                return tc.replace("<w:tcPr>", f"<w:tcPr>{tcw}", 1)
            return tc.replace("<w:tc>", f"<w:tc><w:tcPr>{tcw}</w:tcPr>", 1)
        return re.sub(r"<w:tc>.*?</w:tc>", cell, rm.group(0), flags=re.S)
    return re.sub(r"<w:tr[ >].*?</w:tr>", row, tbl, flags=re.S)


def format_tables(document_xml):
    return re.sub(r"<w:tbl>.*?</w:tbl>", lambda m: _one_table(m.group(0)), document_xml, flags=re.S)
