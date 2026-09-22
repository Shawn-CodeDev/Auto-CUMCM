---
name: cumcm-figure
description: >-
  国赛（CUMCM）论文配图的契约式生产流程：先写"这张图要证明什么"，再决定面板、再写代码。
  适用于任何"画图/改图/审图"的请求——折线图、多面板组合图、机理示意图、灵敏度龙卷风图、
  热力图、三维曲面、帕累托前沿、网络图、雷达图，以及"图太丑""图看不出结论""图里中文乱码"
  "图注怎么写""这张图该不该放"这类问题。也用于把实验输出（E0x）转成论文级图片资产。
  触发场景包括：国赛/数学建模/美赛/研赛论文配图、P5 数据诊断图、P11 结果图、P12 灵敏度与
  验证图、P14 论文插图、以及需要 600 dpi / 矢量 / 中文字体 / 三线表配套的成图任务。
  不适用于：交互式网页图表（Plotly/Altair）、纯 EDA 探索图、以 Illustrator/Figma 为主的排版。
---

# 国赛论文配图（cumcm-figure）

把**证据**变成**论点**。一张国赛配图不是"把数据画出来"，而是"用一个视觉论证说服评委"。

这个 skill 存在的理由：绝大多数队伍的图失分不是因为不好看，而是因为
**图里没有结论**——画了 8 张图，评委看完不知道你想说什么。

---

## 第一动作：先立契约，再写代码

**在生成或修改任何绘图代码之前**，先产出下面这份契约（写在 `sop/project/figure_contract.md`
或直接回复里）。跳过这一步直接出图，是本 skill 最严重的误用。

```text
图编号：            图 3
核心结论：          一句话，必须带动词和方向（"混合整数模型把日成本降低 6.2%"）
                   ✗ 不合格："不同方案的对比"（没有动词、没有方向、没有结论）
图像原型：          quantitative-grid / schematic-led / multi-panel-composite / robustness-panel
面板映射：
  (a) 目的：        每个面板必须回答一个**独特**问题；覆盖它会不会削弱论证？会 → 删掉
  (b) 目的：
证据层级：         主证据（hero）/ 对照与基线 / 稳健性
数据来源：         E0x 实验编号 + 结果文件路径（必须能追到 P11 登记表）
支撑结论编号：     C0x（来自 P13 账本；写不出来说明这张图不该存在）
统计要素：         n / 重复次数 / 中心统计量 / 离散度量 / 检验方法
图注草稿：         caption 要能让读者不看正文就懂这张图
审稿风险：         恶意评委最可能攻击这一点是什么？
最终尺寸：         单栏 ~8cm / 通栏 ~16cm；正文高度预算
```

### 契约的三条硬规则

1. **每张图必须绑定一个 C 编号（结论编号）**。
   这就是 P13 `claim_ledger.md` 的作用。绑不上任何结论的图 = 装饰品 = 占用 30 页额度 = 删掉。

2. **每个面板必须承载独有的证据**。
   自检问法："如果我把 (c) 盖住，论证会变弱吗？"不会 → 合并或删除。
   国赛正文限 30 页，**图占地就是文字让位**。

3. **一张图只有一个核心结论**。
   想表达两个结论 → 拆成两张图，或者明确分成 hero 面板与支撑面板（不等大）。

---

## 图像原型选择

| 原型 | 什么时候用 | 国赛典型题 |
|---|---|---|
| `quantitative-grid` | 结论主要是数值比较 | C 题回归对比、E 题指标排序 |
| `schematic-led` | 必须先理解系统/流程/机理 | A 题传热机理、框架图、算法流程 |
| `multi-panel-composite` | 图 + 表 + 示意 + 多子图组合 | 结果总览图（一图看懂全部答案） |
| `robustness-panel` | 灵敏度/稳健性/误差分析 | 龙卷风图、灵敏度曲线、收敛曲线 |
| `spatial-mechanism` | 二维/三维空间演化 | B 题定位、A 题温度场、几何遮蔽 |

**hero 面板原则**：优先"一个主导面板 + 若干从属面板"，而不是把画布切成等大子图。
等大子图暗示所有证据同等重要——这通常不是事实，也会让读者找不到重点。

---

## 国赛专属约束（与 Nature 投稿不同，务必按这套走）

| 维度 | 国赛要求 | 说明 |
|---|---|---|
| **语言** | 中文图题、中文轴标签、中文图例 | 专有名词可保留英文（NIPT、SEM、ARIMA） |
| **字体** | 中文字体必须正确嵌入 | 用 `SimHei`/`Microsoft YaHei`/`Source Han Sans`；**必须处理负号** |
| **分辨率** | 线条图矢量优先，位图 ≥ 600 dpi | PDF 嵌入矢量最佳；PNG 用 600 dpi |
| **尺寸** | 通栏 16cm = 模板 `\textwidth`；单栏 8cm | 依据 `cumcmthesis.cls` 的 `\geometry{left=25mm,right=25mm}` 与 A4 宽 21cm 算出。**插图优先写 `width=\linewidth`**，让 LaTeX 自己取 16cm；出图时按 16cm 画，缩放到 `\linewidth` 才不会二次压缩 |
| **图题位置** | 图题在图**下方**；表题在表**上方** | 与三线表规范配套 |
| **可读性** | 最小组件字号 ≈ 正文的 80% | 缩放到最终尺寸后仍要能读 |
| **配色** | 避免纯红绿对立；灰度打印仍可区分 | 评委可能黑白打印 |
| **图注** | 自解释：含单位、n、误差棒定义 | 见 `references/figure-qa-contract.md` |
| **数据可追溯** | 每张图能追到 E0x 实验编号 | 见 `references/figure-qa-contract.md` |

