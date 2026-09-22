# 图型反查表（chart-families）

`SKILL.md` 叫你"按传达目的反查图型"，本文就是那张反查表。**先查表，再写代码**——国赛的图型选择错误比绘图错误贵得多。

> 用法：先在 §0 找到你的目的所在行，再跳到对应小节。每一节给「什么时候用 / 不要用 / 国赛常见误用」三栏 + 可直接复制的关键代码。
> 所有代码默认已执行 `apply_cumcm_style()`，并已 `from cumcm_style import PALETTE, CM`。

---

## 0. 你要传达什么 → 用什么图

| 你要传达的 | 首选图型 | 次选 | 千万别用 |
|---|---|---|---|
| A 比 B 好，好多少 | 分组柱状 / 条形排序 | 哑铃图 | 饼图 |
| 排序变了 / 名次互换 | 斜率图 | 哑铃图 | 两条并列柱 |
| 随时间的趋势、峰值位置 | 折线（+ 置信带） | 面积图 | 柱状图 |
| 两个量量纲不同但同步变化 | **拆成上下两个共享 x 轴的子图** | 双轴（慎用，见 §2.2） | 一条曲线两个 y 轴且都从 0 起 |
| 分布形状、离群点、组间重叠 | 箱线 / 小提琴 / 雨云图 | 直方 + 核密度 | 只画均值柱 |
| 两个变量的关系 + 拟合 | 散点（+ 回归线 + 置信带） | 六边形分箱 | 折线连点 |
| 多变量相关结构 | 相关热力图 | 成对散点矩阵 | 雷达图 |
| 构成占比随时间变化 | 堆积柱 / 堆积面积 | 桑基（流程有守恒时） | 饼图 |
| 二维参数网格上的目标值 | 热力图（+ 等高线） | 等高线 | 三维曲面（读数难） |
| 空间/场的方向性 | quiver 矢量场 | 流线 | 三维箭头 |
| 算法收敛了没有 | 收敛曲线（+ 多次运行包络） | 收敛曲线 + 表格 | 只写"程序收敛了" |
| 多目标权衡 | 帕累托前沿 | 平行坐标 | 加权求和后只画一个点 |
| 哪个参数最要紧 | 龙卷风图 | 灵敏度曲线族 | 一张表 |
| 可行域长什么样 | 可行域填充 + 约束边界 | 等高线 | 只给最优解一个点 |
| 节点—边结构、最短路 | 网络图 + 高亮路径 | 邻接矩阵热力图 | 无坐标的力导向图（国赛少见） |
| 多维指标综合评价 | 归一化条形排序 | 雷达图（附警告，见 §9） | 雷达图 + 面积填充 |

---

## 1. 比较类

| 图型 | 什么时候用 | 不要用 | 国赛常见误用 |
|---|---|---|---|
| **分组柱状** | ≤8 个类别 × 2～4 组，类别无序，结论是"哪个更高" | 类别 >8（改条形排序）；x 是连续量（改折线）；组数 >4（改小倍数图） | ① y 轴不从 0 起，把 6.2% 的差画成 3 倍高；② 同一方案在图 3 是蓝、图 5 是绿 |
| **条形排序** | 类别 >6 或类目名很长（中文尤其）；强调排序 | 类别有自然顺序（时间/温度）——排序会破坏顺序信息 | 不排序，按数据表原始顺序画；类目名竖排挤成一团 |
| **斜率图** | 只有两个时点/场景，要展示**名次互换**或"谁进步快" | 时点 ≥3（改折线）；类别 >7（线会缠住） | 拿它比较**不同量纲**的指标——斜率不可比，必须先归一化并在图注写明口径 |
| **哑铃图** | 同一批对象的"前 vs 后"，且更关心**差值与方向** | 组数少且差值大（分组柱更直观）；要展示分布（改箱线） | 两端点用纯红绿——黑白打印后分不出哪个是"前"；必须叠实心/空心标记 |

**分组柱状**（带基线对照的标准写法；下文代码均假设 `import numpy as np` 与 `import matplotlib.pyplot as plt` 已完成）：

