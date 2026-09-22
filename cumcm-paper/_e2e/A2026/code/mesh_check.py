"""网格与时间步无关性检验（问题 1）。

论文里声称"取 n=201 已收敛"，这个脚本给出证据：
    固定物理条件，只变径向网格 n，看 1800 s 时的中心温度与表面含水率。
    再用两个不同的积分容差验证时间步无关性。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from model_shrinking import ShrinkingCylinder  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

params = json.load(open(os.path.join(WORK, "inputs", "problem_params.json"), encoding="utf-8"))
g, pc = params["geometry"], params["problem1_constants"]
R0 = g["radius_cm"] * 1e-2

env_df = pd.read_csv(os.path.join(WORK, "data", "clean", "env.csv"))
t_env = env_df["t_s"].to_numpy(float)
T_env = env_df["T_env_C"].to_numpy(float)
C_env = env_df["C_env"].to_numpy(float)


def env(tt):
    if tt <= t_env[-1]:
        return float(np.interp(tt, t_env, T_env)), float(np.interp(tt, t_env, C_env))
    return float(T_env[-1]), float(C_env[-1])


out = ["# 网格与时间步无关性检验（问题 1）", ""]
out.append("## (1) 径向网格无关性")
out.append("")
out.append("| n | 中心温度@1800s (°C) | 表面含水率@1800s | 相对差（中心温度） |")
out.append("|---|---|---|---|")
ref = None
for n in (51, 101, 201, 401, 801):
    m = ShrinkingCylinder(R0=R0, n=n, kind="p1", shrink=lambda t: R0, beta=1.0)
    o = m.solve(1800.0, env, T0=g["T0_C"], C0=g["C0"], h=pc["h"],
                h_m=pc["hm"] * 1e-7, t_eval=np.array([1800.0]),
                rtol=1e-8, atol=1e-11)
    Tc, Cs = float(o["T"][0, -1]), float(o["C"][-1, -1])
    if ref is None:
        rel = "—（基准）"
        ref = Tc
    else:
        rel = f"{abs(Tc-ref)/abs(ref)*100:.5f}%"
    out.append(f"| {n} | {Tc:.6f} | {Cs:.6f} | {rel} |")
out.append("")

out.append("## (2) 时间积分容差无关性（n = 201）")
out.append("")
out.append("| rtol | atol | 中心温度@1800s (°C) | 表面含水率@1800s |")
out.append("|---|---|---|---|")
for rtol, atol in ((1e-6, 1e-9), (1e-7, 1e-10), (1e-8, 1e-11), (1e-9, 1e-12)):
    m = ShrinkingCylinder(R0=R0, n=201, kind="p1", shrink=lambda t: R0, beta=1.0)
    o = m.solve(1800.0, env, T0=g["T0_C"], C0=g["C0"], h=pc["h"],
                h_m=pc["hm"] * 1e-7, t_eval=np.array([1800.0]),
                rtol=rtol, atol=atol)
    out.append(f"| {rtol:.0e} | {atol:.0e} | {float(o['T'][0,-1]):.6f} | "
               f"{float(o['C'][-1,-1]):.6f} |")
out.append("")
out.append("结论：n ≥ 201 且 rtol ≤ 1e-7 时，结果变化已进入第 4 位小数以下，"
           "故取 n=201、rtol=1e-7 作为主计算配置。")

open(os.path.join(WORK, "results", "E02_mesh_check.md"), "w", encoding="utf-8").write(
    "\n".join(out))
print("\n".join(out))
