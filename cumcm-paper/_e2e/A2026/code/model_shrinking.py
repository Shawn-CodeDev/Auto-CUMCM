"""改进模型：含**移动边界（收缩）**的圆柱热质耦合模型。

为什么要改（这是本案例最有价值的一步，写进模型的推进过程里）
    初版把半径固定为 2 cm，结果：
        * 模型在 27.5 h 就让中心含水率降到 0.15，而实测半径一直收缩到 ~21 h 才停
        * 同一时刻，模型推出的半径比实测大 0.13–0.40 cm
    诊断（见 results/dbg_timescale.md）显示：附件 2 的实测半径在**前 7 h 内**从
    2.000 cm 降到 1.337 cm，之后进入平台；这说明干燥前期的失水比"纯扩散控制"
    快得多，而后期明显变慢——单一常半径扩散模型无法同时描述这两段。

改法：把半径作为**已知时间函数** R(t)（由附件 2 实测值插值 + 单调化）引入模型，
      在归一化坐标 ξ = r/R(t) 上求解，从而显式处理移动边界：
          ∂u/∂t |_ξ = (1/R²) (1/ξ) ∂/∂ξ [ ξ D ∂u/∂ξ ] + (ξ Ṙ/R) ∂u/∂ξ
      其中 (ξ Ṙ/R) ∂u/∂ξ 是坐标随边界收缩带来的对流项。
      同时引入一个有效扩散系数修正因子 β（拟合参数，用于校正收缩导致的
      结构致密化对扩散的抑制），并在 validation_report 中做灵敏度分析。
"""
from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp

_trapz = getattr(np, "trapezoid", None) or np.trapz