```python
x = np.arange(len(cats)); w = 0.36
ax.bar(x - w/2, base, w, label="LP 基线",   color=PALETTE["neutral"][1], edgecolor="black", lw=0.5)
ax.bar(x + w/2, ours, w, label="本文 MILP", color=PALETTE["signal"][0],  edgecolor="black", lw=0.5)
ax.set_xticks(x); ax.set_xticklabels(cats); ax.set_ylabel("全天购电成本 / 元")
for xi, v in zip(x + w/2, ours):                    # 只给 hero 柱子标数
    ax.text(xi, v, f"{v:.0f}", ha="center", va="bottom", fontsize=8)
```

**条形排序**：

```python
order = np.argsort(vals)                    # 升序 → 从下往上画
ax.barh(np.arange(len(vals)), vals[order], color=PALETTE["signal"][0], height=0.7)
ax.set_yticks(np.arange(len(vals))); ax.set_yticklabels(np.array(labels)[order])
ax.set_xlabel("指标值 / 单位")
```

**斜率图**：

```python
for lab, a, b in rows:                       # rows: (名称, 左值, 右值)
    ax.plot([0, 1], [a, b], marker="o", ms=4, lw=1.4, color=col[lab])
    ax.text(-0.03, a, f"{lab} {a:.3f}", ha="right", va="center", fontsize=8)
    ax.text(1.03,  b, f"{b:.3f}", ha="left", va="center", fontsize=8)
ax.set_xlim(-0.55, 1.25); ax.set_xticks([0, 1]); ax.set_xticklabels(["基线", "本文"])
ax.set_ylabel("归一化指标"); ax.spines["left"].set_visible(False)
```

**哑铃图**：

```python
y = np.arange(len(labels))
ax.hlines(y, lo, hi, color=PALETTE["neutral"][2], lw=1.2, zorder=1)
ax.plot(lo, y, "o", ms=4.5, mfc="white", mec=PALETTE["neutral"][0], label="优化前")
ax.plot(hi, y, "o", ms=4.5, color=PALETTE["accent"][0],             label="优化后")
ax.set_yticks(y); ax.set_yticklabels(labels); ax.set_xlabel("日运行成本 / 元")
```

---

## 2. 趋势类

### 2.1 折线 / 带置信带

| 图型 | 什么时候用 | 不要用 | 国赛常见误用 |
|---|---|---|---|
| **折线** | x 是连续量（时间、参数），关心峰值/拐点/单调性 | x 是无序类别（那是柱状的活）；曲线 >6 条（改"基准 + 扰动带"或拆图） | ① 144 个时段画 6 条曲线，图例盖住数据；② 把最优点埋在曲线里不标；③ 平滑插值造出真实数据里不存在的振荡 |
| **带置信带** | 有重复运行/多场景扫描，要表达不确定度（仿真题、启发式题必配） | 只有一次运行却画出一条带（那是编的）；带太宽以至于看不出趋势还不说明 | `fill_between` 用高饱和实色把主曲线盖住——**α 取 0.15～0.25**，并让主曲线 `zorder` 更高 |

```python
ax.plot(t, T, color=PALETTE["signal"][0], lw=1.4, label="有效遮蔽时长")
annotate_extremum(ax, t[i], T[i], f"峰值 {t[i]:.2f} s\n{T[i]:.2f} s")   # 最优解必须一眼可见
add_stat_box(ax, "n = 144 时段，Δt = 10 min")                          # 统计条放轴上方，不压数据

ax.fill_between(t, lo, hi, color=PALETTE["signal"][1], alpha=0.20, lw=0,
                label="20 次运行区间")                                  # 置信带：低饱和 + 无边框
ax.plot(t, mid, color=PALETTE["signal"][0], lw=1.4, zorder=3, label="均值")
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncols=2, frameon=False)
```

### 2.2 双轴（twinx）——含误用警告

**先读这段再动手。** 双轴图可以让两条无关曲线"看起来相关"，这是国赛图里最容易被评委一句话打掉的图形。

只有**同时满足**下面三条才允许用双轴：

