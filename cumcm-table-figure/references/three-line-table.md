# 三线表规范与模板（国赛）

> 本文件是 `cumcm-table-figure` 的表格参考，术语与 `paper_writing.md` §7.1 一致。示例只用模板已加载的宏包，可直接粘进 `manuscript.tex`；需额外宏包处已标注。

## 1. 模板里已经有什么（开工前必读）

`cumcm2026.sty` 已加载 `booktabs, array, tabularx, longtable, multirow, siunitx, caption,
subcaption, enumitem, graphicx, float, xcolor, listings, amsmath, ctex`（`tikz` 由 `example.tex` 加载）。

| 纪律 | 原因 |
|---|---|
| 不要重复 `\usepackage` 这些宏包 | 已加载，重复加载可能触发 option clash |
| 不要重新定义 `Y`/`L`/`R`/`C` 列类型 | 模板已定义，重定义报 `Command \Y already defined` |
| `siunitx` 已设 `detect-all, group-minimum-digits=4` | 表内字号自动跟随正文；**4 位数自动加千分位**（`1234`→`1,234`），不要时在该表前 `\sisetup{group-minimum-digits=5}` |
| `caption` 已设 `position=top`（表） | 表题天然在上方，只要 `\caption` 写在 `tabular` **之前** |

要自己加的：表注 `threeparttable`；横向表 `rotating`；伪代码 `algorithm,algpseudocode`（见 `algorithm-pseudocode.md`）。

## 2. booktabs 正确用法，为什么禁用竖线

```latex
\begin{tabular}{l r r}
  \toprule                                    % 顶线（粗）
  方案 & 日成本 (元) & 相对变化 (\%) \\
  \midrule                                    % 表头线（细）
  线性松弛 & 12\,480.00 & 0.00 \\
  \addlinespace                               % 分组留白，代替横线
  混合整数模型 & 11\,706.00 & \textbf{-6.20} \\   % 最优值加粗
  \bottomrule                                 % 底线（粗）
\end{tabular}
```

**禁用竖线的理由**：竖线与数字相撞（`1` 和 `|` 视觉混淆），人眼横向追踪变慢；
三线表靠**列对齐 + 留白**分组，竖线是冗余编码；Word 默认网格表就是全框线 + 彩色底纹，像未排版。

| 想要的效果 | 正确做法 | 错误做法 |
|---|---|---|
| 分隔列组 / 行组 | `\cmidrule(lr){2-3}`；`\addlinespace` | 加竖线；每行之间 `\hline` |
| 强调合计行 | 合计行前 `\cmidrule{2-4}` + 数字加粗 | 给合计行加灰色底纹 |
| 合并单元格 | `\multicolumn{2}{c}{...}` | 用空列硬凑宽度 |

`\cmidrule` 的裁剪参数不能省：`\cmidrule(lr){2-3}\cmidrule(lr){4-5}` 才不会粘成一条线。

## 3. 表题与表注

**表题在表上方**，中文，说清"这张表是什么 + 用了什么数据"；**不要**在表题里写结论
（"表 3 表明本文方法最优"是正文解读的活）。

```latex
\begin{table}[htbp]
  \centering
  \caption{三种求解策略的最优目标值与计算代价（数据来源：E04，$n=30$ 次独立运行）}
  \label{tab:algo-compare}
  ...
\end{table}
```

**表注（零依赖写法，立刻可用）：**

```latex
\end{tabular}

\vspace{2pt}{\footnotesize 注：日成本单位为元；相对变化以线性松弛方案为基准；
``—'' 表示该方案未报告该指标。数据来源 E04。}
\end{table}
```
**表注（推荐写法，需 `\usepackage{threeparttable}`，注宽与表体对齐）：**

