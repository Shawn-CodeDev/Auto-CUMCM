# LaTeX 插图与版面配合（latex-integration）

`cumcm-figure` 只管到"导出一张合格的 PDF/PNG"为止；本文讲**从图片文件到论文 PDF** 这一段：
尺寸怎么写、浮动体怎么摆、图与表怎么分工、文件怎么组织。

> **本仓库模板的实际可用宏包**（`templates/cumcm-thesis/cumcm2026.sty`，配合 `cumcmthesis.cls`）：
> `geometry`（a4paper，四边 2.5cm ⇒ **`\textwidth = 16cm`**）、`amsmath/amssymb/mathtools`、
> `booktabs/array/tabularx/longtable/multirow`、`graphicx`、`float`、`caption`、`subcaption`、
> `enumitem`、`xcolor`、`listings`、`siunitx`、`microtype`、`titlesec`、`fancyhdr`；cls 里另有 `hyperref`、`ctex`。
> **未预加载**、需要自己 `\usepackage{}` 的常见包：`placeins`（`\FloatBarrier`）、`wrapfig`、`tikz`。

---

## 1. `\includegraphics` 的尺寸控制

### 1.1 三种写法，只用前两种

| 写法 | 何时用 | 结果 |
|---|---|---|
| `width=\linewidth` | **通栏图**（按 16cm 设计） | 缩放 1.000，所见即所得 |
| `width=8cm` / `width=0.5\linewidth` | **单栏图**（按 8cm 设计） | 缩放 1.000 |
| `width=5cm` / `width=0.31\linewidth` | **三分之一栏图** | 缩放 1.000 |
| `width=...,height=...,keepaspectratio` | 需要限制高度时（如竖排长图） | 取两者中较小的缩放比 |

```latex
\includegraphics[width=\linewidth]{E02_q2_dispatch}          % 通栏
\includegraphics[width=8cm]{E05_tornado}                   % 单栏，必须写固定值
\includegraphics[width=0.31\linewidth]{E06_soc_zoom}         % 三分之一栏
\includegraphics[width=\linewidth,height=13cm,keepaspectratio]{E07_soc_day}   % 竖排限高
```

### 1.2 为什么不要用 `scale=`

`scale=` 是相对**图片自身的"自然尺寸"**缩放的，而自然尺寸的判定规则在两种格式下不同，且会被外部工具悄悄改掉：

- **PDF**：自然尺寸是绘图盒的物理尺寸（pt，1pt = 1/72 in）。16cm 宽的图恒为 453.5pt。
- **PNG**：自然尺寸 = 像素数 ÷ 文件里记录的 dpi。matplotlib 会把 `savefig.dpi` 写进 PNG 的 pHYs 元数据
  （`save_cumcm_figure` 用 600），此时自然宽度同样是 16cm，与 PDF 一致；
  **但一旦这张 PNG 被编辑器另存、被截图、被聊天工具转发，dpi 元数据就会丢失**，
  graphicx 只能按 72 dpi 兜底——自然尺寸瞬间变成 8.33 倍（约 1.4 m 宽）。

于是同一个 `scale=0.5`：在刚导出的 PDF 上得到 8cm，在那张丢了元数据的 PNG 上得到 70cm。
更糟的是 `\includegraphics{name}` 不带扩展名时，graphicx 按 `.pdf → .png` 的顺序自动挑文件——
你昨天用 `scale` 调好的排版，今天因为补了一张 PNG 就崩了。

`scale` 的另外两个问题：① **与版心解耦**——换模板、换字号、换页边距后图宽不再匹配版心，
只能手工重调每一个 `scale`；② **不可审查**——图到底印多大，必须知道原图的 dpi 与像素数才能算出来，
而 `width=8cm` 一眼就能看出尺寸，也一眼就能看出它是否与图契约里写的"最终尺寸"一致。

**一条纪律**：`\includegraphics` 的宽度必须与图契约里的"最终尺寸"**逐字相同**。
这是图契约唯一能在 LaTeX 侧被机器核对的字段。

### 1.3 只写文件名（推荐用 `\graphicspath`）

```latex
\graphicspath{{../results/figures/}}     % 放在导言区
...
\includegraphics[width=\linewidth]{E02_q2_dispatch}    % 自动找 ../results/figures/E02_q2_dispatch.pdf
```