1. 两条曲线的 x 轴是**同一物理量**（同一时间轴、同一参数扫描轴）；
2. 二者有**明确的因果/派生关系**，且这个关系在正文里写清楚了（如"成本"与"最优定价"同为 c 的函数）；
3. 图注里**逐轴写明**量名与单位，且两侧轴的颜色与对应曲线颜色一致。

不满足就改用**上下堆叠、共享 x 轴**的两个子图（`sharex=True`），这几乎总是更好的选择：

```python
fig, (a1, a2) = plt.subplots(2, 1, figsize=(CM.single_column, 8*CM.cm), sharex=True)
a1.plot(cs, cost, color=PALETTE["signal"][0]); a1.set_ylabel("最大利润 / 元")
a2.plot(cs, p_opt, color=PALETTE["accent"][0]); a2.set_ylabel("最优定价 / 元")
a2.set_xlabel("单位进货成本 c / 元")
```

必须用双轴时，把两条轴的零点对齐（`ax2.set_ylim(0, ...)` 与 `ax1.set_ylim(0, ...)`），并在图注写明"左右轴零点已对齐"：

```python
ax2 = ax1.twinx()
ax2.plot(cs, p_opt, "s--", ms=3, color=PALETTE["accent"][0], label="最优定价 $p^*$")
ax1.set_ylabel("最大利润 / 元", color=PALETTE["signal"][0])
ax2.set_ylabel("最优定价 / 元", color=PALETTE["accent"][0])
ax1.tick_params(axis="y", colors=PALETTE["signal"][0])
ax2.tick_params(axis="y", colors=PALETTE["accent"][0])
ax1.set_ylim(0, None); ax2.set_ylim(0, None)      # 零点对齐——不许偷懒
```

| 双轴误用 | 症状 | 后果 |
|---|---|---|
| 两条无关指标共用一根 x 轴 | 出货量与股价同图 | 读者会脑补出并不存在的因果 |
| 只调一侧零点 | 左轴从 0、右轴从 38000 | 差异被放大或抹平，属于**数值误导** |
| 两条曲线同色 | 分不清哪条对哪个轴 | 图注写再多也没人看 |
| 用双轴代替子图 | 8 条曲线挤在 4 根轴上 | 信息量不升反降 |

---

## 3. 分布类

| 图型 | 什么时候用 | 不要用 | 国赛常见误用 |
|---|---|---|---|
| **直方图** | 单变量分布形状、偏度、双峰 | 样本 <30（形状是噪声）；要比较多个组（会叠成一团） | 箱数随手写 `bins=10`；不写组距；把不同 n 的组放在同一密度尺度 |
| **核密度（KDE）** | 分布平滑展示、需要叠加多组 | 数据有物理边界（如 SOC ≥ 0）却让 KDE 越过边界 | 带宽用默认值，把双峰抹成单峰——**试 2～3 个带宽并说明选了哪个** |
| **箱线图** | 多组分布对比，关心中位数/四分位/离群点 | 组内样本 <5；要展示双峰（箱线图藏起双峰） | 不标 n；把离群点当错误删掉；用均值 ± 标准差代替箱线 |
| **小提琴图** | 组间分布形状差异明显，n ≥ 30 | 组数 >6（会变糊）；n 小（小提琴的平滑是假的） | 只画小提琴不画内部的箱/中位线——读不出数 |
| **雨云图（raincloud）** | 想同时展示原始点 + 分布 + 汇总量（最诚实） | 点数太多（>500 点会成黑带） | 散点不做 jitter，全部重叠成一条线 |

```python
# 箱线 + 原始点（推荐：既给汇总量，也给样本量证据）
bp = ax.boxplot(datasets, widths=0.5, patch_artist=True, showfliers=False,
                medianprops=dict(color="black", lw=1.2))
for patch, c in zip(bp["boxes"], colors):
    patch.set_facecolor(c); patch.set_alpha(0.55); patch.set_edgecolor("black"); patch.set_linewidth(0.6)
rng = np.random.default_rng(0)
for i, d in enumerate(datasets, start=1):
    ax.scatter(i + rng.uniform(-0.12, 0.12, len(d)), d, s=4, color="#4D4D4D", alpha=0.5, zorder=3)
ax.set_ylabel("单次运行的目标值 / s")
add_stat_box(ax, "每组 n = 20 次独立运行；箱体为四分位距，须线为 1.5×IQR")
```

