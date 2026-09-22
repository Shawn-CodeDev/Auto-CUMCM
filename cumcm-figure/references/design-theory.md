# 制图设计理论（design-theory）

`SKILL.md` 给了配色与排版的**基线**（一个中性家族 + 一个信号家族 + 一个强调家族、去上右边框、不用彩虹色图）。
本文给的是**量化判据**：多大字号在 8cm 宽的图上还读得出来、灰度打印后两个颜色差多少才算分得开、
20MB 的论文 PDF 里每张图能花多少字节。

> 所有数值都以本仓库 `templates/cumcm-thesis/` 的实际排版参数为基准：
> `\LoadClass[a4paper,12pt]{article}`（正文 12pt）、`geometry` 四边 2.5cm（**`\textwidth = 16cm`**）、
> `\linespread{1.35}`、`\captionsetup{font=small,labelsep=quad,skip=6pt}`。

---

## 1. 排版比例与安全字号

### 1.1 尺寸口径（已与代码常量统一）

`cumcm_style.CM` 提供四个宽度常量，取值依据模板真实参数：

| 常量 | 值 | 用途 | 插图写法 |
|---|---|---|---|
| `CM.double_column` | **16cm** = `\textwidth` | 通栏图、多面板组合图 | `width=\linewidth`（缩放 1.000） |
| `CM.single_column` | 8cm | 半宽图、并排双图之一 | `width=8cm`（**必须写定宽**） |
| `CM.one_third` | 5cm | 三子图之一 | `width=5cm` |
| `CM.half_page` | 12cm | 介于单栏与通栏之间 | `width=12cm` |

> ⚠️ **单栏/三子图必须写固定宽度**（`width=8cm` / `width=5cm`），不能写 `width=\linewidth`。
> 后者会把 8cm 的设计放大到 16cm（2 倍），图内字号与线宽全部超标——
> 这是"图里的字比正文还大"这个经典丑图的第一成因。

反推公式（设计尺寸 ↔ 最终印在纸上的字号）：

```text
设计时字号 = 目标印刷字号 × (设计宽度 / 插入宽度)

例：按 16cm 设计、插图 width=\linewidth（16cm）→ 缩放 1.000，所见即所得
例：按 8cm 设计、误写 width=\linewidth（16cm）→ 缩放 2.00×，8pt 变 16pt
```

正常路径下缩放就是 1.000，所以**不需要任何字号补偿**——这也是把常量对齐到 16cm 的意义。

### 1.2 安全字号表

`apply_cumcm_style(base_size)` 的实际映射：`font.size = base_size`、轴标签 `= base_size`、
刻度/图例 `= base_size − 1`（来自 `cumcm_style.py` 的 rcParams）。下表给的是**印刷后**的目标值。

| 元素 | 8cm 单栏 | 16cm 通栏 | 5cm 三子图 | 下限 |
|---|---|---|---|---|
| 轴标签（量名 + 单位） | 8.5–9 | 9–10 | 8–8.5 | 8 |
| 刻度数字 | 7.5–8 | 8–9 | 7–7.5 | 7 |
| 图例文字 | 7.5–8 | 8–9 | 7–7.5 | 7 |
| 面板标签 `(a)` 粗体 | 9–10 | 10–11 | 9–9.5 | 8.5 |
| 图内数值/注释 | 7.5–8 | 8–9 | 7–7.5 | 7 |
| 统计条（`add_stat_box`） | 7.5 | 8–9 | 7 | 7 |
| colorbar 标签 | 8 | 8.5–9 | 7.5 | 7.5 |
| **硬下限** | **7** | **7.5** | **7** | — |

**对应的调用**：

```python
from cumcm_style import apply_cumcm_style, CM

apply_cumcm_style(base_size=9)                                   # 8cm 单栏
fig, ax = plt.subplots(figsize=(CM.single_column, 6*CM.cm))

apply_cumcm_style(base_size=10)                                  # 16cm 通栏多面板（面板多则字号上调）
fig, ax = plt.subplots(figsize=(CM.double_column, 9*CM.cm))

apply_cumcm_style(base_size=8)                                   # 5cm 三子图之一，最小字号降到 7
```

