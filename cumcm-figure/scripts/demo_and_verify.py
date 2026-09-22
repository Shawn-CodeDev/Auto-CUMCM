"""端到端验证 cumcm-figure skill：风格层 + 真实出图 + 终检器。

生成 4 张覆盖国赛典型图型的图，然后用 figure_check.py 检查它们，
确认（a）风格层可用（b）导出成对产出矢量+位图（c）终检器能发现注入的问题。
产物写到 skills/cumcm-figure/_demo/ ，跑完保留供人工目视。
"""
from __future__ import annotations

import os
import subprocess
import sys
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from cumcm_style import (  # noqa: E402
    CM, PALETTE, add_stat_box, annotate_extremum, apply_cumcm_style,
    convergence_plot, panel_label, save_cumcm_figure, tornado_chart,
)

import numpy as np  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "_demo")


def fig_result_compare():
    """原型 quantitative-grid：主结果对比（含基线）。"""
    fig, ax = plt.subplots(figsize=(CM.single_column, 6.0 * CM.cm))
    methods = ["基线 LP", "随机策略", "本文 MIP"]
    cost = [41200, 43800, 38650]
    colors = [PALETTE["neutral"][1], PALETTE["neutral"][2], PALETTE["signal"][0]]
    bars = ax.bar(methods, cost, color=colors, edgecolor="black", linewidth=0.5, width=0.6)
    bars[2].set_color(PALETTE["accent"][0])
    for b, v in zip(bars, cost):
        ax.text(b.get_x() + b.get_width() / 2, v + 300, f"{v}",
                ha="center", va="bottom", fontsize=8)
    ax.set_ylabel("日运行成本（元）")
    ax.set_ylim(36000, 45500)
    ax.annotate("较基线降低 6.2%", xy=(2, 38650), xytext=(0.35, 0.82),
                textcoords="axes fraction", fontsize=8, color=PALETTE["accent"][0],
                arrowprops={"arrowstyle": "->", "color": PALETTE["accent"][0], "lw": 0.8})
    add_stat_box(ax, "n = 24 时段；误差棒为标准差（5 次重复）")
    save_cumcm_figure(fig, os.path.join(OUT, "E03_result_compare"))


def fig_multipanel():
    """原型 robustness-panel：通栏三面板（结果 + 灵敏度 + 收敛）。"""
    fig, axes = plt.subplots(1, 3, figsize=(CM.double_column, 5.2 * CM.cm))

    # (a) 负荷曲线
    t = np.arange(24)
    load = 6000 + 1800 * np.sin((t - 6) * np.pi / 12) ** 2
    axes[0].plot(t, load, color=PALETTE["signal"][0], marker="o", markersize=3)
    axes[0].set_xlabel("时段（h）")
    axes[0].set_ylabel("负荷（kWh）")
    axes[0].set_title("日负荷曲线")
    panel_label(axes[0], "a")

    # (b) 灵敏度曲线
    deltas = np.array([-20, -10, -5, 0, 5, 10, 20])
    cost_chg = np.array([-6.5, -3.2, -1.6, 0, 1.6, 3.1, 6.4])
    axes[1].plot(deltas, cost_chg, color=PALETTE["accent"][0], marker="s", markersize=3.5)
    axes[1].axhline(0, color=PALETTE["neutral"][0], lw=0.8)
    axes[1].set_xlabel("效率 η 变化（%）")
    axes[1].set_ylabel("成本变化（%）")
    axes[1].set_title("效率灵敏度")
    panel_label(axes[1], "b")

    # (c) 收敛曲线
    rng = np.random.default_rng(42)
    hist = 45000 - 6000 * (1 - np.exp(-np.arange(120) / 25)) + rng.normal(0, 40, 120)
    convergence_plot(hist, ax=axes[2], xlabel="迭代次数", ylabel="目标函数值", label="本文 MIP")
    axes[2].set_title("算法收敛过程")
    panel_label(axes[2], "c")

    fig.tight_layout(w_pad=1.6)
    save_cumcm_figure(fig, os.path.join(OUT, "E04_multipanel"), also_svg=True)