好处：正文里看不到长路径；图片目录搬家只改一行。
代价：不同目录下有同名图会歧义——所以 §6 的文件命名规范必须遵守。

---

## 2. 浮动体：`figure` / `figure*` / `subcaption`

### 2.1 `figure` 与 `figure*` 在本模板下没有区别

国赛模板是**单栏**文档（`\LoadClass[a4paper,12pt]{article}`）。LaTeX 的 `figure*`（双栏跨栏浮动体）
在单栏模式下会退化成普通 `figure`。所以：

- **不要指望用 `figure*` 让图"跨栏"**——宽度由 `\includegraphics` 的 `width` 决定，不由环境决定；
- 通栏 = `\includegraphics[width=\linewidth]`，就这么简单。

### 2.2 `subcaption` 的两种用法

**用法一：两个独立子图并排（各 7.8cm）**

```latex
\begin{figure}[htbp]
  \centering
  \begin{subfigure}[b]{0.48\linewidth}
    \includegraphics[width=\linewidth]{E02_q2_plan}
    \subcaption{计划购电策略}\label{fig:plan-a}
  \end{subfigure}\hfill
  \begin{subfigure}[b]{0.48\linewidth}
    \includegraphics[width=\linewidth]{E03_q2_compare}
    \subcaption{与基线的成本对比}\label{fig:plan-b}
  \end{subfigure}
  \caption{问题二的求解结果。(a) 全天功率平衡与储能荷电状态；
           (b) 与线性规划基线的成本对比。}\label{fig:plan}
\end{figure}
```

引用子图用 `\subref{}`：`如图~\ref{fig:plan}\subref{fig:plan-a} 所示`。

**用法二（国赛推荐）：不用 `subcaption`，用 `panel_label`。**
matplotlib 侧在每张图内用 `panel_label(ax, "a")` 打标签，LaTeX 侧就是普通 `figure`，
面板说明写在 `\caption` 里：

```latex
\begin{figure}[htbp]
  \centering
  \includegraphics[width=\linewidth]{E02_q2_plan}   % 图内已有 (a)(b)(c)
  \caption{问题二的最优购电与储能调度方案。(a) 全天 144 时段的功率平衡；
           (b) 储能荷电状态轨迹；(c) 三种方案的成本对比。$n=144$ 个时段，
           确定性求解。数据来自 E02、E03。}\label{fig:q2-plan}
\end{figure}
```

> ⚠️ **两条路只能选一条。** 图内已用 `panel_label` 打了 `(a)`，再用 `\subcaption{}` 就会渲染出
> "图 4a　(a) 全天功率平衡"。选 B 路线（`subcaption`）时，matplotlib 侧就不要打面板标签。

### 2.3 `subfigure` 不要用

`subfigure` 宏包自 2005 年起已废弃，与 `hyperref` 有不兼容记录。**用 `subcaption`**（模板已加载）。

---

## 3. 浮动位置：为什么图会"跑到很远的地方"

### 3.1 先理解机制

`[htbp]` 是**候选位置列表**（here / top / bottom / float page），不是命令。LaTeX 按 `h → t → b → p`
的顺序尝试，全部失败就把图推进队列，等后面的页面再放。三个常见原因：
① 图太大，当前页剩余空间放不下；② 触发浮动体配额（article 默认每页顶部 2 个、底部 2 个、总数 3 个）；
③ 触发面积比例限制（默认 `\topfraction = 0.7`、`\textfraction = 0.2`）。

### 3.2 解决顺序（从最推荐到最不推荐）

**① 先接受它。** 学术排版里图随文浮动、由 `\ref` 引导阅读，是正常且专业的做法。
正文写"如图~\ref{fig:q2-plan} 所示"就够了——评委不会因为图在第 5 页而下拉一页去找。

**② 放宽配额（放导言区，一行见效）**：

```latex
\renewcommand{\topfraction}{0.9}\renewcommand{\bottomfraction}{0.8}
\renewcommand{\textfraction}{0.07}\renewcommand{\floatpagefraction}{0.75}
\setcounter{topnumber}{3}\setcounter{bottomnumber}{2}\setcounter{totalnumber}{4}
```

**③ 用 `[H]` 强制"就地放置"**（`float` 宏包，模板已加载）：

