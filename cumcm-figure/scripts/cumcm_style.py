"""国赛论文配图统一风格层。

解决的问题（每个队伍都会踩）：
  1. matplotlib 默认不含中文字体 → 中文全变方块
  2. 坐标轴负号显示为方块（U+2212 缺字形）
  3. 每个脚本各写一套 rcParams → 论文里图与图之间字体/字号/线宽不一致
  4. 导出尺寸与 LaTeX \\linewidth 不匹配 → 插图后被拉伸糊字
  5. 忘记导出矢量版本 → 放大后锯齿

用法（在绘图脚本顶部）：
    import sys; sys.path.insert(0, r"<repo>/skills/cumcm-figure/scripts")
    from cumcm_style import (apply_cumcm_style, save_cumcm_figure,
                             PALETTE, panel_label, CM, add_stat_box)

    apply_cumcm_style()
    fig, ax = plt.subplots(figsize=(CM.single_column, 6*CM.cm))   # 单位统一用厘米
    ...
    save_cumcm_figure(fig, "results/figures/E04_sensitivity")

命令行自检（不需要画图）：
    python cumcm_style.py            # 打印本机可用中文字体与当前生效配置
"""
from __future__ import annotations

import os
import sys
import warnings

import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager

# 中文字体常以 CID/OTF 形式存在，TrueType 子集化时会打印
# "MERG NOT subset; don't know how to subset; dropped" —— 这是无害信息，
# 但会淹没有用输出，因此在导入期就静音这一类字体子集告警。
warnings.filterwarnings(
    "ignore",
    message=r".*NOT subset.*",
    category=UserWarning,
)
try:  # matplotlib 把这类消息走 logging，不只是 warnings
    import logging
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
except Exception:  # noqa: BLE001
    pass


# --------------------------------------------------------------------------- #
# 物理尺寸：国赛排版以厘米为准，图尺寸与 \linewidth 对齐才不会被拉伸
# --------------------------------------------------------------------------- #
class CM:
    """厘米 ↔ 英寸；以及与本仓库 LaTeX 模板对齐的图宽常量。

    宽度依据（不要凭常识猜，这里是算出来的）：
      cumcmthesis.cls 设置 \\geometry{left=25mm,right=25mm}，A4 纸宽 21cm，
      故正文行宽 \\textwidth = 21 - 2.5 - 2.5 = **16cm**（不是 17cm）。
      插图时写 width=\\linewidth 会自动取 16cm；
      若按 17cm 出图再缩到 \\linewidth，会被压缩 5.9%，字号随之变小——
      所以这里的 double_column 用真实的 16cm。
    """

    cm = 1.0 / 2.54

    # 与 cumcmthesis 模板 / A4 正文宽度对应的常用尺寸（英寸）
    double_column = 16.0 * cm     # 通栏图 = \textwidth（模板实测 16cm）
    single_column = 8.0 * cm      # 单栏图（正文宽度的一半，留出并排间距）
    one_third = 5.0 * cm          # 三子图之一
    half_page = 12.0 * cm         # 半页宽（介于单栏与通栏之间）


# --------------------------------------------------------------------------- #
# 配色：低调、灰度可读、避开纯红绿对立
# --------------------------------------------------------------------------- #
PALETTE = {
    # 中性家族（背景、次要、基线）
    "neutral": ["#4D4D4D", "#8C8C8C", "#BFBFBF", "#E6E6E6"],
    # 信号家族（主结果、主要方法）
    "signal": ["#2E5C8A", "#4B8BBE", "#7FB3D5", "#A9CCE3"],
    # 强调家族（最优解、改进、关键点）
    "accent": ["#C0392B", "#E67E22", "#D4AC0D", "#1E8449"],
    # 多方法对比（最多 6 类，色相分隔但饱和度接近）
    "compare": ["#2E5C8A", "#C0392B", "#1E8449", "#D4AC0D",
                "#7D3C98", "#17A589"],
    # 有序/连续
    "sequential": "viridis",
    "diverging": "RdBu_r",
}

# 中文正文字体优先级：Windows 常见 → 开源 → 兜底
CJK_CANDIDATES = [
    "Microsoft YaHei", "SimHei", "Source Han Sans SC", "Noto Sans CJK SC",
    "WenQuanYi Zen Hei", "PingFang SC", "Hiragino Sans GB", "Arial Unicode MS",
]
LATIN_CANDIDATES = ["Arial", "Helvetica", "DejaVu Sans"]


