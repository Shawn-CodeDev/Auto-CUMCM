"""S6/S7 实验：问题 2（全程干燥）、问题 3（烘干时长）、问题 4（最优厚度）。

问题 2：预热平衡 + 恒温干燥全程（2–3 天），物性用附录 3 的 C、T 依赖经验公式。
       产出表 3/表 4（3 h 内每隔 0.5 h）与 result2.xlsx。
问题 3：以"各处水分浓度 < 0.15 kg/kg"为判据，求所需烘干时长；产出表 5 与 result3.xlsx。
问题 4：药材尺寸随水分流失变化，用附录 4 的经验公式；产出表 6 与 result4.xlsx。

验证（S7）：
       用附件 2 实测的**半径收缩**独立校验模型——半径由体积平均含水率推算的
       体积收缩关系给出，与实测比对本模型的预测能力。
       半径-含水率关系由题面 ρ(C)=650+128C 导出（本模型唯一的结构性假设，
       在 validation_report.md 中做灵敏度分析）。
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
from cumcm_style import (CM, PALETTE, add_stat_box, annotate_extremum,  # noqa: E402
                         apply_cumcm_style, panel_label, save_cumcm_figure)

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


C0_INIT = 2.55
C_TARGET = 0.15


def radius_from_mean_C(Cmean: float, R0: float = 2e-2) -> float:
    """由体积平均含水率推半径。

    推导：[题] 附录 3 的 ρ(C) = 650 + 128C 是**堆积密度**（单位体积物料的质量）。
    单位干物质对应的体积 ∝ (1 + C) / ρ(C)。体积比 = [(1+C)/ρ(C)] / [(1+C0)/ρ(C0)]，
    圆柱体积 ∝ R²，故 R/R0 = sqrt(体积比)。
    """
    vol_ratio = ((1.0 + Cmean) / (650.0 + 128.0 * Cmean)) / \
                ((1.0 + C0_INIT) / (650.0 + 128.0 * C0_INIT))
    return R0 * float(np.sqrt(max(vol_ratio, 1e-12)))


def main() -> int:
    apply_cumcm_style(base_size=9)
    params = json.load(open(os.path.join(INP, "problem_params.json"), encoding="utf-8"))
    g = params["geometry"]
    p23 = params["appendix3_problem23"]
    R = g["radius_cm"] * 1e-2

    # 环境：预热段用实测；之后保持终值（恒温干燥段）——这是显式假设
    env_df = pd.read_csv(os.path.join(CLEAN, "env.csv"))
    t_env = env_df["t_s"].to_numpy(float)
    T_env = env_df["T_env_C"].to_numpy(float)
    C_env = env_df["C_env"].to_numpy(float)

    def env(tt: float):
        if tt <= t_env[-1]:
            return float(np.interp(tt, t_env, T_env)), float(np.interp(tt, t_env, C_env))
        # [假] 恒温干燥段：烘房维持预热段终值
        return float(T_env[-1]), float(C_env[-1])

    say("# 问题 2/3/4 实验结果")
    say("")
    say("## 模型与假设")
    say("")
    say(f"- 物性用**附录 3**（问题 2/3）：ρ=650+128C，c_p=1450+2736·C/(C+1)，"
        f"k=0.21+0.38·C/(C+1)")
    say(f"- 扩散系数 D=2.4e-3·exp(-0.45C)·exp(-3850/T)，随含水率下降而**急剧减小**"
        f"（C=2.55 时 D={2.4e-3*np.exp(-0.45*2.55)*np.exp(-3850/300):.3e} m²/s，"
        f"C=0.15 时 D={2.4e-3*np.exp(-0.45*0.15)*np.exp(-3850/300):.3e} m²/s）")
    say(f"- 恒温干燥段环境取预热段终值：T={T_env[-1]:.2f} °C，"
        f"C={C_env[-1]:.5f} kg/kg **[假]**")
    say(f"- 半径按 ρ(C) 导出的体积收缩关系随含水率变化 **[假]**")
    say("")

    # ---------------- 网格无关性（全程） ----------------
    say("## 网格无关性（全程 72 h 端点）")
    say("")
    say("| n | 体积平均含水率@72h | 相对差 |")
    say("|---|---|---|")
    ref = None
    for n in (101, 201, 401):
        m = CylinderModel(R=R, n=n, kind="p23")
        o = m.solve(72 * 3600.0, env, T0=g["T0_C"], C0=g["C0"],
                    h=params["problem1_constants"]["h"],
                    h_m=params["problem1_constants"]["hm"] * 1e-7,
                    t_eval=np.array([72 * 3600.0]), rtol=1e-6, atol=1e-9)
        cm = m.mean(C=o["C"][:, -1])
        rel = "—（基准）" if ref is None else f"{abs(cm-ref)/ref*100:.4f}%"
        ref = ref or cm
        say(f"| {n} | {cm:.6f} | {rel} |")
    say("")
    say("> 取 n=201。")
    say("")

    N = 201
    model = CylinderModel(R=R, n=N, kind="p23")

    # ---------------- 问题 2：全程 72 h ----------------
    t_end = 72 * 3600.0
    t_eval = np.unique(np.concatenate([
        np.arange(0.0, 3 * 3600.0 + 1.0, 5.0),          # 前 3 h 细
        np.arange(3 * 3600.0, t_end + 1.0, 60.0),       # 之后 1 min
        np.arange(0.0, 3 * 3600.0 + 1.0, 1.0),          # 题面要求的 1 s 栅格
    ]))
    t_eval = t_eval[t_eval <= t_end]
    o2 = model.solve(t_end, env, T0=g["T0_C"], C0=g["C0"],
                     h=params["problem1_constants"]["h"],
                     h_m=params["problem1_constants"]["hm"] * 1e-7,
                     t_eval=t_eval, rtol=1e-7, atol=1e-10)
    say("## 问题 2  求解信息")
    say("")
    say(f"- 时长 72 h，输出 {len(t_eval)} 个时间点，右端调用 {o2['nfev']} 次")
    say("")

    r_req = np.array([0.0, 0.5, 1.0, 1.5, 2.0]) * 1e-2
    t3 = np.arange(0.5, 3.0 + 1e-9, 0.5) * 3600.0

    def snap(o, ts):
        i = int(np.argmin(np.abs(o["t"] - ts)))
        T = np.interp(r_req, model.r, o["T"][:, i])
        C = np.interp(r_req, model.r, o["C"][:, i])
        return T, C

    say("## 表 3  3 小时内药材的温度（°C）")
    say("")
    say("| 时间/h | 0 cm | 0.5 cm | 1 cm | 1.5 cm | 2 cm |")
    say("|---|---|---|---|---|---|")
    rows3, rows4 = [], []
    for th in t3:
        T, C = snap(o2, th)
        rows3.append([th / 3600] + list(np.round(T, 4)))
        rows4.append([th / 3600] + list(np.round(C, 4)))
        say("| " + " | ".join(f"{v:.4f}" for v in rows3[-1]) + " |")
    say("")
    say("## 表 4  3 小时内药材的水分浓度（kg/kg）")
    say("")
    say("| 时间/h | 0 cm | 0.5 cm | 1 cm | 1.5 cm | 2 cm |")
    say("|---|---|---|---|---|---|")
    for row in rows4:
        say("| " + " | ".join(f"{v:.4f}" for v in row) + " |")
    say("")

    # result2.xlsx：每 1 s × 每 0.1 cm（72 h = 259201 行，题面要求）
    r_out = np.round(np.arange(0.0, 2.0 + 1e-9, 0.1), 4) * 1e-2
    t_all = np.arange(0.0, t_end + 1.0, 1.0)
    Tall = np.empty((len(t_all), len(r_out)))
    Call = np.empty_like(Tall)
    for k, tt in enumerate(t_all):
        i = int(np.argmin(np.abs(o2["t"] - tt)))
        Tall[k] = np.interp(r_out, model.r, o2["T"][:, i])
        Call[k] = np.interp(r_out, model.r, o2["C"][:, i])
    with pd.ExcelWriter(os.path.join(RES, "result2.xlsx"), engine="openpyxl") as w:
        pd.DataFrame(np.round(Tall, 4),
                     columns=[f"{c*100:g}" for c in r_out]).to_excel(w, sheet_name="温度")
        pd.DataFrame(np.round(Call, 4),
                     columns=[f"{c*100:g}" for c in r_out]).to_excel(w, sheet_name="水分浓度")
    say("## result2.xlsx")
    say("")
    say(f"- 形状：{len(t_all)} 行（每 1 s，覆盖 72 h）× {len(r_out)} 列（每 0.1 cm）")
    say("")

    # ---------------- 问题 3：烘干时长 ----------------
    Cmean_t = np.array([model.mean(C=o2["C"][:, k]) for k in range(o2["t"].size)])
    Cmax_t = o2["C"].max(axis=0)                  # 最干处（表面）
    # 判据：各处水分浓度 < 0.15  =>  最慢的点（中心）达标
    Ccenter_t = o2["C"][0, :]

    def first_time_below(arr, thr):
        idx = np.where(arr < thr)[0]
        return float(o2["t"][idx[0]]) if len(idx) else None

    t_center = first_time_below(Ccenter_t, C_TARGET)
    t_mean = first_time_below(Cmean_t, C_TARGET)

    say("## 问题 3  烘干时长")
    say("")
    say("判据：题面要求「药材**各处**的水分浓度应低于 0.15 kg/kg」，"
        "即最慢到达的点（中心）也须达标。")
    say("")
    say("| 判据 | 所需时长 |")
    say("|---|---|")
    say(f"| 中心点 C<{C_TARGET} | {t_center/3600:.2f} h（{t_center/86400:.2f} 天）"
        if t_center else "| 中心点 | 72 h 内未达标 |")
    say(f"| 体积平均 C<{C_TARGET} | {t_mean/3600:.2f} h（{t_mean/86400:.2f} 天）"
        if t_mean else "| 体积平均 | 72 h 内未达标 |")
    say("")
    T_dry = t_center if t_center else t_end
    say(f"**结论：所需烘干时长为 {T_dry/3600:.2f} h ≈ {T_dry/86400:.2f} 天。**")
    say("")

    t5 = np.arange(0.0, min(T_dry, t_end) + 1e-9, 6 * 3600.0)
    if t5.size == 0 or t5[-1] < T_dry:
        t5 = np.append(t5, T_dry)
    r5 = np.arange(0.0, 2.0 + 1e-9, 0.5) * 1e-2
    say("## 表 5  药材烘干过程的水分浓度（kg/kg，每隔 6 h）")
    say("")
    say("| 时间/h | " + " | ".join(f"{c*100:g} cm" for c in r5) + " |")
    say("|" + "---|" * (len(r5) + 1))
    for tt in t5:
        i = int(np.argmin(np.abs(o2["t"] - tt)))
        vals = np.interp(r5, model.r, o2["C"][:, i])
        say(f"| {tt/3600:.1f} | " + " | ".join(f"{v:.4f}" for v in vals) + " |")
    say("")

    # result3.xlsx：中心处每 60 s
    t60 = np.arange(0.0, t_end + 1.0, 60.0)
    r_out3 = np.round(np.arange(0.0, 2.0 + 1e-9, 0.1), 4) * 1e-2
    C3 = np.empty((len(t60), len(r_out3)))
    for k, tt in enumerate(t60):
        i = int(np.argmin(np.abs(o2["t"] - tt)))
        C3[k] = np.interp(r_out3, model.r, o2["C"][:, i])
    with pd.ExcelWriter(os.path.join(RES, "result3.xlsx"), engine="openpyxl") as w:
        pd.DataFrame(np.round(C3, 4),
                     columns=[f"{c*100:g}" for c in r_out3]).to_excel(w, sheet_name="水分浓度")
    say("## result3.xlsx")
    say("")
    say(f"- 形状：{len(t60)} 行（每 60 s）× {len(r_out3)} 列（每 0.1 cm）")
    say("")

    # ---------------- 问题 4：尺寸变化 ----------------
    m4 = CylinderModel(R=R, n=N, kind="p4")
    o4 = m4.solve(t_end, env, T0=g["T0_C"], C0=g["C0"],
                  h=params["problem1_constants"]["h"],
                  h_m=params["problem1_constants"]["hm"] * 1e-7,
                  t_eval=t_eval, rtol=1e-7, atol=1e-10)
    Cmean4 = np.array([m4.mean(C=o4["C"][:, k]) for k in range(o4["t"].size)])
    R4 = np.array([radius_from_mean_C(c, R) for c in Cmean4])

    say("## 问题 4  尺寸变化的温度与水分浓度")
    say("")
    say("- 物性用**附录 4**（问题 4）：ρ=760+90C，c_p=1850+2150·C/(C+1)，"
        "k=0.12+0.20·C/(C+1)")
    say(f"- 半径由 {R*100:.3f} cm 收缩到 {R4[-1]*100:.3f} cm"
        f"（收缩 {(1-R4[-1]/R)*100:.1f}%）")
    say("")

    t6 = np.arange(0.0, t_end + 1e-9, 6 * 3600.0)
    say("## 表 6  药材烘干过程的水分浓度（含尺寸变化，每隔 6 h）")
    say("")
    say("| 时间/h | " + " | ".join(f"{c*100:g} cm" for c in r5) + " | 半径/cm |")
    say("|" + "---|" * (len(r5) + 2))
    for tt in t6:
        i = int(np.argmin(np.abs(o4["t"] - tt)))
        vals = np.interp(r5, m4.r, o4["C"][:, i])
        say(f"| {tt/3600:.1f} | " + " | ".join(f"{v:.4f}" for v in vals)
            + f" | {R4[i]*100:.4f} |")
    say("")

    t60_4 = np.arange(0.0, t_end + 1.0, 60.0)
    C4 = np.empty((len(t60_4), len(r_out3)))
    for k, tt in enumerate(t60_4):
        i = int(np.argmin(np.abs(o4["t"] - tt)))
        C4[k] = np.interp(r_out3, m4.r, o4["C"][:, i])
    with pd.ExcelWriter(os.path.join(RES, "result4.xlsx"), engine="openpyxl") as w:
        pd.DataFrame(np.round(C4, 4),
                     columns=[f"{c*100:g}" for c in r_out3]).to_excel(w, sheet_name="水分浓度")
    say("## result4.xlsx")
    say("")
    say(f"- 形状：{len(t60_4)} 行 × {len(r_out3)} 列")
    say("")

    # ---------------- 验证：与附件 2 实测半径对比 ----------------
    rad = pd.read_csv(os.path.join(CLEAN, "radius.csv"))
    t_meas = rad["t_s"].to_numpy(float)
    r_meas = rad["r_m"].to_numpy(float)
    r_pred = np.interp(t_meas, o2["t"], R4)      # 用问题 4 的收缩模型（含尺寸变化）

    err_cm = (r_pred - r_meas) * 100
    rmse = float(np.sqrt(np.mean(err_cm ** 2)))
    mape = float(np.mean(np.abs(err_cm / r_meas * 100)))
    say("## S7 验证  与附件 2 实测半径对比")
    say("")
    say("半径是**独立观测量**（模型没有用半径数据做拟合），因此这是真正的外部验证。")
    say("")
    say("| 指标 | 值 |")
    say("|---|---|")
    say(f"| 测点数 | {len(t_meas)} |")
    say(f"| 半径 RMSE | {rmse:.4f} cm |")
    say(f"| 半径 MAPE | {mape:.2f}% |")
    say(f"| 最大偏差 | {np.abs(err_cm).max():.4f} cm |")
    say(f"| 实测终半径 | {r_meas[-1]*100:.3f} cm |")
    say(f"| 预测终半径 | {r_pred[-1]*100:.3f} cm |")
    say("")

    # ---------------- 图 ----------------
    import matplotlib.pyplot as plt

    # 图：全程含水率场热力图
    fig, axes = plt.subplots(1, 2, figsize=(CM.double_column, 6.0 * CM.cm))
    tt = o2["t"] / 3600.0
    rr = model.r * 100
    stride = max(1, len(tt) // 400)
    ax = axes[0]
    im = ax.pcolormesh(tt[::stride], rr, o2["C"][:, ::stride],
                       cmap=PALETTE["sequential"], shading="auto")
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("水分浓度（kg/kg）", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    ax.set_xlabel("时间（h）")
    ax.set_ylabel("到药材中心的距离（cm）")
    ax.set_title("水分浓度时空演化")
    panel_label(ax, "a")

    ax = axes[1]
    im = ax.pcolormesh(tt[::stride], rr, o2["T"][:, ::stride],
                       cmap="inferno", shading="auto")
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("温度（°C）", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    ax.set_xlabel("时间（h）")
    ax.set_ylabel("到药材中心的距离（cm）")
    ax.set_title("温度时空演化")
    panel_label(ax, "b")
    fig.tight_layout(w_pad=1.6)
    save_cumcm_figure(fig, os.path.join(FIGS, "E05_p2_fields"))

    # 图：中心/表面含水率 + 烘干时长判据
    fig, ax = plt.subplots(figsize=(CM.single_column + 2 * CM.cm, 6.4 * CM.cm))
    ax.plot(tt, o2["C"][0], color=PALETTE["accent"][0], lw=1.6, label="中心")
    ax.plot(tt, o2["C"][-1], color=PALETTE["signal"][0], lw=1.6, label="表面")
    ax.plot(tt, Cmean_t, color=PALETTE["signal"][2], lw=1.4, ls="--", label="体积平均")
    ax.axhline(C_TARGET, color=PALETTE["neutral"][0], lw=1.0, ls=":")
    ax.text(0.5, C_TARGET + 0.06, f"目标 {C_TARGET} kg/kg", fontsize=8,
            color=PALETTE["neutral"][0])
    if t_center:
        annotate_extremum(ax, t_center / 3600, C_TARGET,
                          f"烘干完成 {t_center/3600:.1f} h",
                          xytext=(-88, 22))
    ax.set_xlabel("时间（h）")
    ax.set_ylabel("水分浓度（kg/kg）")
    ax.set_title("含水率衰减与烘干时长判据")
    ax.legend()
    add_stat_box(ax, f"n = {len(o2['t'])} 时刻；判据为中心点达标")
    save_cumcm_figure(fig, os.path.join(FIGS, "E06_drying_time"))

    # 图：验证——半径实测 vs 预测
    fig, axes = plt.subplots(1, 2, figsize=(CM.double_column, 5.8 * CM.cm))
    ax = axes[0]
    ax.plot(t_meas / 3600, r_meas * 100, "o", ms=2.8, color=PALETTE["neutral"][1],
            label="附件 2 实测")
    ax.plot(o2["t"] / 3600, R4 * 100, color=PALETTE["accent"][0], lw=1.6,
            label="模型预测")
    ax.set_xlabel("时间（h）")
    ax.set_ylabel("药材半径（cm）")
    ax.set_title("半径收缩：实测 vs 预测")
    ax.legend()
    panel_label(ax, "a")

    ax = axes[1]
    ax.plot(t_meas / 3600, err_cm, color=PALETTE["signal"][0], lw=1.4)
    ax.axhline(0, color=PALETTE["neutral"][0], lw=0.9)
    ax.set_xlabel("时间（h）")
    ax.set_ylabel("半径偏差（cm）")
    ax.set_title(f"预测偏差（RMSE = {rmse:.3f} cm）")
    panel_label(ax, "b")
    add_stat_box(axes[0], f"MAPE = {mape:.2f}%，共 {len(t_meas)} 个测点")
    fig.tight_layout(w_pad=2.0)
    save_cumcm_figure(fig, os.path.join(FIGS, "E07_validation"))

    # ---------------- 落盘 ----------------
    np.savez_compressed(os.path.join(RES, "E05_fields.npz"),
                        t=o2["t"], r=model.r, T=o2["T"], C=o2["C"],
                        Cmean=Cmean_t, R4=R4)
    pd.DataFrame({"t_s": o2["t"], "C_center": o2["C"][0],
                  "C_surface": o2["C"][-1], "C_mean": Cmean_t,
                  "R_m": R4}).to_csv(
        os.path.join(RES, "E05_scalars.csv"), index=False, encoding="utf-8-sig")

    summary = {
        "drying_time_h": round(T_dry / 3600, 3),
        "drying_time_days": round(T_dry / 86400, 3),
        "radius_rmse_cm": round(rmse, 5),
        "radius_mape_pct": round(mape, 3),
        "final_radius_cm": round(float(R4[-1]) * 100, 4),
        "final_center_C": round(float(o2["C"][0, -1]), 5),
        "final_mean_C": round(float(Cmean_t[-1]), 5),
        "nfev_p2": int(o2["nfev"]),
    }
    json.dump(summary, open(os.path.join(RES, "E05_summary.json"), "w",
                            encoding="utf-8"), ensure_ascii=False, indent=2)

    say("## 图表产出")
    say("")
    say("- `figures/E05_p2_fields.pdf`：72 h 含水率与温度时空演化（热力图）")
    say("- `figures/E06_drying_time.pdf`：含水率衰减与烘干时长判据")
    say("- `figures/E07_validation.pdf`：半径实测 vs 预测 + 偏差")
    say("")
    say("## 关键结果汇总")
    say("")
    for k, v in summary.items():
        say(f"- {k} = {v}")

    open(os.path.join(RES, "E05_report.md"), "w", encoding="utf-8").write(
        "\n".join(log) + "\n")
    print(f"\n写入 {RES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