```latex
\begin{figure}[H]
```

代价是可能在本页留下大片空白——30 页预算下要慎用。**只在"图必须紧跟某段推导"时用**（如算法流程图）。

**④ 用 `\FloatBarrier` 在节末清空浮动队列**（需要 `placeins`，**模板未预加载**）：
导言区 `\usepackage{placeins}`，在每节末尾写 `\FloatBarrier`，保证图不跨节漂移。

**⑤ `\clearpage`**：粗暴但完全可控，会把此前所有浮动体立即输出。适合章节之间。

> **国赛建议**：用 ② + `[htbp]`。只有"图跑到下一节"这类真问题时才上 ③ 或 ④，
> 因为 ③④ 都会牺牲版面密度，而 30 页预算很紧。

### 3.3 图表编号错乱的自查

三条：① 没有手写编号（正文里的"图 3"应全部改成 `\ref`）；② `\label` 必须在 `\caption` **之后**
（写在之前会引用到上一张图的编号）；③ 编译两次（`xelatex → xelatex`）才能解析 `\ref`。

---

## 4. 三线表：`booktabs`（与 `cumcm-table-figure` 的接口）

图和表在国赛里是一套东西，共享四条约定：**表题在上 / 图题在下**、**编号连续且用 `\label`/`\ref`**、
**数字口径统一（`claim_ledger.md` 第 5 节）**、**正文必须有解读**。排版本身交给 `cumcm-table-figure`，
本文只给"图与表放在一起时"的边界纪律：

| 项 | 规范 |
|---|---|
| 线 | 只有 `\toprule` / `\midrule` / `\bottomrule`；**不要竖线**，不要每行都画横线 |
| 表题位置 | `\caption` 写在 `\begin{tabular}` **之前**（模板已设 `\captionsetup[table]{position=top}`） |
| 单位 | 写在表头："量名 (单位)"；用 `siunitx` 的 `\si{}` 统一 |
| 对齐 | 文字列左对齐，数字列用 `S` 列按小数点对齐 |
| 分工 | **同一个数不要既画成图又列成表**。图和表要么是"总览 vs 细节"，要么是"趋势 vs 精确值"，不能是同一份数据的两种呈现 |

```latex
\begin{table}[htbp]
  \centering
  \caption{三枚干扰弹的最优投放方案}\label{tab:q2-plan}
  \begin{tabular}{l S[table-format=3.2] c S[table-format=1.2]}
    \toprule
    干扰弹编号 & {投放时刻 $t_{1,i}$ (s)} & 起爆点 (m) & {有效时长 (s)} \\
    \midrule
    1 & 115.62 & $(0,\ 0,\ 1662)$ & 1.05 \\
    2 & 127.48 & $(0,\ 0,\ 1611)$ & 2.15 \\
    3 & 139.35 & $(0,\ 0,\ 1558)$ & 1.12 \\
    \midrule
    合计（并集） & {—} & — & \bfseries 4.62 \\
    \bottomrule
  \end{tabular}
\end{table}
```

> `S` 列里的表头要用 `{}` 包住（否则 `siunitx` 会尝试把表头也当作数字解析）。

**图与表的分工判据**：

- 图擅长：趋势、形状、离群点、空间分布、多组对比的"一眼可读"；
- 表擅长：精确数值、多列属性、约束余量、符号说明；
- 判据一句话：**"评委需要看出趋势还是需要读出数字？"** 只有后者才用表。
  两者都要时，图给趋势 + 表给关键点，且**不要**把表里的 20 个数全部标到图上。

---

## 5. 编号与 `\label` / `\ref` 规范

### 5.1 前缀约定（全文统一）

| 对象 | `\label` 前缀 | 引用写法 |
|---|---|---|
| 图 | `fig:` | `如图~\ref{fig:q2-plan} 所示` |
| 表 | `tab:` | `结果见表~\ref{tab:q2-plan}` |
| 公式 | `eq:` | `由式~\eqref{eq:obj} 可得` |
| 章节 | `sec:` | `详见第~\ref{sec:validation} 节` |