> 分布类图的**第一纪律**：箱线/小提琴/雨云图都必须标 n。没有 n 的分布图在国赛里等于没画。

---

## 4. 相关类

| 图型 | 什么时候用 | 不要用 | 国赛常见误用 |
|---|---|---|---|
| **散点** | 两个连续量的关系、聚类结构、拟合优度 | 点 >5000（改六边形分箱/密度图）；x 是无序类别 | 全用不透明实心点，重叠成黑带；画了回归线不写 $R^2$ 与 n；用折线连散点 |
| **相关热力图** | 变量数 5～30 的两两相关结构 | 变量 <4（直接列表）；方阵不对称（说明算法写错） | 用 `jet` 色图；不发散居中（相关系数必须在 0 处对称）；不写数值只给颜色 |
| **成对散点矩阵** | 变量 3～8，想一次看完全部两两关系 | 变量 >8（图会碎成渣） | 下三角与上三角画重复的两遍（浪费一半画布） |

```python
# 散点：透明度 + 边缘描边 + 拟合线与 R²
ax.scatter(x, y, s=14, alpha=0.45, color=PALETTE["signal"][1], edgecolors="none")
ax.plot(xs, k*xs + b, color=PALETTE["accent"][0], lw=1.2)
add_stat_box(ax, f"n = {len(x)}，$R^2$ = {r2:.3f}，y = {k:.3f}x + {b:.2f}")
ax.set_xlabel("光伏出力预报 / kW"); ax.set_ylabel("实际出力 / kW")
```

```python
# 相关热力图：发散、0 居中、写数值、上三角留白
C = df.corr().values
im = ax.imshow(C, cmap=PALETTE["diverging"], vmin=-1, vmax=1)
mask = np.triu(np.ones_like(C, bool), k=1)      # 只保留下三角，避免重复信息
im.set_alpha(1.0); Cm = np.ma.array(C, mask=mask); im.set_data(Cm)
for i in range(len(C)):
    for j in range(i):
        ax.text(j, i, f"{C[i,j]:.2f}", ha="center", va="center", fontsize=7)
ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=45, ha="right")
ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels)
ax.set_frame_on(False); ax.tick_params(length=0)
fig.colorbar(im, ax=ax, shrink=0.8, label="Pearson 相关系数")
```

---

## 5. 组成类

| 图型 | 什么时候用 | 不要用 | 国赛常见误用 |
|---|---|---|---|
| **堆积柱** | ≤5 个成分随时间/类别变化，且关心"总量 + 结构" | 成分 >6；成分间会互相抵消（有正有负） | 相邻段亮度接近（黑白打印后分不清）；不标总量；把百分比堆积与绝对量堆积混在同一篇里 |
| **堆积面积** | 时序构成，且成分平滑连续 | 成分次序会变（交叉的面积图会撒谎） | 不按"平均占比"排序成分，导致面积交叉 |
| **饼图** | **几乎不用**。仅当：成分 ≤4、其中一块明显 >50%、且你要强调"这一块占了大半" | 需要比较多个饼；成分 >4；需要看趋势；需要精确读数 | 用 3D 饼图；用饼图比较 5 个时段；把"占比 3% 的项"也画出来 |
| **桑基图（概念）** | 有**守恒**的流动：电量从光伏/电网 → 储能 → 负载，各环节有损耗 | 没有守恒关系的数据（那只是分类）；节点 >15 | 用桑基图表达"比例"却让宽度不代表量——桑基图的核心语义就是宽度 = 量 |

**饼图的替代方案（国赛强烈建议）**：水平条形排序 + 累计线。理由：人眼比较角度/面积的精度远低于比较长度。

```python
order = np.argsort(vals)[::-1]
ax.barh(np.arange(len(vals))[::-1], vals[order], color=PALETTE["signal"][0], height=0.65)
for i, (v, s) in enumerate(zip(vals[order], shares[order])):
    ax.text(v, len(vals)-1-i, f"  {s:.1f}%", va="center", fontsize=8)
ax.set_xlabel("购电量 / kWh"); ax.set_yticks([])   # 类目名直接标注在条内，省一列
```