```latex
\begin{table}[htbp]\centering
  \begin{threeparttable}
    \caption{参数灵敏度分析结果（$\pm10\%$ 扰动）}\label{tab:sens}
    \begin{tabular}{l S[table-format=2.2] S[table-format=2.2] S[table-format=1.2]}
      \toprule
      参数 & {下限 $T^{-}$ (s)} & {上限 $T^{+}$ (s)} & {弹性系数} \\
      \midrule
      沉降速度 $v_s$  & 1.80 & 1.90 & 0.42 \\
      起爆延时 $\tau$ & 1.79 & 1.91 & 0.38 \\
      \bottomrule
    \end{tabular}
    \begin{tablenotes}[flushleft]\footnotesize
      \item 注：弹性系数 $=(\Delta T/T)/(\Delta p/p)$。数据来源 E04。
    \end{tablenotes}
  \end{threeparttable}
\end{table}
```

> `S` 列的**表头必须用花括号包起来**（`{下限 $T^{-}$ (s)}`），否则 siunitx 会把它当数字解析而报错——这是初学 siunitx 最常见的编译失败原因。

## 4. 列宽控制：tabularx / p{} / \resizebox 的取舍

| 需求 | 用什么 | 说明 |
|---|---|---|
| 全部列窄，总宽 < `\linewidth` | `tabular` + `l/r/c` | 最省事，宽度由内容决定 |
| 有一列是长中文（"含义""说明"） | `tabularx` + `Y`/`L`/`R`（模板已定义） | 自动换行并撑满 `\linewidth`；只固定某列宽时用 `p{3cm}` 或 `C{3cm}` |
| 表略宽，想"挤一挤" | `\setlength{\tabcolsep}{4pt}` 或 `\small` | 先动列间距，再动字号 |
| 表明显超宽 | 见 §5 四种方案 | **不要**用 `\resizebox` |

```latex
% 中文说明列用 L，数字列用 r；两侧去掉 padding 使三线表与版心等宽
\begin{tabularx}{\linewidth}{@{}l L r@{}}
  \toprule
  符号 & 含义 & 取值 \\
  \midrule
  $v_s$ & 烟幕云团竖直下沉速度 & 3.00 \\
  $R$   & 烟幕云团有效半径     & 10.00 \\
  \bottomrule
\end{tabularx}
```

**`\resizebox{\linewidth}{!}{...}` 的四个陷阱**：① 等比缩小把 12pt 表内字压到 6～7pt，打印后不可读；
② 缩小比例与表体宽度绑定，换机器改列宽字号就变，**不可复现**；③ 线宽一起变细，顶线与底线失去粗细差别；
④ 评委在 PDF 里放大虽能看清，"字明显比正文小"本身已在扣分。
**替代优先级**：删列 → 精简表头 → `\small`/`\footnotesize`（到 `\footnotesize` 为止）→ 换列宽方案 → §5。

## 5. 超宽表的四种方案

| 方案 | 怎么做 | 代价 | 什么时候选 |
|---|---|---|---|
| **① 缩列** | 删可推断的列（序号、重复单位列），表头改短，`\small` 或缩 `\tabcolsep` | 信息量下降 | **首选** |
| **② 转置** | 行列表头互换，把"方案"从列变行 | 行数变多，可能跨页 | 列数远大于行数（3 行 × 10 列） |
| **③ 拆表** | 按语义拆成"主表 + 支撑表"（目标值表 / 约束余量表） | 多占一个浮动体位置 | 列天然分成两组 |
| **④ 横向排版** | `sidewaystable`（需 `\usepackage{rotating}`） | 读者歪头看；30 页正文里代价大 | 列多且都不可删（逐时段明细） |

```latex
\begin{sidewaystable}                       % 需 \usepackage{rotating}
  \centering
  \caption{8 个站点逐时段需求量明细（数据来源：附件 2，单位：件）}
  \label{tab:station-detail}
  \small
  \begin{tabular}{l *{6}{r}}
    \toprule
    站点 & 08:00 & 09:00 & 10:00 & 11:00 & 12:00 & 13:00 \\
    \midrule
    S1 & 120 & 132 & 141 & 150 & 168 & 173 \\   % 真实表共 8 行 × 12 列（08:00--19:00）
    \bottomrule
  \end{tabular}
\end{sidewaystable}
```