def available_cjk_fonts() -> list[str]:
    """返回本机真正可用（有字形）的中文字体名。"""
    installed = {f.name for f in font_manager.fontManager.ttflist}
    return [f for f in CJK_CANDIDATES if f in installed]


def apply_cumcm_style(base_size: float = 9, *, usetex: bool = False) -> dict:
    """应用国赛统一风格。返回实际生效的配置摘要（便于写进日志/自检）。

    base_size 以"最终印刷尺寸下的字号"为准。国赛正文 12pt 时，
    图内文字 8–10pt 是安全区间；不要用 matplotlib 默认的 10pt 又缩放到 60%。
    """
    cjk = available_cjk_fonts()
    if not cjk:
        warnings.warn(
            "未找到中文字体，中文将显示为方块。请安装 Microsoft YaHei / SimHei / "
            "Source Han Sans SC 之一，或在 apply_cumcm_style(cjk_font=...) 指定字体文件。",
            RuntimeWarning, stacklevel=2,
        )

    matplotlib.rcParams.update({
        # ---- 字体：中文优先，拉丁回退 ----
        "font.family": "sans-serif",
        "font.sans-serif": cjk + LATIN_CANDIDATES,
        "font.size": base_size,
        # 负号：Unicode 减号在中文字体里常常缺字形，强制用 ASCII hyphen
        "axes.unicode_minus": False,

        # ---- 版面：去上/右边框，细线，无网格底色 ----
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.8,
        "axes.titlesize": base_size + 1,
        "axes.labelsize": base_size,
        "axes.labelpad": 2.5,
        "axes.grid": False,
        "axes.axisbelow": True,

        # ---- 刻度 ----
        "xtick.labelsize": base_size - 1,
        "ytick.labelsize": base_size - 1,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "xtick.direction": "out",
        "ytick.direction": "out",

        # ---- 图例：无框，紧凑 ----
        "legend.frameon": False,
        "legend.fontsize": base_size - 1,
        "legend.handlelength": 1.6,
        "legend.handletextpad": 0.5,
        "legend.columnspacing": 1.0,
        "legend.borderaxespad": 0.3,

        # ---- 线型与标记 ----
        "lines.linewidth": 1.4,
        "lines.markersize": 4.0,
        "lines.solid_capstyle": "round",
        "patch.linewidth": 0.6,

        # ---- 图像 ----
        "figure.dpi": 120,             # 屏幕预览
        "savefig.dpi": 600,            # 导出位图
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,

        # ---- 字体嵌入：保证 PDF 里文字可选中、可编辑 ----
        "pdf.fonttype": 42,            # TrueType 子集嵌入
        "ps.fonttype": 42,
        "svg.fonttype": "none",        # SVG 保留文本（便于后期微调）

        "text.usetex": usetex,
    })
    return {
        "base_size": base_size,
        "cjk_fonts_used": cjk or ["<none: 中文会乱码>"],
        "latin_fallback": LATIN_CANDIDATES,
        "single_column_cm": round(CM.single_column / CM.cm, 2),
        "double_column_cm": round(CM.double_column / CM.cm, 2),
        "usetex": usetex,
    }


# --------------------------------------------------------------------------- #
# 导出：一次调用同时产出矢量与位图，并做基础自检
# --------------------------------------------------------------------------- #
def _quiet_native_stderr():
    """在导出期间静音原生 fprintf(stderr) 噪声（字体子集告警等）。

    "MERG NOT subset" 由 FreeType 的 C 层直接写 stderr，Python 的 warnings /
    logging 拦不住它。它无害，但会淹没脚本输出，所以在导出窗口内临时把 fd 2
    重定向到空设备，结束后恢复。失败时静默降级（不影响导出本身）。
    """
    import contextlib
    import tempfile

    @contextlib.contextmanager
    def _ctx():
        try:
            sys.stderr.flush()
            saved = os.dup(2)
        except Exception:
            yield
            return
        try:
            with open(os.devnull, "w") as devnull:
                os.dup2(devnull.fileno(), 2)
                yield
        finally:
            try:
                os.dup2(saved, 2)
                os.close(saved)
            except Exception:
                pass
    return _ctx()


