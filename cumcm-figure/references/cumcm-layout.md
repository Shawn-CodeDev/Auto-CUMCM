# 国赛版面几何（cumcm-layout）

`SKILL.md` 规定"单栏 ~8cm、通栏 ~16cm"。本文把它落到本仓库模板的**真实数字**上，
并回答一个 30 页预算下最要紧的问题：**这张图吃掉多少正文空间。**

> 全部数字来自 `templates/cumcm-thesis/`：
> `cumcm2026.sty` 的 `\geometry{a4paper,left=2.5cm,right=2.5cm,top=2.5cm,bottom=2.5cm,headheight=15pt}`、
> `cumcmthesis.cls` 的 `\LoadClass[a4paper,12pt]{article}` 与 `\baselinestretch = 1.38`（`sty` 里又设 `\linespread{1.35}`）。

---

## 1. 三个标准宽度

| 名称 | 设计宽度 | `CM` 常量 | 在 16cm 版心里的占比 | 适用场景 | 单图信息量上限 |
|---|---|---|---|---|---|
| **三分之一栏** | 5cm | `CM.one_third` | 31% | 2–3 个并列的小倍数面板；单变量小图 | 1 条曲线 / 3 根柱 |
| **单栏** | 8cm | `CM.single_column` | 50% | 单图主结果、龙卷风图、收敛曲线、箱线对比 | ≤4 条曲线 / ≤6 根柱 |
| **半页** | 12cm | `CM.half_page` | 75% | 略宽的单一结果图、带标注的示意图 | ≤5 条曲线 |
| **通栏** | 16cm = `\linewidth` | `CM.double_column` | 100% | 多面板组合、热力图、网络图、三维场 | ≤6 条曲线 / ≤8 根柱 / 一套网格 |

> 四个宽度都按**模板真实版心 16cm** 设定，所以插图时缩放恒为 1.000，不需要任何字号补偿。
> 这一点很重要：早期版本按常识取 17cm 通栏，插入 `width=\linewidth` 会被缩到 94%，
> 9pt 的字变成 8.5pt，线宽也跟着变细——尺寸口径必须从模板算出来，不能凭感觉。

### 1.1 一个必须知道的事实：国赛论文是**单栏**排版

模板 `\LoadClass[a4paper,12pt]{article}` 没有 `twocolumn` 选项，所以：

- 版心宽度 = 21 − 2.5 − 2.5 = **16cm**，全文只有这一条宽度；
- **`figure*` 与 `figure` 在本模板下行为一致**（LaTeX 的 `\@dblfloat` 在单栏模式下退化为 `\@float`），
  不要指望用 `figure*` 让图"跨栏"；
- 更重要的推论：**单栏图并不省版面宽度，只省视觉重量。** 一张 8cm 宽的图仍然独占一整行的纵向空间，
  右侧 7.5cm 是空白。标准 `figure` 环境不提供文字环绕（模板未加载 `wrapfig`）。

因此"省版面"只有三条路：

1. **并排两张单栏图**（各 7.8cm，见 §5.3）——把两行高度压成一行；
2. **改用 `wrapfig`**（需要自己在导言区 `\usepackage{wrapfig}`，且浮动位置易失控，不推荐赶时间时用）；
3. **把图做矮**：同样的宽度下，5cm 高比 8cm 高省 5 行。

### 1.2 宽度错配的处理

| 你的设计宽度 | LaTeX 写法 | 实际缩放 | 补偿方式 |
|---|---|---|---|
| 5cm | `width=5cm`（**必须写固定值**） | 1.000 | 无 |
| 8cm | `width=8cm`（**必须写固定值**） | 1.000 | 无 |
| 12cm | `width=12cm`（**必须写固定值**） | 1.000 | 无 |
| 16cm | `width=\linewidth` | 1.000 | 无（推荐） |

> ❌ **最常见的尺寸错误**：单栏图写 `\includegraphics[width=\linewidth]{...}`。这会把它从 8cm 放大 2.00 倍，
> 图内 9pt 字变成 18pt——比正文（12pt）还大，线宽也被拉粗。**单栏/三子图一律写固定 cm 宽度。**

---

## 2. 多子图几何

### 2.1 等大子图（1×3，最省事）