- **`~` 不能省**：它把"图"与编号绑在一起，防止在行末被拆开（"图"在行尾、编号在下一行）。
- **`\label` 必须紧跟在 `\caption` 之后**（或其后同一个环境内）。写在 `\caption` 之前会引用到上一个编号。
- **禁止手写编号**：`\caption{图 3 各方案对比}` 会渲染成"图 3　图 3 各方案对比"，
  且插入新图后编号全部错位。P15 红队把"图表与文字不对应"列为表述分硬伤。

### 5.2 公式编号

模板（`article` 基类）默认**全文连续编号**。`paper_writing.md` §8.1 推荐按章编号或使用模型编号
`\tag{}`。两种做法都可以，但必须**全文统一**：

```latex
% 做法 A：自动连续编号（默认，最省事）
\begin{equation}\label{eq:obj}
  \min_{c_t,d_t} \sum_{t=1}^{T} \pi_t b_t
\end{equation}

% 做法 B：手动模型编号（配合模型汇总块，可读性更好）
\begin{equation}
\begin{aligned}
  \min_{c_t,d_t}\quad & \sum_{t=1}^{T} \pi_t b_t \\
  \text{s.t.}\quad   & b_t + p_t + d_t = l_t + c_t, \\
                     & 1200 \le s_t \le 10800 .
\end{aligned}
\tag{M2}\label{eq:m2}
\end{equation}
```

**一条硬规则**：每个编号公式必须在正文被引用至少一次（`由式~\eqref{eq:m2} 可知`），否则取消编号。

### 5.3 交叉引用检查（编译后）

```powershell
# 手写编号残留（输出应只剩 \ref 的引用，不应有"图 3"这类硬编码）
Select-String -Path paper\manuscript.tex -Pattern '图\s*\d'
# 定义了但从未引用的标签：先列出全部 \label，再逐个在文中搜 \ref
Select-String -Path paper\manuscript.tex -Pattern '\\label\{([^}]+)\}' -AllMatches |
  ForEach-Object { $_.Matches.Groups[1].Value } | Sort-Object -Unique
```

---

## 6. 图片文件组织约定

```text
results/
  main/E02/q2_plan.csv                     ← 实验产出的数据
  figures/
    E02_q2_dispatch.pdf / .png             ← 由 E02 产出；E0x 前缀 = 来源实验编号
    E03_q2_compare.pdf   E05_tornado.pdf
    S01_framework.pdf                      ← 示意图（无实验来源），S 前缀
sop/project/figures/
    data_01_missing.png  data_04_corr.png  ← P5 数据诊断图（门禁检查此位置，≥3 张）
    fig07_tornado.png                      ← P12 验证图（门禁检查 *.png，≥2 张）
paper/manuscript.tex
```

**命名规则**：

| 情形 | 命名 | 登记位置 |
|---|---|---|
| 有实验来源的结果图 | `results/figures/<E0x>_<name>.pdf`（如 `E02_q2_dispatch.pdf`） | `experiment_registry.md` 第 4 节"来源实验编号"填 E02 |
| 示意图 / 框架图 / 机理图 | `results/figures/S<nn>_<name>.pdf` | 同表"来源实验编号"填"不依赖实验" |
| P5 数据诊断图 | `sop/project/figures/data_<nn>_<name>.png` | 门禁 `file_exists_glob: sop/project/figures/data_*.png`（≥3） |
| P12 验证图 | `sop/project/figures/` 下放一份 PNG 副本 | 门禁 `file_exists_glob: sop/project/figures/*.png`（≥2） |

> ⚠️ **两处目录的关系**：P11/P12 的门禁检查的是 `sop/project/figures/*.png`，而论文插图资产要求落在
> `results/figures/` 下（与 E0x 绑定、进支撑材料）。做法是**出图时两处都写**（或在打包前复制一份），
> 不要只留一处——否则要么门禁不过，要么支撑材料里找不到图。
> `save_cumcm_figure` 已经同时产出 PDF 与 600 dpi PNG，把它输出的 PNG 拷一份过去即可。
> **LaTeX 侧路径**：用 `\graphicspath{{../results/figures/}}`（tex 在 `paper/` 下时），正文只写文件名。

### 6.1 论文引用的对应关系（一张图三处必须一致）

