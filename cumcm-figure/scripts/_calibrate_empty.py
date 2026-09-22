"""校准近空图检测阈值：对比"有数据"与"只有坐标轴"的 PDF 内容流大小与绘制算子数。"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cumcm_style import CM, apply_cumcm_style, save_cumcm_figure

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

try:
    import pymupdf as fitz
except Exception:
    import fitz

D = os.path.join(os.path.dirname(HERE), "_calib")
os.makedirs(D, exist_ok=True)
apply_cumcm_style()

# 三种情形：无数据（仅坐标轴）、少量数据（10 点）、典型数据（200 点）
cases = {
    "empty": None,
    "small": 10,
    "normal": 200,
}
for name, n in cases.items():
    fig, ax = plt.subplots(figsize=(CM.single_column, 5 * CM.cm))
    if n:
        x = np.linspace(0, 10, n)
        ax.plot(x, np.sin(x), marker="o" if n <= 10 else None, markersize=3)
        ax.set_xlabel("时间（小时）")
        ax.set_ylabel("数值")
    else:
        ax.set_xlabel("空图")
    save_cumcm_figure(fig, os.path.join(D, name), verbose=False)

OPS = re.compile(rb"(?m)^\s*(?:[\d\.\-\s]+)?(?:m|l|re|c|h|f|S|s|B|b|W)\s*$")
for name in cases:
    p = os.path.join(D, name + ".pdf")
    doc = fitz.open(p)
    total = 0
    ops = 0
    for page in doc:
        for xref in page.get_contents():
            data = doc.xref_stream(xref) or b""
            total += len(data)
            ops += len(OPS.findall(data))
    imgs = sum(len(pg.get_images(full=True)) for pg in doc)
    doc.close()
    print(f"{name:>8}: stream={total:>7} B   path_ops={ops:>6}  images={imgs}")
