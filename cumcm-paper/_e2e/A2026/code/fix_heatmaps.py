"""修复 E05/E10 的两个时空热力图：矢量 PDF 体积超预算（3.7–4.2 MB）。

原因：pcolormesh 把 12871×201 个四边形全部写进 PDF，矢量文件被撑爆。
虽然它能通过（不是硬错误），但两张图就吃掉论文 20 MB 配额的近 40%，
属于必须修的质量缺陷（figure_check.py 已给出提醒）。

修法：
  1. 画图前把时间维**降到 ~200 个切片**（视觉上无差别）；
  2. 用 rasterized=True 让 pcolormesh 以位图方式嵌入，轴线/文字仍保持矢量；
  3. 重绘后复检体积。
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.dirname(HERE)


def _root(start):
    cur = start
    for _ in range(8):
        if os.path.isdir(os.path.join(cur, "skills")):
            return cur
        nxt = os.path.dirname(cur)
        if nxt == cur:
            break
        cur = nxt
    return start


ROOT = _root(HERE)
sys.path.insert(0, os.path.join(ROOT, "skills", "cumcm-figure", "scripts"))
from cumcm_style import CM, PALETTE, apply_cumcm_style, panel_label, save_cumcm_figure  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RES = os.path.join(WORK, "results")
FIGS = os.path.join(WORK, "figures")

apply_cumcm_style(base_size=9)

O2 = np.load(os.path.join(RES, "E10_p234.npz"))
t = O2["t"] / 3600.0
xi = O2["xi"]
R0 = O2["R_t"][0]
rr = xi * R0 * 100.0
C = O2["C"]
T = O2["T"]

# 时间维降采样到 ~200 片：热力图在 15 cm 宽、5 cm 高的版面上分辨不出更细的切片
NT = 200
idx = np.linspace(0, len(t) - 1, NT).astype(int)


def render(fname: str, st: int) -> None:
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(CM.double_column, 5.6 * CM.cm))
    im = axes[0].pcolormesh(t[idx], rr, C[:, idx], cmap=PALETTE["sequential"],
                            shading="auto", rasterized=True)
    cb = fig.colorbar(im, ax=axes[0], pad=0.02)
    cb.set_label("水分浓度（kg/kg）", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    axes[0].set_xlabel("时间（h）")
    axes[0].set_ylabel("到药材中心的距离（cm）")
    axes[0].set_title("水分浓度时空演化")
    panel_label(axes[0], "a")

    im = axes[1].pcolormesh(t[idx], rr, T[:, idx], cmap="inferno",
                            shading="auto", rasterized=True)
    cb = fig.colorbar(im, ax=axes[1], pad=0.02)
    cb.set_label("温度（°C）", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    axes[1].set_xlabel("时间（h）")
    axes[1].set_ylabel("到药材中心的距离（cm）")
    axes[1].set_title("温度时空演化")
    panel_label(axes[1], "b")
    fig.tight_layout(w_pad=1.6)
    save_cumcm_figure(fig, os.path.join(FIGS, fname), raster_dpi=200)


# cumcm_style.save_cumcm_figure 暂不支持 raster_dpi 参数时，退化为手工导出
try:
    render("E10_p2_fields", 0)
except TypeError:
    import matplotlib.pyplot as plt

    def render2(fname: str) -> None:
        fig, axes = plt.subplots(1, 2, figsize=(CM.double_column, 5.6 * CM.cm))
        im = axes[0].pcolormesh(t[idx], rr, C[:, idx], cmap=PALETTE["sequential"],
                                shading="auto", rasterized=True)
        cb = fig.colorbar(im, ax=axes[0], pad=0.02)
        cb.set_label("水分浓度（kg/kg）", fontsize=8)
        axes[0].set_xlabel("时间（h）")
        axes[0].set_ylabel("到药材中心的距离（cm）")
        axes[0].set_title("水分浓度时空演化")
        panel_label(axes[0], "a")
        im = axes[1].pcolormesh(t[idx], rr, T[:, idx], cmap="inferno",
                                shading="auto", rasterized=True)
        cb = fig.colorbar(im, ax=axes[1], pad=0.02)
        cb.set_label("温度（°C）", fontsize=8)
        axes[1].set_xlabel("时间（h）")
        axes[1].set_ylabel("到药材中心的距离（cm）")
        axes[1].set_title("温度时空演化")
        panel_label(axes[1], "b")
        fig.tight_layout(w_pad=1.6)
        out = os.path.join(FIGS, fname)
        # rasterized=True 时，用 dpi 控制内嵌位图分辨率
        fig.savefig(out + ".pdf", bbox_inches="tight", pad_inches=0.02)
        fig.savefig(out + ".png", dpi=600, bbox_inches="tight", pad_inches=0.02)
        plt.close(fig)
        print(f"[figure] {fname} -> pdf={os.path.getsize(out+'.pdf')/1024:.0f}KB"
              f", png={os.path.getsize(out+'.png')/1024:.0f}KB")

    render2("E10_p2_fields")

print(f"time slices: {len(t)} -> {NT}")
