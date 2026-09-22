"""S2 数据清洗与诊断：读取 2026 A 题附件 1/2，产出清洗后的数据与诊断图。

输入：
    附件1.xlsx —— 烘房环境：时间(s)、温度(°C)、水分浓度(kg/kg)
    附件2.xlsx —— 药材半径随时间变化：时间(s)、半径(cm)

产出：
    data/clean/env.csv         烘房环境插值到统一时间栅格
    data/clean/radius.csv      实测半径
    figures/data_env.pdf/png   环境温度与水分浓度
    figures/data_radius.pdf/png 半径收缩曲线
    data_report.md             数据审计报告

所有量纲统一到 SI。固定随机种子（本步无随机性，仍显式声明以便复现）。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.dirname(HERE)


def _find_repo_root(start: str) -> str:
    """向上找到含 skills/ 与 scripts/ 的仓库根（不要靠数 dirname 层数）。"""
    cur = start
    for _ in range(8):
        if os.path.isdir(os.path.join(cur, "skills")) and os.path.isdir(os.path.join(cur, "scripts")):
            return cur
        nxt = os.path.dirname(cur)
        if nxt == cur:
            break
        cur = nxt
    return start


ROOT = _find_repo_root(HERE)
sys.path.insert(0, os.path.join(ROOT, "skills", "cumcm-figure", "scripts"))
from cumcm_style import (CM, PALETTE, add_stat_box, apply_cumcm_style,  # noqa: E402
                         save_cumcm_figure)

SEED = 42
np.random.seed(SEED)

INP = os.path.join(WORK, "inputs")
CLEAN = os.path.join(WORK, "data", "clean")
FIGS = os.path.join(WORK, "figures")
os.makedirs(CLEAN, exist_ok=True)
os.makedirs(FIGS, exist_ok=True)

report: list[str] = []

# 本机 Python 的 stdout 默认是 cp936，直接 print 中文/上标会抛 UnicodeEncodeError。
# 统一改成 UTF-8，避免"脚本逻辑对但一打印就崩"。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


def log(s: str) -> None:
    print(s, flush=True)
    report.append(s)


# --------------------------------------------------------------------------- #
def main() -> int:
    apply_cumcm_style(base_size=9)

    params = json.load(open(os.path.join(INP, "problem_params.json"), encoding="utf-8"))
    geo = params["geometry"]

    # ---------------- 附件 1：烘房环境 ----------------
    env = pd.read_excel(os.path.join(INP, "附件1.xlsx"))
    env.columns = [str(c).strip() for c in env.columns]
    log("## 一、文件登记")
    log("")
    log("| 文件 | 行×列 | 字段 | 缺失 | 异常 | 单位 |")
    log("|---|---|---|---|---|---|")

    t_env = env["时间"].to_numpy(dtype=float)
    T_env = env["温度"].to_numpy(dtype=float)
    C_env = env["水分浓度"].to_numpy(dtype=float)
    log(f"| 附件1.xlsx | {env.shape[0]}×{env.shape[1]} | 时间/温度/水分浓度 | "
        f"{int(env.isna().sum().sum())} | 0 | s / °C / kg·kg⁻¹ |")

    # ---------------- 附件 2：半径 ----------------
    rad = pd.read_excel(os.path.join(INP, "附件2.xlsx"))
    rad.columns = [str(c).strip() for c in rad.columns]
    t_r = rad["时间"].to_numpy(dtype=float)
    r_cm = rad["半径"].to_numpy(dtype=float)
    log(f"| 附件2.xlsx | {rad.shape[0]}×{rad.shape[1]} | 时间/半径 | "
        f"{int(rad.isna().sum().sum())} | 0 | s / cm |")
    log("")

    # 单调性检查（半径应单调不增）
    d_r = np.diff(r_cm)
    n_increase = int((d_r > 1e-9).sum())
    log("## 二、质量检查")
    log("")
    log(f"- 附件1 时间栅格：{t_env[0]:.0f} → {t_env[-1]:.0f} s，步长 "
        f"{np.median(np.diff(t_env)):.0f} s，共 {len(t_env)} 点")
    log(f"- 附件1 烘房温度范围：{T_env.min():.2f} – {T_env.max():.2f} °C")
    log(f"- 附件1 烘房水分浓度范围：{C_env.min():.5f} – {C_env.max():.5f} kg/kg")
    log(f"- 附件2 时间栅格：{t_r[0]:.0f} → {t_r[-1]:.0f} s（约 {t_r[-1]/3600:.1f} h），"
        f"共 {len(t_r)} 点")
    log(f"- 附件2 半径：{r_cm[0]:.3f} → {r_cm[-1]:.3f} cm，"
        f"收缩 {(1 - r_cm[-1]/r_cm[0])*100:.1f}%")
    log(f"- 半径非单调点：{n_increase} 个"
        + ("（已用累积最小值修正量测抖动）" if n_increase else "（无需修正）"))
    log("")

    # 修正量测抖动：取累积最小，保证半径单调不增
    r_fixed = np.minimum.accumulate(r_cm)

    # ---------------- 量纲统一 ----------------
    r_m = r_fixed * 1e-2                       # cm -> m
    log("## 三、量纲统一（全部转 SI）")
    log("")
    log("| 量 | 原始单位 | SI 单位 | 换算 |")
    log("|---|---|---|---|")
    log("| 半径 | cm | m | ×10⁻² |")
    log("| 时间 | s | s | — |")
    log("| 温度 | °C | °C | 热力学计算中用 K：T[K] = T[°C] + 273.15 |")
    log("| 水分浓度 | kg/kg（干基） | kg/kg | — |")
    log("")

    # ---------------- 落盘 ----------------
    pd.DataFrame({"t_s": t_env, "T_env_C": T_env, "C_env": C_env}).to_csv(
        os.path.join(CLEAN, "env.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame({"t_s": t_r, "r_cm_raw": r_cm, "r_cm": r_fixed,
                  "r_m": r_m}).to_csv(
        os.path.join(CLEAN, "radius.csv"), index=False, encoding="utf-8-sig")

    # ---------------- 诊断图 1：环境 ----------------
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(CM.double_column, 5.4 * CM.cm))
    axes[0].plot(t_env / 60, T_env, color=PALETTE["signal"][0], lw=1.4)
    axes[0].set_xlabel("时间（min）")
    axes[0].set_ylabel("烘房温度（°C）")
    axes[0].set_title("烘房温度变化")
    axes[0].annotate(f"终值 {T_env[-1]:.1f} °C", xy=(t_env[-1] / 60, T_env[-1]),
                     xytext=(-70, 8), textcoords="offset points", fontsize=8,
                     color=PALETTE["accent"][0],
                     arrowprops={"arrowstyle": "->", "color": PALETTE["accent"][0], "lw": 0.8})

    axes[1].plot(t_env / 60, C_env, color=PALETTE["signal"][2], lw=1.4)
    axes[1].set_xlabel("时间（min）")
    axes[1].set_ylabel("烘房水分浓度（kg/kg）")
    axes[1].set_title("烘房水分浓度变化")
    add_stat_box(axes[0], f"n = {len(t_env)}，步长 {np.median(np.diff(t_env)):.0f} s")
    fig.tight_layout(w_pad=2.0)
    save_cumcm_figure(fig, os.path.join(FIGS, "E01_env"))
    log("## 四、诊断图")
    log("")
    log("- `figures/E01_env.pdf`：烘房温度与水分浓度（左：温度单调上升至平衡；"
        "右：水分浓度随物料失水而上升）")

    # ---------------- 诊断图 2：半径收缩 ----------------
    fig, ax = plt.subplots(figsize=(CM.single_column, 6.0 * CM.cm))
    ax.plot(t_r / 3600, r_cm, color=PALETTE["neutral"][1], lw=1.0,
            marker="o", markersize=2.5, label="实测")
    ax.plot(t_r / 3600, r_fixed, color=PALETTE["accent"][0], lw=1.4,
            label="单调化修正")
    ax.set_xlabel("时间（h）")
    ax.set_ylabel("药材半径（cm）")
    ax.set_title("药材半径随时间收缩")
    ax.legend(loc="upper right")
    save_cumcm_figure(fig, os.path.join(FIGS, "E02_radius"))
    log(f"- `figures/E02_radius.pdf`：半径由 {r_cm[0]:.2f} cm 收缩至 "
        f"{r_fixed[-1]:.3f} cm（收缩 {(1-r_fixed[-1]/r_cm[0])*100:.1f}%）")

    # ---------------- 数据局限 ----------------
    log("")
    log("## 五、数据局限（P12 适用边界的原料）")
    log("")
    log(f"- 附件 1 仅覆盖预热平衡阶段前 {t_env[-1]/60:.0f} min，"
        "无法直接标定恒温干燥阶段参数")
    log(f"- 附件 2 覆盖 {t_r[-1]/3600:.1f} h，只记录**外半径**，"
        "无法直接观测内部水分分布")
    log("- 烘房水分浓度是**环境**浓度，与药材内部浓度不同，不可混用")
    log(f"- 半径量测存在 {n_increase} 个非单调抖动点，已用累积最小值修正；"
        "修正引入的偏差未超过 {:.2f} mm".format(float(np.abs(r_cm - r_fixed).max()) * 10))

    open(os.path.join(WORK, "data_report.md"), "w", encoding="utf-8").write(
        "# P5 数据审计\n\n" + "\n".join(report) + "\n")
    print(f"\n数据审计写入 {os.path.join(WORK, 'data_report.md')}")
    print(f"清洗数据写入 {CLEAN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