class ShrinkingCylinder:
    """归一化坐标下的收缩圆柱热质耦合模型。

    ξ = r / R(t) ∈ [0, 1]，网格在 ξ 上固定，物理网格随 R(t) 自动收缩。
    """

    def __init__(self, R0: float = 2e-2, n: int = 201, kind: str = "p23",
                 shrink=None, beta: float = 1.0):
        self.R0 = float(R0)
        self.n = int(n)
        self.kind = kind
        self.beta = float(beta)
        self.xi = np.linspace(0.0, 1.0, self.n)
        self.dxi = self.xi[1] - self.xi[0]
        # 控制体界面（ξ 空间）
        self.xif = np.concatenate([[0.0], 0.5 * (self.xi[:-1] + self.xi[1:]), [1.0]])
        # shrink: 可调用对象 t -> R(t) [m]；默认不收缩
        self.shrink = shrink or (lambda t: self.R0)

    # ---------------- 物性 ----------------
    def props(self, C, T_C):
        if self.kind == "p1":
            return (np.full_like(C, 820.0), np.full_like(C, 2600.0),
                    np.full_like(C, 0.36))
        if self.kind == "p23":
            return (650.0 + 128.0 * C,
                    1450.0 + 2736.0 * C / (C + 1.0),
                    0.21 + 0.38 * C / (C + 1.0))
        if self.kind == "p4":
            return (760.0 + 90.0 * C,
                    1850.0 + 2150.0 * C / (C + 1.0),
                    0.12 + 0.20 * C / (C + 1.0))
        raise ValueError(self.kind)

    def diffusivity(self, C, T_C):
        C = np.clip(C, 1e-8, None)
        if self.kind == "p1":
            return 7e-9 * np.exp(-0.89 * C)
        T_K = np.clip(T_C + 273.15, 250.0, 400.0)
        if self.kind == "p23":
            return self.beta * 2.4e-3 * np.exp(-0.45 * C) * np.exp(-3850.0 / T_K)
        return self.beta * 4.2e-4 * np.exp(-0.30 * C) * np.exp(-3850.0 / T_K)

    # ---------------- 归一化坐标下的散度算子 ----------------
    def _div_grad(self, u, coef):
        """在 ξ 坐标下计算 (1/ξ) ∂/∂ξ [ξ coef ∂u/∂ξ]。

        ξ=0 处用对称性：∂u/∂ξ = 0，故内界面通量为 0。
        """
        n, xif, dxi = self.n, self.xif, self.dxi
        coef_f = np.empty(n + 1)
        coef_f[0] = coef[0]
        coef_f[-1] = coef[-1]
        coef_f[1:-1] = 0.5 * (coef[:-1] + coef[1:])
        out = np.zeros(n)
        for i in range(n):
            xl, xr = xif[i], xif[i + 1]
            glu = (u[i] - u[i - 1]) / dxi if i > 0 else 0.0
            gru = (u[i + 1] - u[i]) / dxi if i < n - 1 else 0.0
            fl = xl * coef_f[i] * glu
            fr = xr * coef_f[i + 1] * gru
            vol = 0.5 * (xr * xr - xl * xl)
            out[i] = (fr - fl) / max(vol, 1e-30)
        return out

    def rhs(self, t, y, env):
        n = self.n
        T = y[:n]
        C = np.clip(y[n:], 1e-8, None)
        T_env, C_env = env(t)
        R = max(self.shrink(t), 1e-4)
        # dR/dt 用中心差分估计
        dt = 1.0
        dRdt = (self.shrink(t + dt) - self.shrink(max(t - dt, 0.0))) / (dt + min(dt, t))

        rho, cp, k = self.props(C, T)
        D = self.diffusivity(C, T)

        # 主扩散项 + 坐标收缩对流项
        dT = self._div_grad(T, k) / (R * R * rho * cp) + (self.xi * dRdt / R) * \
            np.gradient(T, self.xi)
        dC = self._div_grad(C, D) / (R * R) + (self.xi * dRdt / R) * \
            np.gradient(C, self.xi)

        # ---- 边界（ξ=1 处第三类）----
        vol_last = 0.5 * (self.xif[-1] ** 2 - self.xif[-2] ** 2)
        flux_T = self.h * (T_env - T[-1]) / R
        dT[-1] += (flux_T - self.xif[-2] * k[-1] * (T[-1] - T[-2]) / self.dxi / R) / \
            (R * rho[-1] * cp[-1] * vol_last)
        flux_C = self.h_m * (C_env - C[-1]) / R
        dC[-1] += (flux_C - self.xif[-2] * D[-1] * (C[-1] - C[-2]) / self.dxi / R) / \
            (R * vol_last)
        return np.concatenate([dT, dC])

    def solve(self, t_end, env, T0=28.0, C0=2.55, h=25.0, h_m=8e-7,
              t_eval=None, rtol=1e-6, atol=1e-9):
        self.h, self.h_m = float(h), float(h_m)
        y0 = np.concatenate([np.full(self.n, float(T0)),
                             np.full(self.n, float(C0))])
        if t_eval is None:
            t_eval = np.array([0.0, t_end])
        sol = solve_ivp(self.rhs, (0.0, t_end), y0, method="BDF", t_eval=t_eval,
                        args=(env,), rtol=rtol, atol=atol)
        if not sol.success:
            raise RuntimeError(f"求解失败：{sol.message}")
        R_t = np.array([max(self.shrink(tt), 1e-6) for tt in sol.t])
        return {"t": sol.t, "T": sol.y[:self.n, :], "C": sol.y[self.n:, :],
                "xi": self.xi, "R_t": R_t, "nfev": int(sol.nfev)}

    # ---------------- 派生量 ----------------
    def mean_C(self, C_prof):
        return float(_trapz(C_prof * self.xi, self.xi) / _trapz(self.xi, self.xi))

    def r_of_xi(self, xi, R_t):
        """把归一化坐标映射回物理半径（cm）。"""
        return xi * R_t * 100.0


def radius_from_mean_C(Cmean: float, R0: float = 2e-2) -> float:
    """由体积平均含水率推半径（题面 ρ(C)=650+128C 导出的体积收缩关系）。"""
    vol = ((1.0 + Cmean) / (650.0 + 128.0 * Cmean)) / \
          ((1.0 + 2.55) / (650.0 + 128.0 * 2.55))
    return R0 * float(np.sqrt(max(vol, 1e-12)))