def fig_tornado():
    """原型 robustness-panel：龙卷风图（灵敏度分析的标准呈现）。"""
    fig, ax = plt.subplots(figsize=(CM.single_column, 6.0 * CM.cm))
    labels = ["电价峰谷比", "储能效率 η", "储能容量", "寿命损耗系数 λ"]
    lows = np.array([-17.4, -6.5, -2.3, -1.1])
    highs = np.array([18.2, 6.4, 2.1, 1.1])
    tornado_chart(labels, lows, highs, ax=ax)
    ax.set_title("关键参数灵敏度（±20%）")
    save_cumcm_figure(fig, os.path.join(OUT, "E05_tornado"))


def fig_heatmap():
    """原型 spatial-mechanism：热力图（有序数据，用 viridis 而非彩虹）。"""
    fig, ax = plt.subplots(figsize=(CM.single_column, 6.5 * CM.cm))
    rng = np.random.default_rng(7)
    data = np.abs(rng.normal(size=(8, 24)).cumsum(axis=1)) * 100
    im = ax.imshow(data, aspect="auto", cmap=PALETTE["sequential"], origin="lower")
    ax.set_xlabel("时段（h）")
    ax.set_ylabel("节点编号")
    ax.set_title("节点负荷热力图")
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("负荷（kWh）", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    save_cumcm_figure(fig, os.path.join(OUT, "E06_heatmap"))


def poison_one():
    """故意注入问题：文件名含校名 + 造一张几乎空白的图，验证终检器能发现。"""
    bad_dir = os.path.join(OUT, "_poison")
    os.makedirs(bad_dir, exist_ok=True)
    fig, ax = plt.subplots(figsize=(CM.single_column, 3 * CM.cm))
    ax.set_xlabel("参赛大学 张三 学号 2026001")   # 身份信息注入
    ax.plot([0, 1], [0, 1])
    save_cumcm_figure(fig, os.path.join(bad_dir, "E99_参赛大学泄露"), verbose=False)

    # 空图（只有坐标轴，没画数据）——必须触发导出期告警
    fig2, ax2 = plt.subplots(figsize=(CM.single_column, 3 * CM.cm))
    ax2.set_xlabel("空图")   # 不调用 plot，只留坐标轴
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        save_cumcm_figure(fig2, os.path.join(bad_dir, "noindex_empty"), verbose=False)
        empty_warned = any("未检测到任何数据元素" in str(x.message) for x in w)
    return empty_warned


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    info = apply_cumcm_style()
    print("风格层生效:", info["cjk_fonts_used"])
    os.makedirs(OUT, exist_ok=True)

    fig_result_compare()
    fig_multipanel()
    fig_tornado()
    fig_heatmap()
    print(f"\n已生成 4 张图的演示产物到 {OUT}")

    print("\n--- 检查干净的图 ---")
    r1 = subprocess.run([sys.executable, os.path.join(HERE, "figure_check.py"),
                         "--dir", OUT, "--quiet"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    print((r1.stdout or "")[-1500:])

    empty_warned = poison_one()
    print("\n--- 注入问题后检查 ---")
    r2 = subprocess.run([sys.executable, os.path.join(HERE, "figure_check.py"),
                         "--dir", os.path.join(OUT, "_poison"), "--quiet"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (r2.stdout or "")[-1500:]
    print(tail)

    caught_identity = "身份" in tail or "校名" in tail or "大学" in tail
    caught = r2.returncode != 0
    print(f"\n终检器抓到注入问题: {caught}（身份信息: {caught_identity}）")
    print(f"导出期空图告警触发: {empty_warned}")
    failed = False
    if not caught:
        print("!! 终检器未能抓到注入的身份信息，QA 契约形同虚设")
        failed = True
    if not empty_warned:
        print("!! 导出期未对空图告警，空图防护失效")
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