> **国赛的"80% 规则"**：图内最小组件字号 ≥ 正文（12pt）的 80% ≈ 9.6pt 是理想值，但通栏多面板图做不到。
> **务实的国赛口径是：图内最小刻度字号 ≥ 7.5pt，轴标签 ≥ 8.5pt。** 低于 7pt 时打印机会把它糊成一团，
> 靠提高 dpi 救不回来（dpi 只影响位图采样，不改变物理尺寸下的可辨识度）。

### 1.3 尺寸一致性检查

同一篇论文里，所有图的轴标签字号必须一致。做法是**不要在绘图脚本里手写 `fontsize=`**，而是引用 rcParams：

```python
import matplotlib as mpl
small = mpl.rcParams["font.size"] - 1        # 与刻度/图例同级
ax.text(..., fontsize=small)                 # 而不是 fontsize=8
```

---

## 2. 留白与信息密度

### 2.1 三条密度指标

| 指标 | 目标区间 | 偏低（空） | 偏高（挤） |
|---|---|---|---|
| 绘图区面积 / 画布面积 | 60–75% | < 55%：图显得空，LaTeX 里会自动（或被人为）放大 | > 85%：轴标签紧贴边缘，容易在 PDF 裁剪时被切 |
| 每面板数据元素数 | 2–6 条曲线 / 3–8 根柱 | 1 条：缺基线对照 | > 8：黑白打印后无法区分 |
| 最窄面板宽度 | ≥ 5cm | < 5cm：中文轴标签必须换行或缩写 | — |

测量最窄面板宽度的方法：

```python
fig.canvas.draw()
bb = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
print(f"面板宽 {bb.width*2.54:.2f} cm, 高 {bb.height*2.54:.2f} cm")   # 须 ≥ 5cm
```

### 2.2 什么时候该减面板

出现下列任一情况，按顺序执行 `合并 → 缩小 → 删除`：

1. **面板数 ≥ 6 且单个面板平均曲线数 < 2** → 改成小倍数图（1×N），共享一个 y 轴，只留最左一个轴标签。
2. **最窄面板 < 5cm** → 把 2×2 改成 1×3 或"1 宽 + 2 窄"（hero 布局）。
3. **图高 > 10cm（通栏）或 > 12cm（单栏）** → 版面代价超过它带来的信息（换算见 `cumcm-layout.md`）。
4. **两个面板的 y 轴量名相同** → 它们大概率是同一份证据的两次呈现，合并。

### 2.3 布局参数的建议值

```python
fig, axes = plt.subplots(1, 3, figsize=(CM.double_column, 5.5*CM.cm),
                         gridspec_kw=dict(wspace=0.32))    # 列间距：0.25–0.40
fig.subplots_adjust(hspace=0.35)                           # 行间距：0.30–0.45（有共享 x 轴标签时 0.15）
fig.tight_layout(pad=0.6)                                  # 收白边；pad 0.4–0.8
```

不要用 `constrained_layout=True` 与 `bbox_inches="tight"` 之外的手段收边——`save_cumcm_figure` 已经用
`bbox_inches="tight", pad_inches=0.02`，所以**不要**再手动 `subplots_adjust(left=0.2, right=0.8)` 去"留白"。

---

## 3. 配色理论

### 3.1 三家族与 `PALETTE` 的对应

| 家族 | `PALETTE` 键 | 语义职责 | 用量 |
|---|---|---|---|
| 中性 | `neutral[0..3]` = `#4D4D4D #8C8C8C #BFBFBF #E6E6E6` | 基线、背景、非重点系列、参考线 | 面积最大、视觉最安静 |
| 信号 | `signal[0..3]` = `#2E5C8A #4B8BBE #7FB3D5 #A9CCE3` | 主结果、本文方法 | 中等 |
| 强调 | `accent[0..3]` = `#C0392B #E67E22 #D4AC0D #1E8449` | 最优解、改进量、阈值、关键点 | **极少**，一次图里出现 1–2 处 |
| 多方法对比 | `compare[0..5]` | ≥5 个方法的类别色 | 仅当确实要区分 5–6 个方法时 |

四条纪律：

1. **一个方案在所有面板、所有图中用同一个颜色。** 做法是把颜色绑在语义上，不绑在绘制顺序上：
   ```python
   ROLE = {"ours": PALETTE["signal"][0], "lp_baseline": PALETTE["neutral"][1],
           "current": PALETTE["neutral"][2], "best": PALETTE["accent"][0]}
   ```
