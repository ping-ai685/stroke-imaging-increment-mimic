"""
Paper 3: rebuild the manuscript artefacts and run every check, in order. A manuscript is not called
ready unless this exits 0.

  53  numbers.json from the data          56  English draft from its source (citations numbered)
  57  Chinese .docx from its source       58  every number traced to a source
  59  every table cell against its key    60  prose claims, methods-as-implemented, wording boundaries
  61  citations (add --offline to skip the live registry lookup)

It does not clear [CHECK] items: those are decisions for the study lead and are listed at the end.
"""
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
offline = ["--offline"] if "--offline" in sys.argv else []
STEPS = [
    ("53 numbers manifest", ["53_manuscript_numbers.py"]),
    ("51 Figures 2–3", ["51_dca_calibration.py"]),
    ("64 Figures 1 and 4", ["64_figures_design_redundancy.py"]),
    ("56 English draft", ["56_number_citations.py", "paper3_draft_v5_src.md", "paper3_draft_v5.md"]),
    ("57 Chinese docx", ["57_build_cn_docx.py", "paper3_draft_v5_CN.md"]),
    ("65 supplement", ["65_build_supplement.py"]),
    ("67 English docx", ["67_build_en_docx.py", "paper3_draft_v5.md"]),
    ("67 supplement docx EN", ["67_build_en_docx.py", "supplement_v1.md"]),
    ("57 supplement docx CN", ["57_build_cn_docx.py", "supplement_v1_CN.md"]),
    ("68 TRIPOD+AI checklist", ["68_build_tripod_checklist.py"]),
    ("67 Additional file 2 docx", ["67_build_en_docx.py", "additional_file_2_tripod_ai.md"]),
    ("58 number tracing", ["58_trace_every_number.py"]),
    ("59 table cells", ["59_verify_tables.py"]),
    ("60 prose claims", ["60_verify_prose_claims.py"]),
    ("61 citations", ["61_verify_citations.py"] + offline),
]
failed = []
for name, cmd in STEPS:
    r = subprocess.run([sys.executable, str(HERE / cmd[0])] + cmd[1:], capture_output=True, text=True, cwd=HERE)
    last = (r.stdout.strip().splitlines() or [""])[-1]
    print(f"  {'OK ' if r.returncode == 0 else 'BAD'}  {name:22s} {last[:90]}")
    if r.returncode != 0:
        failed.append(name)
        print("\n".join("        " + l for l in (r.stdout + r.stderr).splitlines() if re.search(r"BAD|UNTRACED|Error|assert", l))[:3000])
en = (HERE / "manuscript" / "paper3_draft_v5.md").read_text(encoding="utf-8")
body = re.sub(r"<!--.*?-->", "", en, flags=re.S)
checks = re.findall(r"\[CHECK:? ?([^\]]*)\]", body)
print(f"\n[CHECK] items still open in the English draft ({len(checks)}):")
for c in checks:
    print("   -", c or "(unlabelled)")
print("\nALL CHECKS PASSED" if not failed else f"\nFAILED: {failed}")
sys.exit(1 if failed else 0)