**决策顺序**：先量宽度。超出 10% 以内 → `\small` + 缩 `\tabcolsep`；超出 30% 以上 → 拆表或转置。**能不横排就不横排**。

## 6. 跨页长表：longtable

```latex
\begin{longtable}{l r r}
  \caption{全部 30 组参数扰动算例结果}\label{tab:all-runs}\\
  \toprule
  算例 & 参数扰动 & 有效时长 (s) \\
  \midrule
  \endfirsthead                       % 首页表头
  \multicolumn{3}{l}{\small 续表~\thetable\quad 全部 30 组参数扰动算例结果}\\
  \toprule
  算例 & 参数扰动 & 有效时长 (s) \\
  \midrule
  \endhead                            % 后续页表头（自动重复）
  \midrule
  \endfoot                            % 除末页外的页脚（可写"接下页"）
  \bottomrule
  \endlastfoot                        % 末页页脚
  1 & $v_s$ $-10\%$ & 1.80 \\
  2 & $v_s$ $+10\%$ & 1.90 \\
  % ... 其余 28 行
\end{longtable}
```

五条纪律：① `\caption{...}\label{...}\\` 末尾的 `\\` **不能省**，否则首行表头被吞；
② `\endfirsthead`/`\endhead`/`\endfoot`/`\endlastfoot` 顺序固定，写错会得到空白页；
③ 续表那行用 `\multicolumn{列数}{l}{...}` 并重复列标题，读者不必回翻；
④ `longtable` **不是浮动体**（没有 `[htbp]`），就地分页，要放在"应该分页"的位置；
⑤ **正文里尽量别出现跨页表**——30 页预算下，30 行以上明细表放附录更划算（附录页数不限）。

## 7. 数字排版

**对齐方式二选一。**

| 做法 | 写法 | 优点 | 代价 |
|---|---|---|---|
| **定长小数 + 右对齐（推荐默认）** | `{l r r}`，统一小数位 | 小数点自然对齐；`\textbf{}`、上标都安全；任何 TeX 环境可编译 | 需保证同列位数一致 |
| **siunitx `S` 列** | `S[table-format=2.2]` | 处理 `±`、范围、千分位、`***` 后缀、不同有效位 | 表头要包 `{}`；非数字内容要 `\multicolumn` 逃逸 |

```latex
% S 列 + 显著性上标（table-space-text-post 为后缀预留宽度）
\begin{tabular}{l S[table-format=1.3] S[table-format=1.3, table-space-text-post={$^{***}$}]}
  \toprule
  变量 & {系数} & {标准误} \\
  \midrule
  截距     & 0.512  & 0.043$^{***}$ \\
  \bottomrule
\end{tabular}
```

**有效位数三条规矩**：① **同一列同一小数位**（评委横向扫的是小数点，不是有效数字个数）；
② 结果值 3～4 位有效数字（$T_1=1.85\ \mathrm{s}$、$\eta=68.4\%$），不要写 `1.8500000`；跨数量级才用 `1.2\times10^{4}`，可得精确值写 `12\,000`。

**单位写法**：单位进**表头**，格式"量名 $符号$ (单位)"（`投放时刻 $t_{1,i}$ (s)`、`相对变化 (\%)`）；
无量纲量写 `—` 不留空；变量斜体、单位正体；全表同一物理量只用一种单位，换算说明放表注。

**千分位**：模板已设 `group-minimum-digits=4`，`1234` 会排成 `1,234`；不要时局部设置：

```latex
{\sisetup{group-minimum-digits=5}\begin{tabular}{r} 1234 \\ \end{tabular}}
```

**显著性标记**：数值后接 `$^{***}$`，列格式配 `table-space-text-post={$^{***}$}`（见上），
并在表注给出定义与检验方法（`注：$^{*}$ $p<0.05$，$^{**}$ $p<0.01$，$^{***}$ $p<0.001$（双样本 $t$ 检验，$n=30$）。`）。
四条规矩：① 不给定义的星号等于没标；② 不要用颜色/底纹代替星号；
③ 星号列要通过"删掉它结论会变吗"的检验；④ 表格与数据图的显著性口径必须一致（同一个 $p$ 阈值、同一种检验）。