def count_drawn_artists(fig) -> dict:
    """统计每个坐标轴上真正承载数据的绘图元素数量。

    为什么需要这个：矢量 PDF 里"只有坐标轴"和"有 200 个数据点"的文件体积
    几乎一样（本机实测 2041B vs 4065B，路径算子 54 vs 137），
    靠文件大小或内容流长度都判不出空图，只能在绘图对象层面数。

    排除项很关键：Spine 是 Patch 的子类、ax.patch 是 Rectangle，
    它们都属于坐标轴装饰而非数据。若不排除，空图会被数成"有 2 个元素"。
    """
    from matplotlib.axes import Axes
    from matplotlib.spines import Spine

    DATA_TYPES = (
        matplotlib.lines.Line2D,            # plot / errorbar 的线
        matplotlib.image.AxesImage,         # imshow
        matplotlib.collections.Collection,  # scatter / contour / violin / quadmesh
        matplotlib.patches.Patch,           # bar / barh / fill_between / 自定义补丁
    )

    per_axes = []
    for ax in fig.get_axes():
        if not isinstance(ax, Axes):
            continue
        n = 0
        for a in ax.get_children():
            if not a.get_visible():
                continue
            if isinstance(a, matplotlib.spines.Spine):
                continue          # 四条边框是坐标轴装饰，Spine 是 Patch 子类
            if a is ax.patch:
                continue          # 坐标轴背景填充
            if isinstance(a, matplotlib.axis.Axis):
                continue          # 刻度轴容器
            if isinstance(a, DATA_TYPES):
                n += 1
        per_axes.append({"title": ax.get_title() or "", "artists": n,
                         "has_legend": ax.get_legend() is not None})
    return {"per_axes": per_axes, "total": sum(d["artists"] for d in per_axes)}


def save_cumcm_figure(fig, path_no_ext: str, *,
                      also_svg: bool = False,
                      min_bytes: int = 4000,
                      allow_empty: bool = False,
                      verbose: bool = True) -> dict:
    """导出论文用图。

    产出：
      <path>.pdf  矢量，插进 LaTeX（首选）
      <path>.png  600 dpi 位图，用于预览与支撑材料
      <path>.svg  可选，便于后期在 Illustrator/Inkscape 微调

    导出前统计绘图对象数量；整张图几乎没有数据元素时告警——
    "图能导出"和"图里有东西"是两件事，空图是最容易被漏掉的低级错误。
    确实要输出纯示意图（流程图/框图）时传 allow_empty=True。

    返回各文件字节数 + 绘图对象统计。
    """
    drawn = count_drawn_artists(fig)
    if drawn["total"] == 0 and not allow_empty:
        warnings.warn(
            f"{os.path.basename(path_no_ext)} 未检测到任何数据元素（只有坐标轴/文字）。"
            f"如果确实要输出纯示意图，请传 allow_empty=True。",
            RuntimeWarning, stacklevel=2,
        )

    os.makedirs(os.path.dirname(os.path.abspath(path_no_ext)) or ".", exist_ok=True)
    out: dict = {}

    with _quiet_native_stderr():
        fig.savefig(f"{path_no_ext}.pdf", bbox_inches="tight", pad_inches=0.02)
        out["pdf"] = os.path.getsize(f"{path_no_ext}.pdf")

        fig.savefig(f"{path_no_ext}.png", dpi=600, bbox_inches="tight", pad_inches=0.02)
        out["png"] = os.path.getsize(f"{path_no_ext}.png")

        if also_svg:
            fig.savefig(f"{path_no_ext}.svg", bbox_inches="tight", pad_inches=0.02)
            out["svg"] = os.path.getsize(f"{path_no_ext}.svg")

    plt.close(fig)

    if verbose:
        sizes = ", ".join(f"{k}={int(v)/1024:.0f}KB" for k, v in out.items()
                          if k != "drawn")
        print(f"[figure] {os.path.basename(path_no_ext)} -> {sizes}  "
              f"(数据元素 {drawn['total']})")

    if int(out.get("pdf", 0)) < min_bytes:
        warnings.warn(
            f"{path_no_ext}.pdf 只有 {out.get('pdf')} 字节，可能画布是空的或未绘制任何内容。",
            RuntimeWarning, stacklevel=2,
        )
    out["drawn"] = drawn
    return out


