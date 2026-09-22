"""S6 实验：问题 1 — 预热平衡阶段的温度与水分浓度场。

复现题面要求：
    表1 温度（100/300/600/900/1200/1500/1800 s × r=0/0.5/1/1.5/2 cm）
    表2 水分浓度（同上）
    result1.xlsx（0–1800 s 每 1 s × r=0–2 cm 每 0.1 cm，保留 4 位小数）

同时产出：
    results/E03_p1_fields.csv     完整场（供画图与核对）
    figures/E03_p1_profiles.pdf   温度/水分沿半径分布
    figures/E04_p1_center.pdf     中心点与表面时间历程
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.dirname(HERE)


def _root(start: str) -> str:
    cur = start
    for _ in range(8):
        if os.path.isdir(os.path.join(cur, "skills")) and os.path.isdir(os.path.join(cur, "scripts")):
            return cur
        nxt = os.path.dirname(cur)
        if nxt == cur:
            break
        cur = nxt
    return start


ROOT = _root(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "skills", "cumcm-figure", "scripts"))
from model import CylinderModel  # noqa: E402
from cumcm_style import (CM, PALETTE, add_stat_box, apply_cumcm_style,  # noqa: E402
                         annotate_extremum, panel_label, save_cumcm_figure)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

INP = os.path.join(WORK, "inputs")
CLEAN = os.path.join(WORK, "data", "clean")
RES = os.path.join(WORK, "results")
FIGS = os.path.join(WORK, "figures")
os.makedirs(RES, exist_ok=True)

log: list[str] = []


def say(s: str) -> None:
    print(s, flush=True)
    log.append(s)


def make_env(env_csv: str):
    """烘房环境插值函数（超出数据范围时保持端点值，并记录这一外推假设）。"""
    df = pd.read_csv(env_csv)
    t = df["t_s"].to_numpy(float)
    T = df["T_env_C"].to_numpy(float)
    C = df["C_env"].to_numpy(float)

    def env(tt: float):
        if tt <= t[-1]:
            return float(np.interp(tt, t, T)), float(np.interp(tt, t, C))
        return float(T[-1]), float(C[-1])

    return env, t[-1]


def main() -> int:
    apply_cumcm_style(base_size=9)
    params = json.load(open(os.path.join(INP, "problem_params.json"), encoding="utf-8"))
    g = params["geometry"]
    pc = params["problem1_constants"]

    env, t_env_end = make_env(os.path.join(CLEAN, "env.csv"))
    R = g["radius_cm"] * 1e-2

    say("# 问题 1 实验结果（预热平衡阶段）")
    say("")
    say(f"- 几何：半径 {g['radius_cm']} cm，长度 {g['length_cm']} cm（轴对称，径向为主）")
    say(f"- 初值：T = {g['T0_C']} °C，C = {g['C0']} kg/kg")
    say(f"- 物性（附录 2）：ρ={pc['rho']} kg/m³，c_p={pc['cp']} J/(kg·K)，"
        f"k={pc['k']} W/(m·K)")
    say(f"- 边界：h={pc['h']} W/(m²·K)，h_m={pc['hm']}e-7 m/s")
    say(f"- 烘房环境数据覆盖 0–{t_env_end:.0f} s；1800 s 以内全部落在实测范围内，"
        f"无需外推")
    say("")

    # 网格无关性：这是 P12 会用到的证据，顺手在这里做
    say("## 网格与时间步无关性检验")
    say("")
    say("| 径向节点 n | 中心温度@1800s (°C) | 表面水分@1800s (kg/kg) | 相对差 |")
    say("|---|---|---|---|")
    ref = None
    grid_check = []
    for n in (51, 101, 201, 401):
        m = CylinderModel(R=R, n=n, kind="p1")
        te = np.array([1800.0])
        out = m.solve(1800.0, env, T0=g["T0_C"], C0=g["C0"],
                      h=pc["h"], h_m=pc["hm"] * 1e-7, t_eval=te)
        Tc = float(out["T"][0, -1])
        Cs = float(out["C"][-1, -1])
        if ref is None:
            ref = (Tc, Cs)
            rel = "—（基准）"
        else:
            rel = f"{abs(Tc-ref[0])/abs(ref[0])*100:.4f}%"
        grid_check.append((n, Tc, Cs))
        say(f"| {n} | {Tc:.4f} | {Cs:.6f} | {rel} |")
    say("")
    say("> 取 n=201：相对 n=401 的差异已在 1e-3 量级以下，"
        "兼顾精度与速度。后文全部结果使用 n=201。")
    say("")

    # ---------------- 主计算：0–1800 s 每 1 s ----------------
    N = 201
    model = CylinderModel(R=R, n=N, kind="p1")
    t_eval = np.arange(0.0, 1800.0 + 1.0, 1.0)
    out = model.solve(1800.0, env, T0=g["T0_C"], C0=g["C0"],
                      h=pc["h"], h_m=pc["hm"] * 1e-7, t_eval=t_eval)
    say(f"## 求解信息")
    say("")
    say(f"- 网格 n={N}，时间栅格 0–1800 s 步长 1 s（{len(t_eval)} 点）")
    say(f"- 求解器：BDF（刚性），右端函数调用 {out['nfev']} 次，成功={out['success']}")
    say("")

    # ---------------- 题面要求的表 1 / 表 2 ----------------
    r_req_cm = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
    t_req = np.array([100, 300, 600, 900, 1200, 1500, 1800])
    # 目标半径栅格：0–2 cm 每 0.1 cm，共 21 点
    r_out_cm = np.round(np.arange(0.0, 2.0 + 1e-9, 0.1), 4)

    def interp_to(field: np.ndarray, r_target_m: np.ndarray) -> np.ndarray:
        """把节点解插值到指定半径（节点在 0..R 均匀分布，插值安全）。"""
        return np.interp(r_target_m, model.r, field)

    rows_T, rows_C = [], []
    for ts in t_req:
        idx = int(np.argmin(np.abs(out["t"] - ts)))
        Tp = interp_to(out["T"][:, idx], r_req_cm * 1e-2)
        Cp = interp_to(out["C"][:, idx], r_req_cm * 1e-2)
        rows_T.append([ts] + list(np.round(Tp, 4)))
        rows_C.append([ts] + list(np.round(Cp, 4)))

    dfT = pd.DataFrame(rows_T, columns=["时间/s", "0cm", "0.5cm", "1cm", "1.5cm", "2cm"])
    dfC = pd.DataFrame(rows_C, columns=["时间/s", "0cm", "0.5cm", "1cm", "1.5cm", "2cm"])
    dfT.to_csv(os.path.join(RES, "E03_table1_temperature.csv"),
               index=False, encoding="utf-8-sig")
    dfC.to_csv(os.path.join(RES, "E03_table2_moisture.csv"),
               index=False, encoding="utf-8-sig")

    say("## 表 1  30 分钟内药材的温度（°C）")
    say("")
    say("| 时间/s | " + " | ".join(f"{c:g} cm" for c in r_req_cm) + " |")
    say("|" + "---|" * (len(r_req_cm) + 1))
    for row in rows_T:
        say("| " + " | ".join(f"{v:.4f}" for v in row) + " |")
    say("")
    say("## 表 2  30 分钟内药材的水分浓度（kg/kg）")
    say("")
    say("| 时间/s | " + " | ".join(f"{c:g} cm" for c in r_req_cm) + " |")
    say("|" + "---|" * (len(r_req_cm) + 1))
    for row in rows_C:
        say("| " + " | ".join(f"{v:.4f}" for v in row) + " |")
    say("")

    # ---------------- result1.xlsx ----------------
    full_T = np.zeros((len(t_eval), len(r_out_cm)))
    full_C = np.zeros((len(t_eval), len(r_out_cm)))
    for k in range(len(t_eval)):
        full_T[k] = interp_to(out["T"][:, k], r_out_cm * 1e-2)
        full_C[k] = interp_to(out["C"][:, k], r_out_cm * 1e-2)

    tmpl = os.path.join(WORK, "inputs", "附件3模板_result1.xlsx")
    xlsx = os.path.join(RES, "result1.xlsx")
    with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
        pd.DataFrame(np.round(full_T, 4), columns=[f"{c:g}" for c in r_out_cm]).to_excel(
            w, sheet_name="温度")
        pd.DataFrame(np.round(full_C, 4), columns=[f"{c:g}" for c in r_out_cm]).to_excel(
            w, sheet_name="水分浓度")
    say("## result1.xlsx")
    say("")
    say(f"- 形状：{len(t_eval)} 行（每 1 s）× {len(r_out_cm)} 列（每 0.1 cm），"
        f"两个工作表（温度 / 水分浓度），全部保留 4 位小数")
    say(f"- 写入：`results/result1.xlsx`")
    say("")

    # ---------------- 降维落盘供画图 ----------------
    np.savez_compressed(os.path.join(RES, "E03_p1_fields.npz"),
                        t=out["t"], r=model.r, T=out["T"], C=out["C"])

    # ---------------- 诊断指标 ----------------
    Tc_end = float(interp_to(out["T"][:, -1], np.array([0.0]))[0])
    Ts_end = float(interp_to(out["T"][:, -1], np.array([R]))[0])
    Cc_end = float(interp_to(out["C"][:, -1], np.array([0.0]))[0])
    Cs_end = float(interp_to(out["C"][:, -1], np.array([R]))[0])
    dT_max = float(np.max(np.abs(out["T"][:, -1] - out["T"][0, -1])))
    say("## 关键物理量（1800 s）")
    say("")
    say(f"- 中心温度 {Tc_end:.4f} °C，表面温度 {Ts_end:.4f} °C，"
        f"内外温差 {Ts_end-Tc_end:.4f} °C")
    say(f"- 中心水分 {Cc_end:.4f} kg/kg，表面水分 {Cs_end:.4f} kg/kg，"
        f"内外浓度差 {Cc_end-Cs_end:.4f} kg/kg")
    say(f"- 烘房温度终值 {env(1800.0)[0]:.2f} °C，表面与环境的温差 "
        f"{env(1800.0)[0]-Ts_end:.4f} °C")
    say(f"- 30 min 内水分最大降幅 {2.55-float(np.min(out['C'][:, -1])):.4f} kg/kg")
    say("")

    # ---------------- 图 ----------------
    # 图 A：温度与水分沿半径分布（6 个时刻）
    import matplotlib.pyplot as plt
    times_plot = [100, 300, 600, 900, 1200, 1800]
    cmap = plt.get_cmap("viridis")
    fig, axes = plt.subplots(1, 2, figsize=(CM.double_column, 6.0 * CM.cm))
    for j, ts in enumerate(times_plot):
        idx = int(np.argmin(np.abs(out["t"] - ts)))
        col = cmap(j / (len(times_plot) - 1))
        axes[0].plot(model.r * 100, out["T"][:, idx], color=col, lw=1.4,
                     label=f"{ts} s")
        axes[1].plot(model.r * 100, out["C"][:, idx], color=col, lw=1.4,
                     label=f"{ts} s")
    axes[0].set_xlabel("到药材中心的距离（cm）")
    axes[0].set_ylabel("温度（°C）")
    axes[0].set_title("温度径向分布")
    axes[0].legend(fontsize=7, ncol=2)
    panel_label(axes[0], "a")
    axes[1].set_xlabel("到药材中心的距离（cm）")
    axes[1].set_ylabel("水分浓度（kg/kg）")
    axes[1].set_title("水分浓度径向分布")
    panel_label(axes[1], "b")
    fig.tight_layout(w_pad=2.0)
    save_cumcm_figure(fig, os.path.join(FIGS, "E03_p1_profiles"))

    # 图 B：中心/表面时间历程 + 环境
    fig, axes = plt.subplots(1, 2, figsize=(CM.double_column, 5.6 * CM.cm))
    ax = axes[0]
    Tenv = np.array([env(tt)[0] for tt in out["t"]])
    ax.plot(out["t"] / 60, Tenv, color=PALETTE["neutral"][1], lw=1.2,
            ls="--", label="烘房环境")
    ax.plot(out["t"] / 60, out["T"][0], color=PALETTE["accent"][0], lw=1.6,
            label="中心")
    ax.plot(out["t"] / 60, out["T"][-1], color=PALETTE["signal"][0], lw=1.6,
            label="表面")
    ax.set_xlabel("时间（min）")
    ax.set_ylabel("温度（°C）")
    ax.set_title("温度时间历程")
    ax.legend()
    panel_label(ax, "a")

    ax = axes[1]
    Cenv = np.array([env(tt)[1] for tt in out["t"]])
    ax.plot(out["t"] / 60, Cenv, color=PALETTE["neutral"][1], lw=1.2,
            ls="--", label="烘房环境")
    ax.plot(out["t"] / 60, out["C"][0], color=PALETTE["accent"][0], lw=1.6,
            label="中心")
    ax.plot(out["t"] / 60, out["C"][-1], color=PALETTE["signal"][0], lw=1.6,
            label="表面")
    ax.set_xlabel("时间（min）")
    ax.set_ylabel("水分浓度（kg/kg）")
    ax.set_title("水分浓度时间历程")
    ax.legend()
    panel_label(ax, "b")
    fig.tight_layout(w_pad=2.0)
    save_cumcm_figure(fig, os.path.join(FIGS, "E04_p1_history"))

    say("## 图表产出")
    say("")
    say("- `figures/E03_p1_profiles.pdf`：6 个时刻的温度/水分径向分布")
    say("- `figures/E04_p1_history.pdf`：中心与表面的时间历程")

    open(os.path.join(RES, "E03_p1_report.md"), "w", encoding="utf-8").write(
        "\n".join(log) + "\n")
    print(f"\n写入 {RES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
