"""诊断：模型干燥速率与实测半径收缩的时间尺度对不上，定位原因。

观测到的事实：
    * 模型在 ~27.5 h 就让中心含水率降到 0.15，72 h 时中心已到 0.050
    * 附件 2 的半径却一直收缩到 72 h 才停（2.000 -> 1.198 cm）
若物料在 27.5 h 就干了，半径不该继续收缩到 72 h。

本脚本量化几个候选原因：
    (a) 传质系数 h_m 是否使表面浓度被"钉"在 0（即边界是否处于扩散控制）
    (b) 用体积平均含水率反推的半径与实测半径在同一时刻差多少（收缩滞后）
    (c) 若把 h_m 缩小若干倍，干燥时长如何变化（灵敏度）
"""
import json
import os
import sys

import numpy as np
import pandas as pd

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


sys.path.insert(0, HERE)
from model import CylinderModel  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

params = json.load(open(os.path.join(WORK, "inputs", "problem_params.json"), encoding="utf-8"))
g = params["geometry"]
pc = params["problem1_constants"]
R = g["radius_cm"] * 1e-2

env_df = pd.read_csv(os.path.join(WORK, "data", "clean", "env.csv"))
t_env = env_df["t_s"].to_numpy(float)
T_env = env_df["T_env_C"].to_numpy(float)
C_env = env_df["C_env"].to_numpy(float)


def env(tt):
    if tt <= t_env[-1]:
        return float(np.interp(tt, t_env, T_env)), float(np.interp(tt, t_env, C_env))
    return float(T_env[-1]), float(C_env[-1])


def radius_from_mean_C(Cmean, R0=R):
    vol = ((1 + Cmean) / (650 + 128 * Cmean)) / ((1 + 2.55) / (650 + 128 * 2.55))
    return R0 * float(np.sqrt(max(vol, 1e-12)))


out = []

# ---------------- (a) 表面浓度时间历程 ----------------
o = CylinderModel(R=R, n=201, kind="p23").solve(
    72 * 3600, env, T0=g["T0_C"], C0=g["C0"], h=pc["h"], h_m=pc["hm"] * 1e-7,
    t_eval=np.array([0.5, 1, 2, 4, 8, 16, 24, 32, 48, 72]) * 3600.0,
    rtol=1e-7, atol=1e-10)
out.append("(a) 表面 / 中心 / 体积平均 含水率时间历程")
out.append("| 时间/h | C_env | C_surface | C_center | C_mean | 半径(推) cm |")
out.append("|---|---|---|---|---|---|")
for k, ts in enumerate(o["t"]):
    cm = o["C"][:, k]
    Cs, Cc = cm[-1], cm[0]
    Cmean = float(np.trapz(cm * o["r"], o["r"]) / np.trapz(o["r"], o["r"]))
    out.append(f"| {ts/3600:.1f} | {env(ts)[1]:.5f} | {Cs:.5f} | {Cc:.5f} | "
               f"{Cmean:.5f} | {radius_from_mean_C(Cmean)*100:.4f} |")
out.append("")

# ---------------- (b) 实测半径 vs 由实测/模型含水率推的半径 ----------------
rad = pd.read_csv(os.path.join(WORK, "data", "clean", "radius.csv"))
Cmean_t = np.array([float(np.trapz(o["C"][:, k] * o["r"], o["r"]) /
                          np.trapz(o["r"], o["r"])) for k in range(o["t"].size)])
r_model = np.array([radius_from_mean_C(c) for c in Cmean_t])
r_from_model = np.interp(rad["t_s"], o["t"], r_model)
out.append("(b) 实测半径 vs 模型含水率推出的半径（同一时刻）")
out.append("| 时间/h | 实测半径 cm | 模型推半径 cm | 差 cm |")
out.append("|---|---|---|---|")
for i in range(0, len(rad), max(1, len(rad) // 10)):
    out.append(f"| {rad['t_s'][i]/3600:.1f} | {rad['r_cm'][i]:.4f} | "
               f"{r_from_model[i]*100:.4f} | {(r_from_model[i]*100 - rad['r_cm'][i]):+.4f} |")
out.append("")

# ---------------- (c) h_m 灵敏度 ----------------
out.append("(c) 传质系数 h_m 对干燥时长的影响")
out.append("| h_m | 中心 C 到 0.15 的时长 h | 72h 中心 C | 72h 体积平均 C |")
out.append("|---|---|---|---|")
for scale in (0.02, 0.05, 0.1, 0.25, 0.5, 1.0):
    hm = pc["hm"] * 1e-7 * scale
    m = CylinderModel(R=R, n=101, kind="p23")
    te = np.arange(0, 72 * 3600 + 1, 600.0)
    oo = m.solve(72 * 3600, env, T0=g["T0_C"], C0=g["C0"], h=pc["h"], h_m=hm,
                 t_eval=te, rtol=1e-6, atol=1e-9)
    cc = oo["C"][0]
    idx = np.where(cc < 0.15)[0]
    tt = f"{oo['t'][idx[0]]/3600:.2f}" if len(idx) else "未达标"
    cm72 = float(np.trapz(oo["C"][:, -1] * m.r, m.r) / np.trapz(m.r, m.r))
    out.append(f"| {hm:.2e} (×{scale}) | {tt} | {cc[-1]:.5f} | {cm72:.5f} |")
out.append("")
out.append("说明：h_m 越小，表面浓度越高、传质阻力越大，干燥越慢。")

open(os.path.join(WORK, "results", "dbg_timescale.md"), "w", encoding="utf-8").write(
    "\n".join(out))
print("\n".join(out))
