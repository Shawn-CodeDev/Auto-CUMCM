"""S4/S5 圆柱药材烘干过程的热质耦合模型与求解器。

物理模型（轴对称有限圆柱，重点在径向）
    热量：ρ(C) c_p(C) ∂T/∂t = (1/r) ∂/∂r [ r k(C) ∂T/∂r ]
    水分：∂C/∂t      = (1/r) ∂/∂r [ r D(C,T) ∂C/∂r ]

边界条件（r = R 处与烘房环境耦合，第三类）
    k ∂T/∂r = -h (T_env - T_s)
    D ∂C/∂r = -h_m (C_env - C_s)
    中心 r = 0 处对称：∂T/∂r = ∂C/∂r = 0

初值
    T(r,0) = 28 °C，C(r,0) = 2.55 kg/kg（题面给定）

数值方法
    径向有限体积离散（保证圆柱面积权重守恒）+ 时间方向 method-of-lines，
    用 scipy.integrate.solve_ivp 的 BDF（问题刚性：热扩散时间尺度 ~10² s，
    质量扩散 ~10⁵ s，相差三个数量级，显式方法会被稳定性条件卡死）。

参数来源标注
    [题] = 题面给定（附录 2/3/4），[拟] = 由附件数据拟合，[假] = 本队假设
"""
from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp

# numpy 1.x 叫 trapz，2.x 改名为 trapezoid；这里做兼容，避免环境差异导致脚本崩
_trapz = getattr(np, "trapezoid", None) or np.trapz


