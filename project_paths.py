"""Where the raw databases live, read from data_paths.cfg in the project root.

The scripts in 03_code/ and 08_paper3_multimodal/ each carried the path of the
drive the analysis was first run on. When the data moved, every one of them broke.
They now take the path from here, and here takes it from one file:

    data_paths.cfg

Edit that file when the data moves; nothing else needs to change. This module only
says where the data is. It does not check that the directories exist, so a script
that can run from its own saved inputs still can when the raw data is not attached.
"""
import configparser
from pathlib import Path

CFG = Path(__file__).resolve().parent / "data_paths.cfg"

_cfg = configparser.ConfigParser()
if not _cfg.read(CFG, encoding="utf-8") or "paths" not in _cfg:
    raise SystemExit(f"\n找不到数据路径配置文件，或其中没有 [paths] 一节：\n  {CFG}\n")


def _path(key):
    try:
        return str(Path(_cfg["paths"][key]).expanduser())
    except KeyError:
        raise SystemExit(f"\n{CFG} 的 [paths] 里缺少 {key} 这一项。\n")


MIMIC_VMAC = _path("mimic_vmac")   # MIMIC v_mac 文件夹
MIMIC_IV = _path("mimic_iv")       # MIMIC-IV 3.1，含 hosp/ 和 icu/
MIMIC_NOTE = _path("mimic_note")   # MIMIC-IV-Note 文本报告
EICU = _path("eicu")               # eICU-CRD 2.0