**堆积柱的黑白安全写法**：颜色之外再加填充纹理，且相邻段不要用相近亮度。

```python
hatches = ["", "//", "..", "xx", "\\\\"]
for k, (lab, c, h) in enumerate(zip(labels, colors, hatches)):
    ax.bar(t, series[k], bottom=bottom, color=c, label=lab,
           edgecolor="black", lw=0.4, hatch=h)
    bottom += series[k]
ax.set_ylabel("功率 / kW"); ax.set_xlabel("时段")
```

---

## 6. 空间 / 场类

| 图型 | 什么时候用 | 不要用 | 国赛常见误用 |
|---|---|---|---|
| **热力图（`imshow`/`pcolormesh`）** | 二维参数网格上的目标值 $(t_1,\theta)\mapsto T$ | 网格大部分为空（那是散点）；坐标不是等距（必须用 `pcolormesh` + 真实坐标数组） | 无 colorbar；colorbar 不写单位；用 `jet`；行列轴标签与数据转置错位（**画完必须核对一行真实数据**） |
| **等高线** | 需要精确读取等值线位置、要标出可行域边界 | 目标非连续；只有一条等值线 | 等值线不标数值 (`ax.clabel`)；线太密（改 `levels`)；不做 filled 与 line 的组合 |
| **三维曲面** | 真的有三维结构且旋转后有新信息（如峰值位置不直观） | **代替等高线读数**（曲面遮挡严重，读数难） | 视角选得让峰被挡；无 `colorbar`；`plot_surface` 用默认 100×100 网格导致文件巨大 |
| **quiver 矢量场** | 有方向性的场：速度场、梯度场、测向指向 | 向量大小差异 >100 倍（归一化或取对数） | 箭头太密成一团（用 `ax.quiver(..., scale=...)` 抽稀）；不画参考箭头 |

```python
# 热力图 + 等值线叠加：既能读数又能看结构
cs = ax.contourf(T1, T2, Z, levels=12, cmap=PALETTE["sequential"])
cl = ax.contour(T1, T2, Z, levels=6, colors="white", linewidths=0.6)
ax.clabel(cl, inline=True, fontsize=7, fmt="%.1f")
ax.plot(t1_star, th_star, "*", ms=9, color=PALETTE["accent"][0])   # 最优点必须标
ax.set_xlabel("投放时刻 $t_1$ / s"); ax.set_ylabel("航向角 $\\theta$ / (°)")
fig.colorbar(cs, ax=ax, label="有效遮蔽时长 / s")
```

```python
# quiver：先抽稀再画（step 控制密度），并加一个参考箭头表明尺度
s = 4
q = ax.quiver(X[::s, ::s], Y[::s, ::s], U[::s, ::s], V[::s, ::s],
              color=PALETTE["signal"][0], width=0.003)
ax.quiverkey(q, 0.9, 1.05, 10, "10 m/s", labelpos="E")
```

> **三维曲面的国赛判据**：如果评委在你的三维图上找不到峰值，你就欠他一张等高线。多数情况下**直接上等高线**更得分。

---

## 7. 优化专用

| 图型 | 什么时候用 | 不要用 | 国赛常见误用 |
|---|---|---|---|
| **收敛曲线** | 任何启发式算法（GA/SA/PSO/DE）——证明"收敛了"而不是"跑完了" | 精确求解器（LP/MILP 的最优性由对偶间隙证明，不需要收敛曲线） | 只画一条最好轨迹，读者无法判断稳定性——必须叠加多次运行的包络或至少一条最差轨迹 |
| **帕累托前沿** | 双目标（成本 vs 储能寿命、精度 vs 耗时），要展示权衡而非单一解 | 单目标问题硬造第二个目标；目标间可加权重化为一个（那就直接报加权结果） | 把被支配点也画成"前沿"；不标出最终选的那个折中点及其选择理由 |
| **龙卷风图** | 参数 ≥3 的 OAT 灵敏度排序——一张图告诉评委"哪个参数最要紧" | 参数 <3（用灵敏度表）；只扫了一个参数 | 只画正扰动或只画负扰动（丢掉不对称性）；不按影响排序；图里出现两个不同的基准 |
| **可行域** | 2 维决策变量的优化题——让评委"看见"约束怎么把最优解挤到角点/边界 | 决策变量 ≥4 维（画不出来，用约束余量表代替） | 只画约束线不填充可行域；无等值线，看不出目标往哪边增；不标最优解与紧约束 |