2. **强调色不得用于两个不同含义。** 红色既标"最优解"又标"越界点"，读者会以为最优解越界了。
3. **灰度可读性优先于美观。** 见 §3.3。
4. **不超过三个色系。** `compare` 的 6 色只在"真的要区分 6 个方法"时用；类别 ≥7 就应该换图型或拆图。

### 3.2 有序 vs 发散 vs 定性

| 数据类型 | 判据 | 色图 | 硬约束 |
|---|---|---|---|
| **有序（sequential）** | 值有大小方向，**没有自然中点**（时长、成本、浓度） | `viridis` / `cividis`（`PALETTE["sequential"]`） | 亮度必须单调；不要用 jet/rainbow |
| **发散（diverging）** | 有自然中点：0、基准值、均值（相对变化、残差、相关系数） | `RdBu_r` / `coolwarm`（`PALETTE["diverging"]`） | **中点必须落在数据的中性值上**，用 `TwoSlopeNorm` |
| **定性（qualitative）** | 类别无序（方案名、区域名） | `PALETTE["compare"]`（≤6 类） | 色相分隔但饱和度接近；相邻类亮度要拉开 |

```python
import matplotlib.colors as mcolors
# 相对变化（有正有负）：强制 0 居中，否则"看起来都变红了"
norm = mcolors.TwoSlopeNorm(vmin=-20, vcenter=0, vmax=20)
im = ax.imshow(delta, cmap=PALETTE["diverging"], norm=norm)
fig.colorbar(im, ax=ax, label="成本相对基准的变化 / %")
```

**为什么禁用 jet/rainbow**（评委可能黑白打印）：jet 的亮度沿色带**非单调**——蓝→青→黄→红的过程中亮度先升后降，
灰度化后会在绿色区出现一条并不存在的"亮带"，读者会以为那里有极值。`viridis` 的亮度单调递增，没有这个问题。

### 3.3 灰度可读性检验（可执行）

**判据**：任意两个需要被读者区分的类别，其相对亮度差 **≥ 0.08**（0–1 标尺）。
不足 0.08 就必须补线型、标记形状或填充纹理。

```python
def rel_lum(hexcolor: str) -> float:
    """sRGB 相对亮度（0–1）。判据：需要区分的两类之间 |ΔL| ≥ 0.08。"""
    h = hexcolor.lstrip("#")
    ch = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    ch = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]

from cumcm_style import PALETTE
sig, neu = PALETTE["signal"][0], PALETTE["neutral"][1]
print(f"signal[0] L={rel_lum(sig):.3f}  neutral[1] L={rel_lum(neu):.3f}  "
      f"ΔL={abs(rel_lum(sig)-rel_lum(neu)):.3f}")     # 需要 ≥ 0.08 才算分得开
```

**最省事的整体检查**：把导出的 PNG 直接转灰度，用眼睛过一遍（15 秒，能抓住 90% 的问题）。

```python
from PIL import Image
Image.open("results/figures/E02_q2_dispatch.png").convert("L").save("_gray_check.png")
print("打开 _gray_check.png：还能分辨出每一条曲线/每一类柱子吗？")
```

`PALETTE` 里需要特别注意的相邻对（灰度差偏小，必须配线型或标记）：

| 组合 | 问题 | 补救 |
|---|---|---|
| `signal[2]` 与 `signal[3]` | `#7FB3D5` 与 `#A9CCE3` 灰度接近 | 加 `--` / `:` 线型 |
| `neutral[2]` 与 `neutral[3]` | 浅灰对更浅灰 | 只用于背景层，不用于并列类别 |
| `compare[1]` `#C0392B` 与 `compare[2]` `#1E8449` | 红/绿在红绿色盲下几乎同色（且黑白下也接近） | 见 §4 的色盲检查 |

---

## 4. 线型与标记的可区分性

### 4.1 三通道编码

| 系列数 | 编码通道 | 具体 |
|---|---|---|
| 1–4 | 颜色 + 线型 | `["-", "--", "-.", ":"]` |
| 5–6 | 颜色 + 标记 | `["o", "s", "^", "D", "v", "P"]`，`markevery=8` 抽稀 |
| 7+ | —— | 拆图，或改成"均值线 + 区间带 + 少数关键曲线" |