# --------------------------------------------------------------------------- #
# 面板标签：国赛组合图规范——小写字母，粗体，左上角
# --------------------------------------------------------------------------- #
def panel_label(ax, label: str, *, dx: float = -0.12, dy: float = 1.06,
                size: float | None = None, boxed: bool = False) -> None:
    """在坐标轴左上角加 (a)/(b)/(c) 面板标签。

    放在轴外（默认 dx=-0.12）避免遮挡数据；若左侧空间不足可改 dx=0.02。
    """
    txt = f"({label})" if not label.startswith("(") else label
    ax.text(dx, dy, txt, transform=ax.transAxes,
            fontsize=size or matplotlib.rcParams["font.size"] + 1,
            fontweight="bold", va="bottom", ha="left",
            bbox=({"facecolor": "white", "edgecolor": "none", "pad": 1.0}
                  if boxed else None))


def add_stat_box(ax, text: str, *, loc: str = "upper center") -> None:
    """在绘图区上方加一行无框统计条（n / 误差定义 / 检验结果）。

    国赛图注要求写明这些，但塞进图例会挤占数据区——放在轴上方居中是最省地的做法。
    """
    ax.set_title(text, fontsize=matplotlib.rcParams["font.size"] - 1,
                 loc="center", pad=4)


def annotate_extremum(ax, x, y, text: str, *, color: str | None = None,
                      xytext=(8, 8)) -> None:
    """标注极值点/最优点——国赛图里"最优解在哪"必须一眼可见。"""
    color = color or PALETTE["accent"][0]
    ax.plot([x], [y], marker="o", markersize=4.5, color=color, zorder=5)
    ax.annotate(text, xy=(x, y), xytext=xytext, textcoords="offset points",
                fontsize=matplotlib.rcParams["font.size"] - 1, color=color,
                arrowprops={"arrowstyle": "-", "color": color, "lw": 0.8})


# --------------------------------------------------------------------------- #
# 常用国赛图型的快捷构造（避免每次重复排版）
# --------------------------------------------------------------------------- #
def tornado_chart(labels, lows, highs, *, ax=None, title: str = "参数灵敏度",
                  xlabel: str = "目标值相对变化 (%)"):
    """龙卷风图：灵敏度分析的标准呈现。lows/highs 为百分比变化（可正可负）。"""
    import numpy as np
    if ax is None:
        _, ax = plt.subplots(figsize=(CM.single_column, 0.55 * len(labels) + 1.2))
    y = np.arange(len(labels))[::-1]
    ax.barh(y, np.asarray(highs) - np.asarray(lows),
            left=np.asarray(lows), height=0.55,
            color=PALETTE["signal"][1], edgecolor="black", linewidth=0.5)
    ax.axvline(0, color="#4D4D4D", lw=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel(xlabel)
    ax.set_title(title, fontsize=matplotlib.rcParams["font.size"])
    return ax


def convergence_plot(history, *, ax=None, xlabel: str = "迭代次数",
                     ylabel: str = "目标函数值", label: str = "本算法"):
    """收敛曲线：启发式算法的必配图（证明"收敛了"而不是"跑完了"）。"""
    if ax is None:
        _, ax = plt.subplots(figsize=(CM.single_column, 6 * CM.cm))
    ax.plot(range(1, len(history) + 1), history,
            color=PALETTE["signal"][0], lw=1.4, label=label)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    return ax


# --------------------------------------------------------------------------- #
def _selfcheck() -> None:
    print("=== cumcm-figure 环境自检 ===")
    print(f"matplotlib {matplotlib.__version__}")
    cjk = available_cjk_fonts()
    print(f"可用中文字体: {cjk if cjk else '无 —— 中文会显示为方块，请先安装字体'}")
    info = apply_cumcm_style()
    print(f"生效配置: {info}")
    # 真正画一张包含中文与负号的小图，验证字体链路
    fig, ax = plt.subplots(figsize=(CM.single_column, 4 * CM.cm))
    ax.plot([-2, -1, 0, 1, 2], [1, -1, 0, 1, -1], marker="o")
    ax.set_xlabel("时间（小时）")
    ax.set_ylabel("成本变化率（%）")
    ax.set_title("中文与负号渲染自检")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_selfcheck")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sizes = save_cumcm_figure(fig, out, verbose=False)
    print(f"自检图已导出: {out}.pdf ({sizes['pdf']} B), {out}.png ({sizes['png']} B)")
    print("请打开该 PDF 确认：中文正常、负号是短横线而非方块。")


if __name__ == "__main__":
    _selfcheck()