**收敛曲线**（`convergence_plot` 已给单条曲线，稳定性证据要自己叠）：

```python
ax = convergence_plot(hist_best, label="DE（最好一次）")
ax.plot(range(1, len(hist_worst)+1), hist_worst, ls="--", lw=1.0,
        color=PALETTE["neutral"][1], label="DE（最差一次）")
ax.axhline(lp_bound, ls=":", lw=1.0, color=PALETTE["accent"][0], label="LP 松弛下界")
annotate_extremum(ax, len(hist_best), hist_best[-1], f"收敛于 {hist_best[-1]:.0f} 元")
ax.legend()
```

**帕累托前沿**（必须标出你最终选的那个折中点）：

```python
ax.plot(pf_cost, pf_life, "o-", ms=3, lw=1.0, color=PALETTE["signal"][0], label="Pareto 前沿")
ax.plot(cost_pick, life_pick, "*", ms=11, color=PALETTE["accent"][0], label="本文推荐折中解")
ax.annotate("成本上升 2% → 吞吐量下降 18%", xy=(cost_pick, life_pick), xytext=(12, 12),
            textcoords="offset points", fontsize=8, color=PALETTE["accent"][0],
            arrowprops=dict(arrowstyle="-", color=PALETTE["accent"][0], lw=0.8))
ax.set_xlabel("全天购电成本 / 元"); ax.set_ylabel("储能日吞吐量 / kWh")
```

**龙卷风图**（`tornado_chart` 已处理排序与零线，只需先排好序）：

```python
rows.sort(key=lambda r: max(abs(r[1]), abs(r[2])))       # 影响小的排下面
ax = tornado_chart([r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows],
                   title="参数 ±20% 对全天购电成本的影响")
ax.set_xlabel("成本相对基准的变化 / %")
```

**可行域**（等值线 + 最优解 + 紧约束，三者缺一不可）：

```python
ax.contourf(X, Y, Z, levels=14, cmap=PALETTE["sequential"], alpha=0.85)
ax.contour(X, Y, Z, levels=8, colors="white", linewidths=0.5)
ax.plot(x_opt, y_opt, "*", ms=11, color=PALETTE["accent"][0])
ax.annotate("紧约束", xy=(x_tight, y_tight), xytext=(-40, 14), textcoords="offset points",
            fontsize=8, arrowprops=dict(arrowstyle="->", lw=0.8))
ax.set_xlabel("充电功率 $c_t$ / kW"); ax.set_ylabel("放电功率 $d_t$ / kW")
```

---

## 8. 网络类

| 图型 | 什么时候用 | 不要用 | 国赛常见误用 |
|---|---|---|---|
| **网络图** | 节点—边结构：路径规划、供应链、关联分析、通信链路 | 展示数值大小（节点大小只能定性）；节点 >100 且无聚类（画出来是毛球） | 力导向布局不固定 `seed`（每次重跑图都不一样，不可复现）；不标源点/汇点；**最短路问题不给路径长度数值** |

**布局纪律**：国赛要求可复现——力导向必须固定 `seed`，题目自带坐标时**用真实坐标而不是力导向**。