| 位置 | 内容 | 核对方式 |
|---|---|---|
| 文件 | `results/figures/E02_q2_dispatch.pdf` | `Test-Path` |
| 契约 | 「图编号：图 3」「数据来源：E02 → results/main/E02/q2_plan.csv」 | 与登记表第 4 节逐行对照 |
| 论文 | `\includegraphics[...]{E02_q2_dispatch}` + `\label{fig:q2-plan}` + 图注里的 E02 | `\ref` 编译后目视 |

三处任一不一致，就是 P15 的"证据链断裂"。

---

## 7. 中文字体：图内 vs 图题

### 7.1 一个**应该**存在的差异

| 位置 | 字体 | 为什么 |
|---|---|---|
| 图内中文（轴标签、图例、标注） | **黑体类**：Microsoft YaHei / SimHei / Source Han Sans SC（`apply_cumcm_style()` 自动挑本机可用的） | 图内字号小（7.5–9pt），宋体在这个尺寸下笔画会糊 |
| 图题 / 图注（`\caption`） | 跟随正文（ctex 默认宋体，`font=small`） | 图注是正文的一部分，字体应随正文 |
| 图内西文与数字 | Arial / Helvetica（`LATIN_CANDIDATES` 默认） | 与中文黑体的笔画粗细协调 |

所以"图内黑体 + 图题宋体"**是正确且有意的差异**，不要为了"统一"把图内也改成宋体。
真正要统一的是三件事：**字号节奏**（图内最小刻度 ≥7.5pt，见 `design-theory.md` §1.2）、
**符号写法**（图内的 $t_1$ 与正文的 $t_1$ 是同一个符号）、**数字口径**（有效数字位数一致）。

### 7.2 如果一定要与正文的 Times New Roman 完全一致

模板用 `\setmainfont{Times New Roman}` 管西文，而 matplotlib 侧默认是 Arial，
同一图注里相邻出现会略不协调。若你在意，在 `apply_cumcm_style()` **之后**追加：

```python
import matplotlib as mpl
from cumcm_style import apply_cumcm_style
apply_cumcm_style(base_size=9)
mpl.rcParams.update({
    "font.sans-serif": ["SimHei", "Times New Roman", "DejaVu Sans"],  # 中文优先，西文回退到 Times
    "mathtext.fontset": "stix",          # 数学符号用 Times 风格
})
```

**但不要在图与图之间换来换去**：一篇论文里图内西文字体必须一致，混用比"与正文不完全一致"更刺眼。
国赛赶时间时，**用默认的无衬线组合就好**——它在小字号下的清晰度最好，评委不会因为字体族不同扣分。

### 7.3 中文缺字检查（热力学/医学题高发）

图内出现生僻字（焓、熵、黏、阈、酶…）时，`SimHei` 可能缺字形，打印成方块。
**必须在导出的 PDF 里逐个目视确认**；发现缺字就换 `Microsoft YaHei`（字形覆盖更全），
或改用符号/英文表示（在符号表里登记）。

---

## 8. 一个完整的可编译片段（单图 + 双子图 + 三线表）