```python
LS = ["-", "--", "-.", ":"]
MK = ["o", "s", "^", "D"]
for k, (lab, y) in enumerate(series):
    ax.plot(t, y, ls=LS[k % 4], marker=MK[k % 4], markevery=10, ms=3.5,
            color=PALETTE["compare"][k % 6], lw=1.3, label=lab)
```

### 4.2 线宽与标记的尺寸下限

| 元素 | 下限 | 说明 |
|---|---|---|
| 曲线线宽 | 0.9pt | 低于此值在 600dpi 位图上会断线；`apply_cumcm_style` 默认 1.4 |
| 柱边框 | 0.4pt | 用于区分同色相邻柱；`patch.linewidth` 默认 0.6 |
| 标记尺寸 | 3pt | 再小就变成一个点；默认 4 |
| 误差棒线宽 | 0.8pt，cap 2.5pt | cap 太小看不见 |

### 4.3 色盲友好检查

约 8% 的男性有红绿色觉异常。国赛评委里一定有。两个动作：

**动作 1｜近似模拟**（Viénot 1999 的线性近似，把 sRGB 当作线性空间使用；用于快速自查足够）：

```python
def deut_sim(hexcolor: str) -> str:
    """绿色盲（deuteranopia）近似模拟，返回 '#rrggbb'。"""
    h = hexcolor.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
    r2, g2, b2 = 0.625*r + 0.375*g, 0.700*r + 0.300*g, 0.300*g + 0.700*b
    return "#" + "".join(f"{int(round(min(max(c, 0), 1)*255)):02x}" for c in (r2, g2, b2))

from cumcm_style import PALETTE
for c in PALETTE["compare"]:
    print(c, "→", deut_sim(c))
# 若两个类别的模拟结果看起来一样 → 必须加线型/标记
```

**动作 2｜不依赖颜色的语义**（真正的保险）：

- 最短路/最优解：用**星号标记 + 直接标注文字**，而不是只靠红色；
- 组间对比：加填充纹理 `hatch=["", "//", "..", "xx"]`；
- 时序类别：加线型；
- 方向性（增加/减少）：用 `^` / `v` 标记或箭头，而不是只靠红/绿。

> **一条硬规则**：颜色**永远不能**是唯一的编码通道。任何一处"只有颜色不同"的区分，都必须再叠一个
> 线型、标记、纹理或直接标注。

---

## 5. 直接标注 vs 图例

### 5.1 取舍判据

| 判据 | 用**直接标注** | 用**图例** |
|---|---|---|
| 类别数 | ≤ 4 | 5–6 |
| 位置稳定性 | 每个系列有稳定的空白区（曲线末端、柱顶、区域中心） | 曲线互相穿插、无稳定空位 |
| 空间固定性 | 区域/通道/方位固定（地图分区、通道名） | 类别在图上位置随机 |
| 出现次数 | 同一词汇在多个面板重复出现（共享图例更省） | 只出现一次 |
| 遮挡风险 | 标注区无数据 | 图表已满，放不进任何标注 |

**国赛的默认选择**：类别固定时优先直接标注——它省掉读者的"颜色 → 图例 → 含义"两次视线往返，
在评委只给你 3–5 分钟翻图的前提下，这个省法很值钱。

### 5.2 图例位置的优先级（依次尝试）

```python
# ① 轴外右侧（最不遮挡数据；通栏图慎用，会挤压绘图区）
ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)

# ② 轴上方一行（多子图共享图例时最省地方）
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncols=3, frameon=False)

# ③ 轴内空白区（只有在①②都放不下时）
ax.legend(loc="upper left", framealpha=0.0)
```

**禁止**：`loc="best"`。它的落点在 matplotlib 版本间会变，同一篇论文里两张图的图例位置不一致，
是"没检查过"的直接信号。也**禁止**把图例、统计框、n 标注叠在密集数据区上——统计信息改用
`add_stat_box`（本质是 `set_title(loc="center")`，画在轴**上方**，不占绘图区）。

### 5.3 图内标题 vs 图题