```python
import matplotlib as mpl
from cumcm_style import apply_cumcm_style, save_cumcm_figure, CM, panel_label
apply_cumcm_style(base_size=9)

fig, axes = plt.subplots(1, 3, figsize=(16/2.54, 5.5*CM.cm),
                         gridspec_kw=dict(wspace=0.34))
for ax, lab in zip(axes, "abc"):
    panel_label(ax, lab)
save_cumcm_figure(fig, "results/figures/E05_sens_panels")
```

3 个面板、通栏 16cm、列间距 `wspace=0.34` → 单面板宽约 4.7cm。**已接近 5cm 下限**：
只适合"单变量小图 + 极短轴标签"。若轴标签是中文长词（"储能荷电状态"），改 1×2 或上下布局。

### 2.2 hero 横向不等大（1 宽 + 2 窄，最常用的国赛布局）

```python
fig = plt.figure(figsize=(16/2.54, 7*CM.cm))
gs = fig.add_gridspec(2, 6, hspace=0.45, wspace=0.62)
ax_a = fig.add_subplot(gs[:, :4])          # hero：左 2/3 宽，占满全高
ax_b = fig.add_subplot(gs[0, 4:])          # 支撑 1
ax_c = fig.add_subplot(gs[1, 4:])          # 支撑 2
panel_label(ax_a, "a"); panel_label(ax_b, "b"); panel_label(ax_c, "c")
```

hero 面板宽 ≈ 9.3cm，支撑面板宽 ≈ 4.7cm——支撑面板只放"一条曲线 / 一个排序"，不要放多序列对比。

### 2.3 hero 纵向不等大（上宽 + 下三窄）

```python
fig = plt.figure(figsize=(16/2.54, 8.5*CM.cm))
gs = fig.add_gridspec(2, 3, height_ratios=[1.30, 1.0], hspace=0.42, wspace=0.36)
ax_a = fig.add_subplot(gs[0, :])                       # 通栏 hero（时序总览）
ax_b, ax_c, ax_d = (fig.add_subplot(gs[1, i]) for i in range(3))
```

适合"总览 + 三个分解量"（如全天调度图 + 成本/SOC/紧急购电三张小图）。

### 2.4 共享图例面板（图例很大时）

```python
fig = plt.figure(figsize=(16/2.54, 5*CM.cm))
gs = fig.add_gridspec(1, 5, wspace=0.30)
axes = [fig.add_subplot(gs[0, i]) for i in range(4)]
ax_leg = fig.add_subplot(gs[0, 4]); ax_leg.set_axis_off()
h, l = axes[0].get_legend_handles_labels()
ax_leg.legend(h, l, loc="center left", frameon=False, fontsize=mpl.rcParams["font.size"] - 1)
```

> **国赛判断**：图例条目 ≤3 且很短时，用轴上方一行共享图例（`ncols=3, bbox_to_anchor=(0.5, 1.02)`）
> 比单开一个图例面板更省地方。只有图例 ≥6 条时才值得开面板。

### 2.5 内嵌放大（代替第 4 个面板）

```python
axins = ax_a.inset_axes([0.56, 0.56, 0.42, 0.40])      # [x0, y0, 宽, 高]（轴坐标）
axins.plot(t, soc, color="#2E5C8A", lw=1.1)
axins.set_xlim(18, 22); axins.set_ylim(8500, 11000)
axins.set_xticks([18, 20, 22]); axins.tick_params(labelsize=mpl.rcParams["font.size"] - 1.5)
ax_a.indicate_inset_zoom(axins, edgecolor="#4D4D4D", alpha=0.8)
```

内嵌框里的字号要减 1.5–2pt（否则内嵌框看起来比主图还重要），且**最多嵌一个**。

---

## 3. 面板标签的规范

`panel_label(ax, "a")` 的默认参数是 `dx=-0.12, dy=1.06`（轴外左上角、粗体、输出 `(a)`）。三种情形的用法：

| 情形 | 调用 | 位置理由 |
|---|---|---|
| 默认（左侧有空位） | `panel_label(ax, "a")` | 标签在 y 轴标签左上方，不压数据 |
| 左侧被 y 轴标签占满（如宽 y 标签 + 长刻度） | `panel_label(ax, "a", dx=0.02)` | 移到轴内左上角，必要时 `boxed=True` 加白底 |
| 面板上方还有共享图例/统计条 | `panel_label(ax, "a", dy=1.14)` | 抬高，避免与共享图例重叠 |
| 小倍数图（≥4 个面板） | `panel_label(ax, lab, size=mpl.rcParams["font.size"] + 1)` | 字号固定，不随面板缩小 |