class CylinderModel:
    """轴对称圆柱药材的热质耦合烘干模型。

    参数
    ----
    R : float           药材半径 [m]
    n : int             径向网格数（节点）
    kind : str          'p1' 用题面附录 2 的常数与 D(C)；
                        'p23' 用附录 3 的 C、T 依赖经验公式；
                        'p4'  用附录 4 的经验公式
    """

    def __init__(self, R: float = 2e-2, n: int = 101, kind: str = "p1"):
        self.R = float(R)
        self.n = int(n)
        self.kind = kind
        self.r = np.linspace(0.0, self.R, self.n)
        self.dr = self.r[1] - self.r[0]
        # 有限体积：节点 i 的控制体界面
        self.rf = np.concatenate([[0.0], 0.5 * (self.r[:-1] + self.r[1:]), [self.R]])

    # ---------------- 物性（按 kind 选择来源） ----------------
    def props(self, C: np.ndarray, T_C: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """返回 (rho, cp, k)。C 为干基含水率，T_C 为摄氏温度。"""
        if self.kind == "p1":
            # [题] 附录 2：常数物性
            rho = np.full_like(C, 820.0)
            cp = np.full_like(C, 2600.0)
            k = np.full_like(C, 0.36)
        elif self.kind == "p23":
            # [题] 附录 3
            rho = 650.0 + 128.0 * C
            cp = 1450.0 + 2736.0 * C / (C + 1.0)
            k = 0.21 + 0.38 * C / (C + 1.0)
        elif self.kind == "p4":
            # [题] 附录 4
            rho = 760.0 + 90.0 * C
            cp = 1850.0 + 2150.0 * C / (C + 1.0)
            k = 0.12 + 0.20 * C / (C + 1.0)
        else:
            raise ValueError(f"未知模型类型 {self.kind}")
        return rho, cp, k

    def diffusivity(self, C: np.ndarray, T_C: np.ndarray) -> np.ndarray:
        """水分扩散系数 D(C,T) [m²/s]。"""
        C = np.clip(C, 1e-6, None)
        if self.kind == "p1":
            # [题] 附录 2：D = 7e-9 exp(-0.89 C)
            return 7e-9 * np.exp(-0.89 * C)
        T_K = np.clip(T_C + 273.15, 250.0, 400.0)
        if self.kind == "p23":
            # [题] 附录 3：D = 2.4e-3 exp(-0.45 C) exp(-3850/T)
            return 2.4e-3 * np.exp(-0.45 * C) * np.exp(-3850.0 / T_K)
        # [题] 附录 4：D = 4.2e-4 exp(-0.30 C) exp(-3850/T)
        return 4.2e-4 * np.exp(-0.30 * C) * np.exp(-3850.0 / T_K)

    # ---------------- 空间算子 ----------------
    def _laplacian(self, u: np.ndarray, coef: np.ndarray) -> np.ndarray:
        """(1/r) d/dr [ r * coef * du/dr ] 的有限体积离散。

        用控制体界面上的通量做差分，保证圆柱几何下的守恒性
        （直接写 (1/r)∂/∂r(r ∂u/∂r) 在 r→0 处会出现 0/0）。
        """
        n, rf, dr = self.n, self.rf, self.dr
        out = np.zeros(n)
        # 界面上的系数取相邻节点算术平均
        coef_f = np.empty(n + 1)
        coef_f[0] = coef[0]
        coef_f[-1] = coef[-1]
        coef_f[1:-1] = 0.5 * (coef[:-1] + coef[1:])

        for i in range(n):
            rl, rr = rf[i], rf[i + 1]
            # 界面梯度（中心差分；边界处由调用方设置的虚拟梯度给出）
            glu = (u[i] - u[i - 1]) / dr if i > 0 else 0.0
            gru = (u[i + 1] - u[i]) / dr if i < n - 1 else 0.0
            flux_l = rl * coef_f[i] * glu
            flux_r = rr * coef_f[i + 1] * gru
            vol = 0.5 * (rr * rr - rl * rl)          # ∫r dr
            out[i] = (flux_r - flux_l) / max(vol, 1e-30)
        return out

    # ---------------- 右端项 ----------------
    def rhs(self, t: float, y: np.ndarray, env) -> np.ndarray:
        """y = [T_0..T_{n-1}, C_0..C_{n-1}]，返回 dy/dt。"""
        n = self.n
        T = y[:n]
        C = np.clip(y[n:], 1e-8, None)
        T_env, C_env = env(t)
        rho, cp, k = self.props(C, T)
        D = self.diffusivity(C, T)

        dT = self._laplacian(T, k) / (rho * cp)
        dC = self._laplacian(C, D)

        # ---- 边界：第三类（对流）----
        rl_vol = 0.5 * (self.rf[-1] ** 2 - self.rf[-2] ** 2)
        # 温度：k dT/dr = -h (T_env - T_s)  =>  界面通量
        flux_T = self.R * self.h * (T_env - T[-1])
        dT[-1] += (flux_T - self.rf[-2] * k[-1] * (T[-1] - T[-2]) / self.dr) / rl_vol
        # 水分：D dC/dr = -h_m (C_env - C_s)
        flux_C = self.R * self.h_m * (C_env - C[-1])
        dC[-1] += (flux_C - self.rf[-2] * D[-1] * (C[-1] - C[-2]) / self.dr) / rl_vol

        # 中心对称：r<0 侧无通量，_laplacian 里 i=0 已置 glu=0
        return np.concatenate([dT, dC])

    # ---------------- 求解 ----------------
    def solve(self, t_end: float, env, T0: float = 28.0, C0: float = 2.55,
              h: float = 25.0, h_m: float = 8e-7,
              t_eval: np.ndarray | None = None,
              rtol: float = 1e-6, atol: float = 1e-8) -> dict:
        """推进到 t_end 秒。env(t) -> (T_env_C, C_env)。"""
        self.h = float(h)          # [题] 对流换热系数 h = 25 W/(m²·K)
        self.h_m = float(h_m)      # [题] 对流传质系数 h_m = 8e-7 m/s
        y0 = np.concatenate([np.full(self.n, float(T0)),
                             np.full(self.n, float(C0))])
        if t_eval is None:
            t_eval = np.array([0.0, t_end])
        sol = solve_ivp(self.rhs, (0.0, t_end), y0, method="BDF",
                        t_eval=t_eval, args=(env,), rtol=rtol, atol=atol)
        if not sol.success:
            raise RuntimeError(f"求解失败：{sol.message}")
        T = sol.y[:self.n, :]
        C = sol.y[self.n:, :]
        return {"t": sol.t, "T": T, "C": C, "r": self.r, "success": sol.success,
                "nfev": int(sol.nfev)}

    # ---------------- 派生量 ----------------
    def mean(self, C: np.ndarray | None = None, field: np.ndarray | None = None) -> float:
        """按面积加权的径向平均值（圆柱面积权重 ∝ r）。"""
        f = C if field is None else field
        w = self.r
        return float(_trapz(f * w, self.r) / _trapz(w, self.r))

    def radius_from_mean(self, Cmean: float) -> float:
        """由平均含水率推半径（用于与附件 2 对比）。

        [假] 假设药材体积随干基含水率线性收缩：水的密度 1000 kg/m³、
        干物质密度由题面 ρ(C)=650+128C 反推。这是一个显式假设，
        P12 会对其做灵敏度分析。
        """
        rho_bulk = 650.0 + 128.0 * Cmean          # [题] 附录 3 的 ρ(C)
        # 干燥基质量守恒：ρ_bulk * V ∝ (1 + C) * const
        rho0 = 650.0 + 128.0 * 2.55
        ratio = ((1.0 + Cmean) / (1.0 + 2.55)) * (rho0 / rho_bulk)
        return self.R * float(np.sqrt(max(ratio, 1e-9)))