**图内不要再写 `ax.set_title("图 3 ...")`**：图题已经由图下方的 `\caption` 承担，重复一次既浪费纵向空间，
又可能造成编号不一致（图内写"图 3"、LaTeX 编成"图 4"）。例外只有一个——多面板图里用极短的定位词
（"成本"、"SOC"），此时字号取 `font.size`，不加粗。

---

## 6. 导出策略与体积预算

### 6.1 矢量 vs 位图：判据表

| 图形内容 | 导出方式 | 单图典型体积 |
|---|---|---|
| 折线 / 柱状 / 散点 / 箱线 / 误差棒 / 网络图 | **PDF 矢量**（`save_cumcm_figure` 默认） | 20–200 KB |
| 热力图 / 等值线填色 / 三维曲面 / >5000 点的散点 | PDF + `set_rasterized(True)`，或 PNG 600dpi | 300 KB–1.5 MB |
| 密集网格填色（500×500 以上单元） | **必须**光栅化，否则 PDF 会记录每个单元 | 未光栅化时常 10–40 MB |
| 照片 / 截图类素材 | PNG 600dpi 或 JPEG（质量 90） | 200 KB–1 MB |

```python
cs = ax.contourf(X, Y, Z, levels=20, cmap=PALETTE["sequential"])
cs.set_rasterized(True)          # 只把色块光栅化；坐标轴、文字、标注仍是矢量（可选中）
fig.savefig("out.pdf")           # 必须在 set_rasterized 之后保存
```

### 6.2 字体嵌入

`apply_cumcm_style()` 已把 `pdf.fonttype = 42`（TrueType 子集嵌入）与 `ps.fonttype = 42` 设好。
**不要覆盖它**，也不要设 `pdf.fonttype = 3`（Type 3 位图字体，中文会变糊、不可搜索）。

导出后**逐张检查**（这是"打开 PDF 看一眼"的机器可查部分）：

```python
from pypdf import PdfReader
txt = PdfReader("results/figures/E02_q2_dispatch.pdf").pages[0].extract_text()
assert "时段" in txt, "PDF 内文字不可提取 → 字体未嵌入或被转成了路径"
```

命令行等价检查（装了 poppler 时更权威）：

```powershell
pdffonts results\figures\E02_q2_dispatch.pdf     # 每行 em 列必须为 yes
```

### 6.3 DPI

| 场景 | dpi |
|---|---|
| 屏幕预览 / 快速迭代 | 120（`figure.dpi`，`save_cumcm_figure` 不用于此） |
| 论文用位图（PNG 进 Word、或热力图 PDF 内嵌） | **600**（`save_cumcm_figure` 固定用 600） |
| 支撑材料附图 | 600 |
| 300 dpi 何时可接受 | 仅当图内最小字号 ≥ 9pt 且不含 < 0.5pt 的细线 |

**矢量图没有 dpi 概念**——把矢量 PDF 说成"600 dpi"是常见误解，评委不扣分，但你自己会被误导：
矢量图真正的质量风险是字体没嵌入和线宽太细，不是分辨率。

### 6.4 体积预算算法（论文 PDF ≤ 20MB，规则 `R-FILES`）

**预算分配**：

```text
论文 PDF 上限                            20.0 MB
  ├─ 骨架（正文文字、公式、三线表，全矢量）   0.3–1.0 MB
  ├─ 附录源码 listings（纯文本，压缩好）      ≈ 0.03 MB/页 × 15 页 ≈ 0.5 MB
  └─ 安全余量（留给你没预料到的东西）         5.0 MB
        ⇒ 图片预算 B_img = 20 − 1.0 − 0.5 − 5.0 ≈ 13.5 MB，取整为 12 MB

单图上限 = B_img / N_fig
    N_fig = 8  → 1.50 MB/图
    N_fig = 10 → 1.20 MB/图
    N_fig = 14 → 0.85 MB/图
```

**三条硬规则**：

1. **线条图只放 PDF 矢量。** 这类图典型 20–200 KB，永远不该触发预算。若某张折线图 > 500 KB，
   几乎一定是把大量散点或网格填色塞进了矢量层 → 加 `set_rasterized(True)`。