## 8. 空值与缺失值

| 含义 | 符号 | 写法 |
|---|---|---|
| 缺测 / 无数据 | `—` | 文本书写；`S` 列里用 `\multicolumn{1}{c}{—}` 逃逸；不适用时也在表注声明 |
| 数值为零 | `0.00` | 用数字写，**不要**写 `—` |
| 小于检出限 | `<0.01` | 文本书写，表注说明检出限 |
| 未收敛 / 失败 | `n.c.` | 表注定义 `n.c.` = 未在 $K$ 次迭代内收敛 |

**最重要的纪律：不留空。** 空白格子在评委眼里等于"这队自己都没搞清楚"；用 `—`（破折号）而不是 `-`（看起来像负号）。

## 9. 六个完整示例

### 示例 1：变量说明表（证明：符号唯一、单位自洽、决策变量与常数分得清）

```latex
\begin{table}[htbp]\centering
  \caption{符号说明}\label{tab:symbols}
  \begin{tabularx}{\linewidth}{@{}l L l l@{}}
    \toprule
    符号 & 含义 & 单位 & 类型 \\
    \midrule
    $t_1$     & 干扰弹投放时刻 & s & 决策变量，$t_1\in[100,180]$ \\
    $R$       & 烟幕云团有效半径 & m & 常数（题目给定），$R=10$ \\
    $v_s$     & 云团竖直下沉速度 & m/s & 常数（题目给定），$v_s=3$ \\
    $\Phi(t)$ & 遮蔽判定函数（1 为遮蔽，0 为未遮蔽） & — & 派生量，取值 $\{0,1\}$ \\
    \bottomrule
  \end{tabularx}
  \vspace{2pt}{\footnotesize 注：中间量（如视线距离 $d(t)$）随文定义，不进总表。}
\end{table}
```

### 示例 2：结果对比表（证明：四问都有数、逐问递进、约束严格满足）

```latex
\begin{table}[htbp]\centering
  \caption{四问最优方案与约束余量（数据来源：E01--E04）}\label{tab:results-all}
  \begin{tabular}{l r r r r}
    \toprule
    问题 & 有效时长 $T_k$ (s) & 投放时刻 (s) & 投放高度余量 (m) & 迭代次数 \\
    \midrule
    问题一 & 1.85 & 142.63 & 105.72 & 61 \\
    问题二 & 4.62 & —      & 98.40  & 240 \\
    \addlinespace
    问题三 & 5.17 & 138.02 & 92.15  & 312 \\
    问题四 & \textbf{7.91} & 141.55 & 88.07 & 405 \\
    \bottomrule
  \end{tabular}
  \vspace{2pt}{\footnotesize 注：``—'' 表示该时刻由算法内部确定；``投放高度余量'' 为起爆高度与下限之差。}
\end{table}
```

### 示例 3：灵敏度表（证明：结论在什么范围内不变、哪个参数最要紧）

```latex
\begin{table}[htbp]\centering
  \caption{关键参数 $\pm10\%$ 扰动下的最优遮蔽时长（数据来源：E05，$n=18$）}
  \label{tab:sensitivity}
  \begin{tabular}{l S[table-format=1.2] S[table-format=1.2] S[table-format=1.2] r}
    \toprule
    参数 & {$T(-10\%)$ (s)} & {$T(+10\%)$ (s)} & {最大相对变化 (\%)} & 弹性系数 \\
    \midrule
    沉降速度 $v_s$  & 1.80 & 1.90 & 2.70 & 0.42 \\
    起爆延时 $\tau$ & 1.79 & 1.91 & 2.80 & 0.38 \\
    释放半径 $R$    & 1.84 & 1.86 & 1.08 & 0.07 \\
    \bottomrule
  \end{tabular}
  \vspace{2pt}{\footnotesize 注：基准 $T_1=1.85$ s；弹性系数 $=(\Delta T/T)/(\Delta p/p)$，绝对值越大越关键。}
\end{table}
```

### 示例 4：参数表（证明：每个参数的来路都清楚）

