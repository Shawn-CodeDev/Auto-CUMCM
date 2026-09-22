"""标定有效扩散系数 β：用附件 2 的**实测半径**时间尺度反演。

做法（一步一参数的辨识，不是同时拟合两个参数）
    1. 半径 R(t) 由附件 2 实测插值给出（单调化），作为**已知输入**而非待拟合量；
    2. 于是模型里只剩一个未知量 β（有效扩散系数修正因子）；
    3. 定义目标：模型预测的"体积平均含水率降到 0.15 kg/kg 所需时间"应等于
       实测半径停止收缩的时间（半径进入平台 = 物料基本干燥完成的观测量度）；
    4. 一维求根定出 β。

这样做的可辩护性：R(t) 直接来自题目附件，不是我们编的；β 只有一个自由度，
且它的物理含义明确（收缩致密化对扩散的抑制）。β 的取值会在
validation_report.md 里做 ±30% 灵敏度分析。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import brentq

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from model_shrinking import ShrinkingCylinder  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

params = json.load(open(os.path.join(WORK, "inputs", "problem_params.json"), encoding="utf-8"))
g = params["geometry"]
pc = params["problem1_constants"]
R0 = g["radius_cm"] * 1e-2
C_TARGET = 0.15

env_df = pd.read_csv(os.path.join(WORK, "data", "clean", "env.csv"))
t_env = env_df["t_s"].to_numpy(float)
T_env = env_df["T_env_C"].to_numpy(float)
C_env = env_df["C_env"].to_numpy(float)
rad = pd.read_csv(os.path.join(WORK, "data", "clean", "radius.csv"))
t_r = rad["t_s"].to_numpy(float)
r_meas = rad["r_m"].to_numpy(float)


def env(tt):
    if tt <= t_env[-1]:
        return float(np.interp(tt, t_env, T_env)), float(np.interp(tt, t_env, C_env))
    return float(T_env[-1]), float(C_env[-1])


def shrink_measured(t):
    """实测半径作为已知的时间函数（超出测量范围时保持终值）。"""
    if t <= t_r[-1]:
        return float(np.interp(t, t_r, r_meas))
    return float(r_meas[-1])


# 实测半径停止收缩（进入平台）的时刻 —— 作为"基本干燥完成"的观测代理
plateau = r_meas[-1]
tol = 0.002 * r_meas[0]                     # 0.2% 初始半径
idx = np.where(np.abs(r_meas - plateau) < tol)[0]
t_plateau = float(t_r[idx[0]]) if len(idx) else float(t_r[-1])

out = []
out.append("# β 标定（有效扩散系数修正因子）")
out.append("")
out.append(f"- 实测初始半径 {r_meas[0]*100:.4f} cm，终半径 {r_meas[-1]*100:.4f} cm")
out.append(f"- 半径进入平台（|R-R_final| < {tol*100:.4f} cm）的时刻："
           f"{t_plateau/3600:.2f} h")
out.append(f"- 标定判据：模型体积平均含水率降到 {C_TARGET} kg/kg 的时间 = "
           f"{t_plateau/3600:.2f} h")
out.append("")


def time_to_dry(beta: float, t_max: float = 120 * 3600.0) -> float:
    m = ShrinkingCylinder(R0=R0, n=101, kind="p23", shrink=shrink_measured, beta=beta)
    te = np.arange(0.0, t_max + 1.0, 300.0)
    o = m.solve(t_max, env, T0=g["T0_C"], C0=g["C0"], h=pc["h"],
                h_m=pc["hm"] * 1e-7, t_eval=te, rtol=1e-6, atol=1e-9)
    cm = np.array([m.mean_C(o["C"][:, k]) for k in range(o["t"].size)])
    hit = np.where(cm < C_TARGET)[0]
    return float(o["t"][hit[0]]) if len(hit) else float("inf")


out.append("| β | 体积平均 C 到 0.15 的时长 (h) |")
out.append("|---|---|")
probe = [0.1, 0.2, 0.35, 0.5, 0.75, 1.0]
for b in probe:
    tt = time_to_dry(b)
    out.append(f"| {b} | {tt/3600:.2f}" if np.isfinite(tt) else f"| {b} | 未达标 |")
out.append("")

# 求根：f(β) = t_dry(β) - t_plateau
lo, hi = 0.02, 1.0
f_lo, f_hi = time_to_dry(lo) - t_plateau, time_to_dry(hi) - t_plateau
if f_lo * f_hi > 0:
    out.append(f"⚠️ 区间 [{lo},{hi}] 内未变号（f({lo})={f_lo/3600:.2f} h，"
               f"f({hi})={f_hi/3600:.2f} h），改用最接近的网格值。")
    beta = min(probe, key=lambda b: abs(time_to_dry(b) - t_plateau))
else:
    beta = float(brentq(lambda b: time_to_dry(b) - t_plateau, lo, hi, xtol=1e-3))

t_dry_beta = time_to_dry(beta)
out.append(f"## 标定结果")
out.append("")
out.append(f"- **β = {beta:.4f}**")
out.append(f"- 标定后模型干燥时长 {t_dry_beta/3600:.2f} h（目标 {t_plateau/3600:.2f} h）")
out.append("")

json.dump({"beta": round(beta, 5), "t_plateau_h": round(t_plateau / 3600, 3),
           "t_dry_h": round(t_dry_beta / 3600, 3),
           "criterion": f"体积平均含水率降到 {C_TARGET} kg/kg"},
          open(os.path.join(WORK, "results", "E08_beta_calibration.json"), "w",
               encoding="utf-8"), ensure_ascii=False, indent=2)

open(os.path.join(WORK, "results", "E08_beta_calibration.md"), "w",
     encoding="utf-8").write("\n".join(out))
print("\n".join(out))