```latex
% !TeX program = xelatex
\documentclass[withoutpreface,bwprint]{cumcmthesis}   % 电子版：不含承诺书与编号页
\usepackage{cumcm2026}
\usepackage{placeins}                  % 需要 \FloatBarrier 时才加（模板未预加载）

\graphicspath{{../results/figures/}}   % 正文里只写图片文件名

% 放宽浮动体配额，让图更容易落在引用的附近（见 §3.2）
\renewcommand{\topfraction}{0.9}\renewcommand{\bottomfraction}{0.8}
\renewcommand{\textfraction}{0.07}\renewcommand{\floatpagefraction}{0.75}
\setcounter{topnumber}{3}\setcounter{bottomnumber}{2}\setcounter{totalnumber}{4}

% 元数据去身份（cumcm2026.sty 已把 pdfauthor 置空，这里再补一次并清掉 creator）
\AtBeginDocument{\hypersetup{pdfauthor={},pdfcreator={}}}

\begin{document}
\section{问题二的模型建立与求解}
\subsection{结果分析}

由式~\eqref{eq:m2} 的功率平衡与储能递推，采用混合整数线性规划求得全天最优调度方案，
全天购电成本为 38650 元，较线性规划基线降低 6.2\%，结果如图~\ref{fig:q2-plan} 所示。

\begin{equation}
\begin{aligned}
  & b_t + p_t + d_t = l_t + c_t, \\
  & s_t = s_{t-1} + \eta\, c_t - d_t/\eta, \qquad s_0 = s_T = 6000 .
\end{aligned}
\tag{M2}\label{eq:m2}
\end{equation}

% ---------- 单图（通栏）：width 必须等于图契约里的最终尺寸 ----------
\begin{figure}[htbp]
  \centering
  \includegraphics[width=\linewidth]{E02_q2_dispatch}
  \caption{问题二的最优购电与储能调度方案。(a) 全天 144 时段的功率平衡，紧急购电恒为 0；
           (b) 储能荷电状态轨迹，阴影为允许区间 $[1200,\ 10800]$~kWh，起止均为 6000~kWh；
           (c) 三种方案的全天购电成本对比。$n=144$ 个时段（$\Delta t=10$~min），确定性
           MILP 求解，误差为 5 个随机种子的最大漂移 $0.4\%$。数据来自 E02 与 E03。}
  \label{fig:q2-plan}
\end{figure}

由图~\ref{fig:q2-plan}(a) 可见，购电量集中在 0.3~元/kWh 的谷时段，峰时段由储能放电覆盖，
全程未触发紧急购电，说明方案在 5 倍电价的惩罚下仍严格可行。

\subsection{灵敏度分析}

% ---------- 双子图并排（各 7.8cm = 0.48\linewidth） ----------
\begin{figure}[htbp]
  \centering
  \begin{subfigure}[b]{0.48\linewidth}
    \includegraphics[width=\linewidth]{E05_tornado}
    \subcaption{参数灵敏度排序}\label{fig:sens-a}
  \end{subfigure}\hfill
  \begin{subfigure}[b]{0.48\linewidth}
    \includegraphics[width=\linewidth]{E06_sens_curve}
    \subcaption{电价的灵敏度曲线}\label{fig:sens-b}
  \end{subfigure}
  \caption{关键参数对全天购电成本的影响。$n=144$ 个时段；每个参数取
           $\pm5\%$、$\pm10\%$、$\pm20\%$ 共 4 档，均为单因素（OAT）扰动，
           未计入参数间交互效应。数据来自 E05。}
  \label{fig:sens}
\end{figure}

图~\ref{fig:sens-a} 表明电价峰谷比是主导敏感参数（$\pm20\%$ 引起成本 $\mp17.4\%$ 变化），
寿命损耗系数影响最小（$\pm1.1\%$）；图~\ref{fig:sens-b} 显示该响应在 $\pm10\%$ 内近似线性，
故一阶灵敏度估计足够。

\subsection{约束余量}

\begin{table}[htbp]
  \centering
  \caption{最优解的约束满足情况}\label{tab:margins}     % 表题在表上方
  \begin{tabular}{l S[table-format=5.1] S[table-format=5.1] c}
    \toprule
    约束 & {解处取值} & {限值} & 判定 \\
    \midrule
    储能电量下界 (kWh) & 1200.0 & 1200.0  & 紧约束 \\
    储能电量上界 (kWh) & 9840.2 & 10800.0 & 余量 959.8 \\
    单段充电功率 (kW)  & 5000.0 & 5000.0  & 紧约束 \\
    功率平衡残差 (kWh) & 0.0    & 0.0     & $<10^{-6}$ \\
    \bottomrule
  \end{tabular}
\end{table}

表~\ref{tab:margins} 显示 2 条约束在最优点处取等号，功率平衡残差小于 $10^{-6}$~kWh，
解为模型的一致解。

\FloatBarrier            % 保证本节浮动体在本节内输出（需 placeins）
\end{document}
```

### 编译与检查

```powershell
xelatex manuscript.tex; xelatex manuscript.tex    # 两次：第二次才解析 \ref / \eqref
Get-Item manuscript.pdf | ForEach-Object { "{0:N2} MB" -f ($_.Length/1MB) }   # 必须 ≤ 20MB
```

要点回顾：**插图宽度写固定 cm 或 `\linewidth`，永不写 `scale`**；**宽度 = 图契约里的最终尺寸**；
**`\label` 紧跟 `\caption`**；**面板标签与 `subcaption` 二选一**；**表题在上、图题在下**；**编译两次才看编号**。