四条规范：

1. **小写字母 + 圆括号**，全文统一 `(a)(b)(c)`；不要用 `a)`、`A`、`(A)` 混排。
2. **粗体**（`panel_label` 已设 `fontweight="bold"`），字号比轴标签大 1–2pt，印刷后 10–11pt。
3. **位置在所有面板中一致**：都用左上角，不要 (a) 在左上、(b) 在图内右下。
4. **标签与 LaTeX `\subcaption` 不能同时用**。图内已经用 `panel_label` 打了 `(a)(b)(c)`，
   就**不要**再用 `subcaption` 环境（会生成"图 3(a) (a) ..."这种双重编号）。
   国赛惯例是：**图内打标签，面板说明写在图注里**（`(a) ... (b) ...`，见 `figure-caption.md`）。

---

## 4. 高度预算：一张图吃掉多少正文

### 4.1 先算出模板的一行有多高

```text
正文可用高度 = 29.7 − 2.5(上) − 2.5(下) − 0.53(headheight 15pt) ≈ 24.2 cm，保守取 24.0 cm
行高（baseline skip） = 12 pt × 1.35 = 16.2 pt = 0.571 cm
每页行数 = 24.0 / 0.571 ≈ 42 行
每行字数 = 16 cm / (12 pt = 0.423 cm) ≈ 37 个汉字
一页纯正文 ≈ 42 × 37 ≈ 1550 字（含公式、段末余白后实际约 1200–1400 字）
```

### 4.2 一张图的总占高

图不只是图本身，还要加上图注与浮动体间距：

```text
图的总占高 = H_fig + H_caption + H_gap

H_caption：caption 用 font=small（≈11pt），行高 ≈ 0.46 cm
           2 行图注 ≈ 0.93 cm（单句/标准图注）
           3 行图注 ≈ 1.39 cm（组合图分面板说明）
H_gap：    caption skip 6pt(0.21cm) + 浮动体上下间距 textfloatsep 20pt(0.70cm) ≈ 0.91 cm

⇒ 标准口径：总占高 ≈ H_fig + 1.9 cm（2 行图注） / H_fig + 2.3 cm（3 行图注）
```

### 4.3 换算表（通栏 16cm 宽）

| 图高 H | 总占高（2 行图注） | 消耗正文行数 | 占一页 | 等量正文汉字 |
|---|---|---|---|---|
| 4 cm | 5.9 | 10.3 | 0.25 页 | ≈ 380 字 |
| 5 cm | 6.9 | 12.1 | 0.29 页 | ≈ 450 字 |
| **6 cm** | **7.9** | **13.8** | **0.33 页** | **≈ 510 字** |
| 7 cm | 8.9 | 15.6 | 0.37 页 | ≈ 580 字 |
| 8 cm | 9.9 | 17.3 | 0.41 页 | ≈ 640 字 |
| 10 cm | 11.9 | 20.8 | 0.50 页 | ≈ 770 字 |
| 12 cm | 13.9 | 24.3 | 0.58 页 | ≈ 900 字 |

**用一句话记住**：**每张 6cm 高的通栏图 ≈ 13.8 行 ≈ 0.33 页 ≈ 510 个汉字。**
一张图的代价，就是一段 500 字的论证。这就是 `SKILL.md` 说"图占地就是文字让位"的具体含义。

### 4.4 30 页正文的图表预算

```text
正文 30 页 ≈ 30 × 42 = 1260 行

推荐配额：
  图：8–12 张，平均高 6.5 cm → 平均 15 行/张 → 合计 120–180 行 ≈ 10%–14%
  表：5–8 张，平均 10 行表格 → 含表题与间距约 12 行/张 → 合计 60–96 行 ≈ 5%–8%
  图表合计 ≤ 22% 正文（276 行 / 1260）

超出 22% 时的止损顺序：
  ① 先删"绑不上 C 编号"的图（契约阶段就该拦住）
  ② 把等大 2×2 改成 hero 布局，通常能省 2–3 cm 高度
  ③ 把 8 张图里的 3 张合并成 1 张通栏多面板图（省 2 组图注 + 2 组间距 ≈ 8 行）
  ④ 最后才考虑减小图高——小于 5cm 高的多面板图基本读不了
```