> ⚠️ **中文乱码是国赛最常见的低级失分**。默认 matplotlib 不含中文字体且负号会变方块。
> 直接用 `scripts/cumcm_style.py` 里已验证的配置，不要手搓 `rcParams`。

---

## 工作流

### 第 1 步：立契约
读 P12 `validation_report.md` 与 P11 `experiment_registry.md`，为每张计划中的图填契约。
**先确认结论，再确认数据来源，最后才谈画法。**

### 第 2 步：查图型
不确定用什么图 → 读 `references/chart-families.md`（按"你要传达什么"反查图型）。
想要配色与排版基调 → 读 `references/design-theory.md`。

### 第 3 步：出图
用 `scripts/cumcm_style.py` 的统一风格层，禁止每个脚本各写一套 `rcParams`：

```python
import sys; sys.path.insert(0, r"<skill_dir>/scripts")
from cumcm_style import apply_cumcm_style, save_cumcm_figure, PALETTE, panel_label

apply_cumcm_style()                       # 中文字体 + 负号 + 去上右边框 + 字号
fig, axes = plt.subplots(1, 3, figsize=(17/2.54, 5.5/2.54))   # 通栏，单位英寸
...                                        # 你的绘图逻辑
panel_label(axes[0], "a")                  # 面板标签
save_cumcm_figure(fig, "results/figures/E04_sensitivity")     # 同时出 .pdf + .png(600dpi)
```

`save_cumcm_figure` 会同时产出矢量 PDF（进论文）与 600 dpi PNG（进支撑材料/预览），
并做一次基础自检（字号、留白、文件大小）。

### 第 4 步：终检
交付前逐条过 `references/figure-qa-contract.md` 的检查表。
**必须打开导出的 PDF 实际看一眼**——"代码跑通了"不等于"图能读"。

### 第 5 步：写入论文
图题与图注模板见 `references/figure-caption.md`。
LaTeX 插图与尺寸控制见 `references/latex-integration.md`。

---

## 面板逻辑：默认阅读顺序

除非题目故事线另有要求，按这个顺序排布：

1. **建立系统**——样本、场景、坐标系、实验设置，让读者知道在看什么
2. **主效应**——最核心的那个对比/最优解/预测结果
3. **机理或定位**——为什么是这个结果
4. **量化**——把定性的观察变成数字
5. **稳健性**——参数扰动、换方法、换数据子集

第 1 个面板通常定义整张图的**视觉词汇**（颜色、符号、方向、类别）。
这个词汇要在整张图、乃至整篇论文里保持一致。

---

## 配色与排版基线

- **一个中性家族 + 一个信号家族 + 一个强调家族**，不要超过三个色系。
- 同一方案/方法在所有面板中用**同一颜色**。
- 类别固定或空间固定时优先**直接标注**，而不是图例（减少视线往返）。
- **不要**在密集数据区上叠图例、统计框、n 标注；放到轴外或用居中无框统计条。
- 不用彩虹色图（jet/rainbow）；有序数据用 `viridis`/`cividis`，发散数据用
  `RdBu_r`/`coolwarm` 并让 0 居中。
- 灰度可读性：颜色之外再加**线型**或**标记形状**区分。

---

## 什么时候不要用这个 skill

- 交互式网页图表（Plotly / Altair / Bokeh）
- 纯探索性 EDA（还在找数据规律，没有要证明的结论）
- 以 Illustrator / Figma 为主的图形设计
- 表格排版 → 用 `cumcm-table-figure`
- 机制示意图 / 流程图 / 算法框图 → 用 `cumcm-table-figure`

---

## 相关文件

| 文件 | 什么时候读 |
|---|---|
| `references/figure-contract.md` | 需要把"我要画个图"翻译成结论/证据/面板映射时 |
| `references/chart-families.md` | 不知道该用什么图型时（按传达目的反查） |
| `references/design-theory.md` | 配色、字体、留白、排版比例、导出策略 |
| `references/cumcm-layout.md` | 单栏/通栏尺寸、多子图几何、跨页大图 |
| `references/figure-qa-contract.md` | 交付前终检（含国赛合规项与数据可追溯） |
| `references/figure-caption.md` | 写图题、图注、面板说明 |
| `references/latex-integration.md` | 插图、缩放、子图、浮动体、三线表配合 |
| `scripts/cumcm_style.py` | 统一风格层（中文字体/负号/配色/导出）；内含 `PALETTE` 配色方案 |
| `scripts/figure_check.py` | 自动检查导出图的字号、体积、字体嵌入、身份信息、近空图 |
| `scripts/demo_and_verify.py` | 端到端验证：出 4 张示范图 + 注入问题确认终检器有效 |