```python
import networkx as nx
pos = nx.spring_layout(G, seed=2026, k=0.9)         # 必须固定 seed
nx.draw_networkx_edges(G, pos, edge_color=PALETTE["neutral"][2], width=0.8)
nx.draw_networkx_nodes(G, pos, node_size=90, node_color=PALETTE["neutral"][2],
                       edgecolors="black", linewidths=0.5)
nx.draw_networkx_edges(G, pos, edgelist=list(zip(shortest[:-1], shortest[1:])),
                       edge_color=PALETTE["accent"][0], width=2.0)     # 最短路径高亮
nx.draw_networkx_labels(G, pos, font_size=8)
add_stat_box(ax, f"最短路径长度 {total_len:.2f} km（Dijkstra，n = {G.number_of_nodes()} 节点）")
ax.set_axis_off()

# 题目自带坐标时（B 题定位/路径类）：
nx.draw_networkx(G, pos={n: (xy[n][0], xy[n][1]) for n in G}, ax=ax, node_size=40)
ax.set_aspect("equal"); ax.set_xlabel("东向坐标 / km"); ax.set_ylabel("北向坐标 / km")
```

---

## 9. 评价类：雷达图（以及它为什么会骗人）

### 9.1 三条必须先知道的缺陷

1. **面积会指数放大差异。** 感官量是"多边形面积"，而面积 ∝ 半径²：两个指标各高 20%，看起来多出 44% 的面积。
2. **指标顺序会改变形状。** 把 5 个指标的排列顺序换一下，同一方案会从"均衡"变成"畸形"。
3. **零点不唯一。** 各维量纲不同时必须归一化，而归一化下界取多少（0？60 分？队内最小值？）直接决定形状。

因此：**雷达图只能用于"自己跟自己比"的定性展示，不能用于"数值精度"论证。**

### 9.2 什么时候仍然可以用 / 用什么替代

同时满足三条才可以用：① 指标 4～6 个且已明确归一化到同一标尺（图注写明口径）；
② 只对比 1～2 个方案（3 个以上多边形会互相遮挡）；③ 结论是"更均衡/更偏科"这类定性判断，
而不是"高 12.3%"这类定量判断。

| 你的目的 | 替代图 | 为什么更好 |
|---|---|---|
| 5 个方案 × 6 个指标的排序 | 6 个小倍数条形图（`GridSpec` 1×6） | 长度比较精度远高于角度比较 |
| 方案的"偏科"程度 | 归一化得分 − 各维均值的发散条形图 | 直接读出"哪一维拖后腿" |
| 多指标综合评价 | 加权得分排序条形图 + 权重表 | 权重显式可见，可被检验 |

### 9.3 一定要用时的写法

```python
ang = np.linspace(0, 2*np.pi, n, endpoint=False)
closed = np.r_[ang, ang[0]]
ax = fig.add_subplot(111, projection="polar")
for vals, c, lab in series:
    v = np.r_[vals, vals[0]]
    ax.plot(closed, v, lw=1.4, color=c, label=lab)
    ax.fill(closed, v, color=c, alpha=0.08)          # 填充一律 ≤0.1，否则互相盖住
ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)   # 12 点起、顺时针
ax.set_xticks(ang); ax.set_xticklabels(names)
ax.set_ylim(0, 1); ax.set_yticks([0.25, 0.5, 0.75, 1.0]); ax.set_yticklabels([])
ax.grid(color="#BFBFBF", lw=0.5)
add_stat_box(ax, "各维已按极差归一化到 [0,1]；顺序固定为 成本→效率→寿命→可靠性→环保→响应")
ax.legend(loc="upper right", bbox_to_anchor=(1.32, 1.08))
```

图注里必须出现的一句：**"各维归一化到 [0,1]，指标顺序固定为……；雷达图面积不代表数值比例，仅用于比较偏科程度。"**

---

## 10. 选图型时最容易犯的三个错

1. **用图形掩盖数据的缺失。** 只有一次运行 → 画柱状不画箱线；只有一个参数 → 画灵敏度曲线不画龙卷风图。图形形状不能提供数据里没有的统计信息。
2. **一张图放两种坐标系。** 左右双轴、上下不同单位、内外圈不同尺度——每多一套坐标，读者多一次换算，多一次误读机会。
3. **按"我会画什么"选图。** 正确顺序永远是：核心结论 → 需要哪几个量 → 哪个图型让这几个量一眼可读。反过来的结果是一篇"图很丰富但看不出结论"的论文——这正是本 skill 存在的理由。