**快速自检脚本**（在通栏图上量真实高度）：

```python
import matplotlib as mpl
fig.canvas.draw()
bb = fig.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
h_cm = bb.height * 2.54
print(f"图高 {h_cm:.2f} cm → 消耗约 {(h_cm + 1.9)/0.571:.1f} 行正文")
```

---

## 5. 四种特殊版面的具体尺寸

### 5.1 跨栏大图

在单栏文档里"跨栏"就等于"占满 16cm 版心"。有意义的做法只有一种：**通栏 + 多面板**，而不是把一张图拉宽。

```python
fig = plt.figure(figsize=(16/2.54, 9*CM.cm))
```

- 宽高比建议 **1.6:1 ~ 2.2:1**。9cm 高的通栏图消耗约 19 行（0.45 页），是"总览图"的上限。
- 超过 12cm 高的通栏图（≈ 0.58 页）只在"整页图"（结果总览、地图）时使用，且整篇论文**最多一张**。

### 5.2 竖排长图

- 尺寸：**8cm 宽 × 12～16cm 高**（`figsize=(CM.single_column, 14*CM.cm)`）。
- 适用：长时序（144 段全天轨迹）、上下堆叠 2–3 个共享 x 轴的面板、SOC + 电价 + 功率的三联图。
- 代价：14cm 高 ≈ 28 行 ≈ 0.66 页。**一篇论文里最多 1 张**。
- 竖排长图的 `hspace` 要小（共享 x 轴时 0.12–0.18），否则中间的白缝会把图切成三张。

```python
fig, axes = plt.subplots(3, 1, figsize=(CM.single_column, 13*CM.cm), sharex=True,
                         gridspec_kw=dict(hspace=0.16))
```

### 5.3 双子图并排

```text
版心 16cm = 图1 7.8cm + 间隙 0.4cm + 图2 7.8cm
```

```python
fig, axes = plt.subplots(1, 2, figsize=(16/2.54, 6*CM.cm), gridspec_kw=dict(wspace=0.42))
```

LaTeX 侧（`subcaption` 已在 `cumcm2026.sty` 中加载）：

```latex
\begin{figure}[htbp]
  \centering
  \begin{subfigure}[b]{0.48\linewidth}
    \includegraphics[width=\linewidth]{results/figures/E02_q2_plan.pdf}
    \subcaption{计划购电策略}\label{fig:plan-a}
  \end{subfigure}\hfill
  \begin{subfigure}[b]{0.48\linewidth}
    \includegraphics[width=\linewidth]{results/figures/E03_q2_compare.pdf}
    \subcaption{与基线的成本对比}\label{fig:plan-b}
  \end{subfigure}
  \caption{问题二的求解结果}\label{fig:plan}
\end{figure}
```

> ⚠️ **两条只能选一条**：用 `\subcaption` 就让 matplotlib 的 `panel_label` 空着（不要在图里打 `(a)`）；
> 用 `panel_label` 就在 `\caption` 里手写 `(a) ... (b) ...`。同时用会产生"图 4a (a)"。
> 国赛推荐后者——评委的习惯是图注里读面板说明。

### 5.4 三子图并排

- 各 (16 − 2×0.3)/3 = **5.13cm**，已低于 `CM.one_third`(5cm) 且接近 5cm 下限。
- 只放单变量小图（排序条形、单条曲线、3 根柱），轴标签用 ≤6 个汉字。
- 需要更多信息时改用 §2.3 的"上宽下三窄"，而不是把三张小图都拉宽。

---

## 6. 版面配合的三条纪律

1. **同一篇论文里，图宽只用三种值**（5.5 / 8.5 / 16cm）。混用 7cm、9cm、11cm 会让页面看起来参差不齐，
   也让人怀疑你没有统一的设计意图。
2. **图的宽度与它在论证中的地位对齐**：hero 图通栏，支撑图单栏，分解小图三分之一栏。
   宽度本身就是一种"重要性声明"，用错了比不用还糟。
3. **页数超了先删图，不要先缩图**。把 8cm 缩到 5cm 会让图内 9pt 字变成 5.6pt（不可读），
   而删掉一张绑不上 C 编号的图，损失为零。