```latex
\begin{table}[htbp]\centering
  \caption{模型参数取值与来源}\label{tab:params}
  \begin{tabularx}{\linewidth}{@{}l l L l@{}}
    \toprule
    参数 & 符号 & 取值 & 来源 \\
    \midrule
    无人机飞行速率   & $v_u$      & $120$ m/s  & 题目给定 \\
    起爆延时         & $\tau$     & $4.8$ s    & 题目给定 \\
    云团有效半径     & $R$        & $10$ m     & 题目给定 \\
    云团下沉速度     & $v_s$      & $3$ m/s    & 题目给定 \\
    时间离散步长     & $\Delta t$ & $0.01$ s   & 本文设定（截断误差 $\le 2\Delta t$） \\
    粒子数与迭代上限 & $N,\ K$    & $60,\ 400$ & 本文设定（$N$ 由收敛曲线标定，见 E01） \\
    \bottomrule
  \end{tabularx}
\end{table}
```

### 示例 5：算法对比表（证明：选这个算法不是拍脑袋，有精度/稳定性/耗时三方取舍）

```latex
\begin{table}[htbp]\centering
  \caption{四种求解策略的性能对比（30 次独立运行，数据来源：E03）}\label{tab:algo-compare}
  \begin{tabular}{l r r r r}
    \toprule
    算法 & 最优值均值 (s) & 标准差 (s) & 平均耗时 (s) & 成功率 (\%) \\
    \midrule
    网格扫描     & 1.71 & 0.000 & 12.4 & 100 \\
    遗传算法     & 1.79 & 0.032 & 8.7  & 86 \\
    粒子群算法   & 1.82 & 0.015 & 6.2  & 93 \\
    粒子群 + SQP & \textbf{1.85} & 0.004 & 9.8 & \textbf{100} \\
    \bottomrule
  \end{tabular}
  \vspace{2pt}{\footnotesize 注：``成功率'' 指 30 次运行中达到最优值 $99\%$ 以上的比例；各算法统一迭代上限。}
\end{table}
```

### 示例 6：方案明细表（证明：要交付的每项答案都在表里，合计口径写清楚了）

```latex
\begin{table}[htbp]\centering
  \caption{三枚干扰弹的最优投放方案明细（数据来源：E02）}\label{tab:q2-detail}
  \begin{tabular}{c r r r r}
    \toprule
    弹序 & 投放时刻 $t_{1,i}$ (s) & 起爆点 $x$ (m) & 起爆点 $z$ (m) & 有效时长 (s) \\
    \midrule
    1 & 115.62 & 0 & 1662 & 1.05 \\
    2 & 127.48 & 0 & 1611 & 2.15 \\
    3 & 139.35 & 0 & 1558 & 1.12 \\
    \midrule
    合计（并集） & — & — & — & \textbf{4.62} \\
    \bottomrule
  \end{tabular}
  \vspace{2pt}{\footnotesize 注：$z$ 轴竖直向上；合计行为三个遮蔽区间的\textbf{并集}长度，不等于三行之和。}
\end{table}
```

## 10. 交付前检查清单

- [ ] 表题在表**上方**，中文，写清对象/口径/数据来源
- [ ] 三线表：只有 `\toprule`/`\midrule`/`\bottomrule`（+ 必要 `\cmidrule`），**无竖线、无 `\hline`**
- [ ] 列宽在 `\linewidth` 内；**没有** `\resizebox` 缩字；表内字号 ≥ 正文 80%（最多 `\footnotesize`）
- [ ] 单位写在表头，无量纲写 `—`；同列小数位一致，小数点对齐；空值统一用 `—` 且表注说明含义
- [ ] 最优值加粗，且与摘要/正文/数据图逐位一致
- [ ] 表注含：数据来源（E0x）、单位/坐标系、符号与显著性定义
- [ ] 正文在**表之前**引用（`表~\ref{tab:...}`），表后有 2～4 句解读
- [ ] 表内无校名、姓名、学号、赛区信息；编译后在 PDF 里实际看过（不超版心、跨页表头重复）