2. **热力图 / 等值线 / 三维曲面**按降级顺序处理：
   ① `set_rasterized(True)` → ② 降低数据分辨率（`Z = Z[::2, ::2]`，先确认等值线形状不变）→
   ③ 改导出 PNG 600dpi 嵌入 → ④ 拆分或删面板。
3. **单张图超过 1.2 MB 就当场回头优化。** 不要指望"十四张图加起来还没到 20MB"——
   附录源码、嵌入字体、公式图片都会吃预算。

**导出后立即断言**（`save_cumcm_figure` 返回各文件的字节数，正好用于这个检查）：

```python
from cumcm_style import save_cumcm_figure
sizes = save_cumcm_figure(fig, "results/figures/E02_q2_dispatch")

BUDGET = 1_200_000
assert sizes["pdf"] < BUDGET, f"单图超预算：{sizes['pdf']/1e6:.2f} MB > {BUDGET/1e6:.2f} MB"
```

**累计检查**（每加完 2–3 张图跑一次）：

```powershell
Get-ChildItem results\figures\*.pdf | Measure-Object Length -Sum |
  ForEach-Object { "{0:N2} MB / 12.00 MB" -f ($_.Sum/1MB) }
```

**最后一道闸**：论文编译完成后，`Get-Item paper\manuscript.pdf | % Length`。超过 12MB 就开始按上面的
降级顺序从最大的图开始处理——**先处理最大的那一张，不要平均主义**。

---

## 7. 十个"丑图"症状与改法

| # | 症状 | 一眼能看出的表现 | 改法（前 → 后） |
|---|---|---|---|
| 1 | **中文豆腐块** | 轴标签全是 `□□□` | 手写 `rcParams` → `apply_cumcm_style()`（它会挑本机真实存在的中文字体） |
| 2 | **负号变方块** | `-1` 显示成 `□1` | 加 `axes.unicode_minus=False`（`apply_cumcm_style` 已设） |
| 3 | **柱状图 y 轴截断** | 从 38500 起，6.2% 的差画成 3 倍高 | 改从 0 起 → 若必须截断，在 y 轴画断轴记号并在图注写明"纵轴自 38500 起"（这是数值诚信问题，不是美观问题） |
| 4 | **图例压数据** | 图例框盖住峰值或误差棒 | `loc="best"` → 轴外 `bbox_to_anchor=(1.02, 0.5)` 或轴上方一行 |
| 5 | **彩虹色迷雾** | 用了 `jet`，没有 colorbar | `cmap="jet"` → `viridis`（有序）/ `RdBu_r` + `TwoSlopeNorm`（发散），并加 `colorbar` 与单位 |
| 6 | **线条缠成一团** | 8 条曲线加 6 项图例 | 拆成 2–3 张 → 或改成"均值线 + 运行区间带 + 2 条关键曲线" |
| 7 | **三维曲面糊成一团** | 视角差、峰被挡、读不出数 | `plot_surface` → `contourf` + `contour` + `clabel`（先问：这个峰在等高线上找得到吗？找得到就不需要三维） |
| 8 | **散点成一条黑带** | 数据重叠，看不出密度 | 减小点 + `alpha=0.3` → 或改六边形分箱 / 密度热力图 |
| 9 | **图与图风格不一** | 图 3 的字比图 5 大，线也粗 | 每个脚本各写一套 `rcParams` → 全部走 `apply_cumcm_style()`，字号用 `rcParams["font.size"] ± 1` 引用 |
| 10 | **白边过大 / 图内标题与图题重复** | 图四周有大片空白；图里又写了一遍"图 3 ..." | 手动 `subplots_adjust` 留白 → 删掉，用 `save_cumcm_figure` 的 `bbox_inches="tight"`；删掉 `ax.set_title("图 3 ...")`，只保留 `\caption` |

### 附：改完之后的自检顺序（30 秒）

1. 打开导出的 **PDF**（不是 PNG，也不是 IDE 预览）；
2. 缩放到 **100%**（不是"适合页面"）——这才是它在纸上的真实大小；
3. 看三件事：图内最小的字读得出来吗？中文和负号正常吗？图例/标注挡住数据了吗？
4. 打印预览切黑白，再看一遍曲线能不能分开。

四步里任何一步不过关，就回到对应的小节改，别靠"再调调颜色"。
