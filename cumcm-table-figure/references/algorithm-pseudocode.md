# 算法伪代码规范与模板（国赛）

> 本文件是 `cumcm-table-figure` 的伪代码参考。伪代码属于"不是用数据点画出来的图"，
> 与流程图同源：**流程图给读者全局视角，伪代码给读者可复现的细节**，两者可以同时出现。
> 宏包未预装在 `templates/cumcm-thesis/`，需要自己在导言区加载（见 §1）。

**目录**

1. [宏包选择与中文化配置](#1-宏包选择与中文化配置)
2. [输入/输出/复杂度标注规范](#2-输入输出复杂度标注规范)
3. [五份完整可编译伪代码](#3-五份完整可编译伪代码)
4. [行号与正文引用](#4-行号与正文引用)
5. [伪代码与附录代码的一致性](#5-伪代码与附录代码的一致性)
6. [什么时候不要用伪代码](#6-什么时候不要用伪代码)
7. [交付前检查清单](#7-交付前检查清单)

---

## 1. 宏包选择与中文化配置

模板**没有**加载任何算法排版宏包（见 `example.tex` 附录的宏包清单），必须自己加。

| 方案 | 写法 | 优点 | 代价 |
|---|---|---|---|
| **`algorithm` + `algpseudocode`（推荐）** | 见下方导言区配置 | 语法简洁、`\State/\For/\If` 直观、与 `\ref` 交叉引用顺畅 | 需中文化若干关键字 |
| `algorithm2e` | `\usepackage[ruled,vlined,linesnumbered]{algorithm2e}` | 内置中文关键字设置、`vlined` 竖线风格 | 语法与前者完全不同；与 `algorithm`/`algpseudocode` **不能同时加载**（`\Comment` 等命令冲突） |

**推荐配置（放进导言区，一次配好全文通用）：**

```latex
\usepackage{algorithm}          % 浮动体 + \caption + \floatname
\usepackage{algpseudocode}      % \State \For \If \While \Return
% float 宏包模板已加载（提供 [H] 选项），不要再写一次 \usepackage{float}

\floatname{algorithm}{算法}                          % 把 "Algorithm" 改成 "算法"
\renewcommand{\algorithmicrequire}{\textbf{输入：}}    % \Require 的中文
\renewcommand{\algorithmicensure}{\textbf{输出：}}     % \Ensure 的中文
\renewcommand{\algorithmiccomment}[1]{\hfill $\triangleright$ #1}
\algrenewcommand\algorithmicdo{\textbf{执行}}          % \For 的 "do"
\algrenewcommand\algorithmicto{\textbf{到}}             % \For 的 "to"
```

**两条编译纪律**：

1. **必须用 XeLaTeX 编译**——模板基于 ctex，`pdflatex` 直接报错；
2. 伪代码环境是**浮动体**：`[H]`（需 `float` 包，模板已加载）强制就地，`[htbp]` 允许浮动。
   正文页数紧张时用 `[htbp]`，让 LaTeX 自己找位置；论文结构敏感时用 `[H]`。
   一张伪代码通常占 1/3～1/2 页，**四问各贴一份就是两页**，务必按需。

---

## 2. 输入/输出/复杂度标注规范

一份合格的伪代码必须让评委在不看正文的情况下回答三个问题：
**吃什么数据**（输入）、**吐什么结果**（输出）、**要多少代价**（复杂度）。

| 要素 | 怎么写 | 检查方式 |
|---|---|---|
| **输入** | `\Require` 逐项列出**符号 + 含义 + 来源**（题目给定/标定/上一问输出） | 把输入项与正文符号表对照，缺一个就是漏洞 |
| **输出** | `\Ensure` 列出算法**真正返回**的量，含单位 | "输出：结果" 是不合格写法 |
| **复杂度** | 最后一行 `\State \textbf{复杂度}：...`，写清规模变量与量级 | 评委据此判断你能不能算完 |
| **计算代价** | 复杂度后面补一句**实测**（运行时间 / 内存 / 机器环境） | 只有理论复杂度没有实测，工程可信度不足 |
| **参数设置** | 迭代上限、种群规模、步长、终止阈值 | 必须能在正文找到"这些值怎么定的" |
| **约束处理** | 罚函数 / 修复算子 / 投影，写清是哪一种 | 评委最爱在这里找漏洞 |

复杂度行的写法示例（直接照抄格式）：

```latex
\State \textbf{复杂度}：单代 $O(NM)$，总计 $O(GNM)$，其中 $G$ 为迭代上限、$N$ 为种群规模、
       $M$ 为时间离散步数。本问 $G=400$、$N=60$、$M=10^{4}$，约 $2.4\times10^{8}$ 次判定，
       实测 6.2 s（Python 3.10 / NumPy 向量化，单核）。
```

---

## 3. 五份完整可编译伪代码

> 符号沿用 `paper_writing.md` 的示例场景（烟幕干扰弹），便于与正文对照。
> 每份都可直接粘进 `manuscript.tex`（导言区先按 §1 配置）。

### 算法 1：遗传算法求解多弹投放时刻协同（问题二）

```latex
\begin{algorithm}[htbp]
\caption{遮蔽区间并集时长最大化的遗传算法}\label{alg:ga}
\begin{algorithmic}[1]
\Require 无人机初始位置 $P_{u,i}(0)$、速率 $v_{u,i}$、航向 $\theta_i$（$i=1,2,3$）；
         起爆延时 $\tau$、烟幕参数 $R,H,v_s$；投放窗口 $[t_{\min},t_{\max}]$；
         种群规模 $N$、迭代上限 $G$、交叉概率 $p_c$、变异概率 $p_m$
\Ensure 最优投放时刻 $\{t_{1,i}^*\}$ 与最大有效遮蔽时长 $T^*$（s）
\State 初始化种群 $\mathcal{P} \gets \{\mathbf{x}_n\}_{n=1}^{N}$，$\mathbf{x}_n \sim U(t_{\min},t_{\max})^{3}$
\State 评估适应度 $T(\mathbf{x}_n)$：逐点计算判定函数 $\Phi(t)$（式 (5)），再用扫描线合并 $\Phi=1$
       的时间区间取并集长度；记录 $T^* \gets \max_n T(\mathbf{x}_n)$
\For{$g = 1$ \textbf{到} $G$}
  \State 锦标赛选择父代 $\mathcal{P}_{\text{par}} \subset \mathcal{P}$（规模 $N$）
  \State 单点交叉：以概率 $p_c$ 交换父代分量，得到子代 $\mathcal{P}_{\text{off}}$
  \State 高斯变异：以概率 $p_m$ 对分量加扰动 $\mathcal{N}(0,\sigma_g)$，$\sigma_g \gets 0.1\,(t_{\max}-t_{\min})(1-g/G)$
  \State \textbf{约束修复}：对越界分量作反射 $\tilde t \gets t_{\min} + |\bmod(\tilde t - t_{\min},\ 2L) - L|$，
         $L = t_{\max}-t_{\min}$；对起爆高度越界的个体回退到父代
  \State 评估子代适应度 $T(\mathbf{x})$（逐点判定 $\Phi(t)$ + 扫描线合并区间）
  \State 精英保留：把上一代前 $5\%$ 个体直接复制进下一代，避免最优解丢失
  \If{连续 40 代 $T^*$ 改进量 $< 10^{-4}$ s}
    \State \textbf{break} \Comment{早停，避免无效迭代}
  \EndIf
\EndFor
\State \Return $\{t_{1,i}^*\},\ T^*$
\State \textbf{复杂度}：单代 $O(NM)$，总计 $O(GNM)$。本问 $G=400$、$N=60$、$M=10^{4}$，
       实测 8.7 s（30 次独立运行均值），成功率 $86\%$（见 表~\ref{tab:algo-compare}）。
\end{algorithmic}
\end{algorithm}
```

**要点**：① 第 8 行的修复算子写成了**可执行公式**，不是"修复到可行域"这种空话；
② 第 3 行把适应度评估写成"判定器 + 扫描线"两步，并指向正文式 (5)，
   避免在两处重复 20 行判定器代码，也不会留下悬空引用；
③ 最后一行给复杂度 + 实测 + 成功率，直接呼应算法对比表。

### 算法 2：模拟退火求解单弹投放时刻（问题一）

```latex
\begin{algorithm}[htbp]
\caption{单枚干扰弹最优投放时刻的模拟退火算法}\label{alg:sa}
\begin{algorithmic}[1]
\Require 可行区间 $[t_{\min},t_{\max}]$、初温 $T_0$、终止温度 $T_f$、降温系数 $\alpha$、
         每温度迭代次数 $L$、内层判定步长 $\Delta t$
\Ensure 最优投放时刻 $t_1^*$ 与最大遮蔽时长 $T^*$（s）
\State $t \gets$ 粗网格扫描（步长 $0.5$ s）得到的当前最优
\State $T \gets T_0 \gets 0.05\ T(t)$，$T^* \gets T(t)$，$t_1^* \gets t$
\While{$T > T_f$}
  \For{$\ell = 1$ \textbf{到} $L$}
    \State 邻域扰动：$t' \gets t + \xi$，$\xi \sim \mathcal{N}(0, (0.05\,T/T_0)^2)$
    \If{$t' \notin [t_{\min}, t_{\max}]$}
      \State $t' \gets \mathrm{clip}(t', t_{\min}, t_{\max})$ \Comment{投影回可行域}
    \EndIf
    \State 计算 $\Delta T \gets T(t') - T(t)$
    \If{$\Delta T > 0$ 或 $u < \exp(\Delta T / T)$，其中 $u \sim U(0,1)$}
      \State $t \gets t'$ \Comment{Metropolis 准则：劣解按概率接受}
      \If{$T(t) > T^*$}
        \State $T^* \gets T(t)$；$t_1^* \gets t$
      \EndIf
    \EndIf
  \EndFor
  \State $T \gets \alpha T$ \Comment{降温，$\alpha = 0.95$}
\EndWhile
\State \Return $t_1^*,\ T^*$
\State \textbf{复杂度}：$O(L \log_{\alpha}(T_f/T_0) \cdot M)$，本问 $L=200$、$\alpha=0.95$、
       共 132 个温度层，实测 5.4 s；30 次运行标准差 $0.008$ s。
\end{algorithmic}
\end{algorithm}
```

**要点**：第 6 行的投影、第 14 行的 Metropolis 准则、第 19 行的降温公式三处是模拟退火的
"身份特征"，缺任何一处都会被评委认为"这不是退火，只是随机搜索"。

### 算法 3：MIP 的分支定界（求解整数决策变量）

```latex
\begin{algorithm}[htbp]
\caption{混合整数规划的分支定界算法}\label{alg:bnb}
\begin{algorithmic}[1]
\Require 混合整数模型 $(P)$：目标 $\max c^\top x$，约束 $Ax \le b$，
         整数变量下标集 $\mathcal{I}$，相对间隙容差 $\varepsilon = 10^{-4}$
\Ensure 最优解 $x^*$ 与最优值 $z^*$；若未证明最优，返回当前最好可行解与间隙
\State 求解线性松弛 $(P_0)$，得 $z_0$ 与 $\bar x^{(0)}$
\If{$\bar x^{(0)}$ 各分量均为整数}
  \State \Return $\bar x^{(0)},\ z_0$ \Comment{松弛解已经是整数解，直接结束}
\EndIf
\State 初始化活跃节点列表 $\mathcal{L} \gets \{(P_0, z_0)\}$，上界 $z^{\text{UB}} \gets z_0$，
       下界 $z^{\text{LB}} \gets -\infty$
\While{$\mathcal{L} \neq \varnothing$}
  \State 选支：从 $\mathcal{L}$ 中取出松弛界最大的节点 $(P_k, z_k)$，移出列表
  \If{$z_k \le z^{\text{LB}}(1+\varepsilon)$}
    \State \textbf{剪枝}（界剪枝）：该节点不可能改进当前最好解，丢弃
  \Else
    \State 选一个非整数分量 $\bar x_j$（$j\in\mathcal{I}$），按 $\lfloor \bar x_j \rfloor$ 与
           $\lceil \bar x_j \rceil$ 分出两个子节点 $P_{k1}, P_{k2}$，加入 $\mathcal{L}$
    \State 分别求解子节点的线性松弛，得到 $z_{k1}, z_{k2}$ 与解 $\bar x^{(k1)}, \bar x^{(k2)}$
    \For{每个子节点 $P_{kj}$}
      \If{子节点不可行}
        \State \textbf{剪枝}（可行性剪枝）
      \ElsIf{松弛解全为整数且 $z_{kj} > z^{\text{LB}}$}
        \State 更新 $z^{\text{LB}} \gets z_{kj}$，$x^* \gets \bar x^{(kj)}$
      \EndIf
    \EndFor
    \State 若 $z^{\text{UB}} \gets \max_{P\in\mathcal{L}} z(P)$，则更新上界
  \EndIf
\EndWhile
\State \Return $x^*,\ z^{\text{LB}}$，并报告间隙 $(z^{\text{UB}}-z^{\text{LB}})/|z^{\text{LB}}|$
\State \textbf{复杂度}：最坏 $O(2^{|\mathcal{I}|})$，实际由剪枝决定；本问探索 137 个节点，
       67 次 LP 求解，实测 1.9 s，最终间隙 $<10^{-6}$（已证明最优）。
\end{algorithmic}
\end{algorithm}
```

**要点**：① 三种剪枝（界剪枝、可行性剪枝、最优性剪枝）要分别出现并说明判据；
② **必须返回间隙**——"求解器说最优"与"证明最优"是两件事，评委看的就是这一步；
③ 若用现成求解器（Gurobi/CPLEX），在正文写清"调用哪家求解器、什么版本、什么参数"，
伪代码只描述你自己实现的搜索控制逻辑。

### 算法 4：熵权—TOPSIS 综合评价

```latex
\begin{algorithm}[htbp]
\caption{熵权法确定权重与 TOPSIS 排序}\label{alg:topsis}
\begin{algorithmic}[1]
\Require 评价矩阵 $X = (x_{ij})_{m\times n}$（$m$ 个方案、$n$ 个指标）、
         指标方向向量 $\mathbf{d}\in\{+,-\}^n$（$+$ 为效益型、$-$ 为成本型）
\Ensure 各方案贴近度 $C_i \in [0,1]$ 与排序结果
\State 极差规范化：对 $j=1,\dots,n$，
       $r_{ij} \gets \dfrac{x_{ij}-\min_i x_{ij}}{\max_i x_{ij}-\min_i x_{ij}}$（效益型），
       成本型取 $r_{ij} \gets \dfrac{\max_i x_{ij}-x_{ij}}{\max_i x_{ij}-\min_i x_{ij}}$
\If{存在 $j$ 使 $\max_i x_{ij} = \min_i x_{ij}$}
  \State 该指标无区分度，置权重 $w_j \gets 0$，并在表注中说明
\EndIf
\State 计算比重 $p_{ij} \gets r_{ij} / \sum_{i=1}^{m} r_{ij}$（若 $r_{ij}=0$ 则 $p_{ij}\ln p_{ij}\gets 0$）
\State 计算熵值 $e_j \gets -\dfrac{1}{\ln m}\sum_{i=1}^{m} p_{ij}\ln p_{ij}$
\State 计算差异系数 $g_j \gets 1-e_j$，权重 $w_j \gets g_j / \sum_{j=1}^{n} g_j$
\State 构造加权规范化矩阵 $v_{ij} \gets w_j r_{ij}$
\State 确定正/负理想解 $v_j^{+} \gets \max_i v_{ij}$，$v_j^{-} \gets \min_i v_{ij}$
\State 计算距离 $D_i^{+} \gets \sqrt{\sum_{j}(v_{ij}-v_j^{+})^2}$，$D_i^{-} \gets \sqrt{\sum_{j}(v_{ij}-v_j^{-})^2}$
\State 计算贴近度 $C_i \gets \dfrac{D_i^{-}}{D_i^{+}+D_i^{-}}$，按 $C_i$ 降序排序
\State \Return $\{w_j\},\ \{C_i\}$ 与排序
\State \textbf{复杂度}：$O(mn)$，无迭代；本题 $m=12$、$n=6$，实测 $<0.01$ s。
\State \textbf{稳健性}：对 $X$ 施加 $\pm5\%$ 随机扰动重复 1000 次，排序首位不变的比例为 $97.3\%$
       （见 表~\ref{tab:sensitivity}），说明评价结论对指标测量误差不敏感。
\end{algorithmic}
\end{algorithm}
```

**要点**：① 极端情形（列全相等、$r_{ij}=0$）必须显式处理，否则 $\ln 0$ 直接报错——
评委非常看重这类边界；② 评价类算法**必须给稳健性**（排序会不会翻），否则结论无法采信。

### 算法 5：蒙特卡洛不确定性传播

```latex
\begin{algorithm}[htbp]
\caption{参数不确定性的蒙特卡洛传播与置信区间估计}\label{alg:mc}
\begin{algorithmic}[1]
\Require 参数分布 $\{p_k \sim \mathcal{D}_k(\cdot)\}_{k=1}^{K}$（由 P5 数据审计给出）、
         随机样本数 $S$、置信水平 $1-\alpha$、随机种子 $s_0$
\Ensure 目标量 $T$ 的均值 $\hat\mu$、标准差 $\hat\sigma$、$1-\alpha$ 置信区间、收敛诊断量
\State 固定随机种子 $s_0$ \Comment{保证结果可复现，论文里的数字必须能被复算}
\State \textbf{for} $s = 1$ \textbf{to} $S$ \textbf{do}
  \State 抽样：$p_k^{(s)} \sim \mathcal{D}_k$，$k=1,\dots,K$
  \State 在固定参数下求解确定性模型，得到 $T^{(s)}$
\State \textbf{end for}
\State 估计均值与标准差：$\hat\mu \gets \frac{1}{S}\sum_s T^{(s)}$，
       $\hat\sigma \gets \sqrt{\frac{1}{S-1}\sum_s (T^{(s)}-\hat\mu)^2}$
\State 用分位数法给出区间 $[\hat q_{\alpha/2},\ \hat q_{1-\alpha/2}]$
\State \textbf{收敛诊断}：计算批均值法的 MC 标准误 $\widehat{\mathrm{SE}} = \hat\sigma/\sqrt{S}$，
       若 $\widehat{\mathrm{SE}}/\hat\mu > 0.5\%$，则 $S \gets 2S$ 并回到第 3 行
\State \Return $\hat\mu,\ \hat\sigma$、置信区间与 $\widehat{\mathrm{SE}}$
\State \textbf{复杂度}：$O(S\cdot c)$，$c$ 为单次确定性求解代价。本问 $S=10^{4}$、$c\approx 0.6$ ms，
       总计 6.0 s；$\widehat{\mathrm{SE}}/\hat\mu = 0.21\% < 0.5\%$，样本量充分。
\end{algorithmic}
\end{algorithm}
```

**要点**：① 固定随机种子（可复现是硬要求）；② **必须给收敛诊断**——
只写"跑了 10000 次"没有说服力，"标准误 0.21%"才说明样本量够了；
③ 若用拉丁超立方/拟蒙特卡洛，要在正文说明抽样方式的改进与理由。

---

## 4. 行号与正文引用

`algpseudocode` 的 `[1]` 会打印行号，但**不提供稳定的行标签**。因此：

| 需求 | 推荐做法 | 理由 |
|---|---|---|
| 引用整份算法 | `算法~\ref{alg:ga}`（配 `\label{alg:ga}`） | 稳定，永不出错 |
| 引用某一步 | 在伪代码里显式写 `\State \textbf{Step 3：}` 之类的步骤名，正文引用"算法 1 的约束修复步骤" | 加行/删行不会让引用失效 |
| 必须引用具体行号 | 写"算法 1 第 8 行"，并**在定稿后锁定**：任何插行都要同步改引用 | 数字直接、但有维护成本 |

纪律：① 定稿前做一次全局搜索 `第 [0-9]+ 行`，逐个核对；② 引用行号时把该行内容也写出来
（"算法 1 第 8 行的反射修复算子"），这样即使行号漂移，读者仍能找到；
③ **不要**在正文里说"详见算法 1"就完事——要说清"算法 1 的哪一步解决了哪个难点"。

---

## 5. 伪代码与附录代码的一致性

竞赛规则要求附录含**全部完整可运行的源程序**。伪代码是代码的"论文视图"，
两者不一致会被判为"程序运行结果与论文不符"（可能取消评奖资格）。

**做一张对照表**（放在 `sop/project/` 或直接写进实现笔记）：

| 伪代码位置 | 附录代码 | 必须一致的内容 |
|---|---|---|
| 算法 1 输入 | `code/main/ga_solve.py` → `def solve(inst, cfg)` | 参数名与默认值、参数个数 |
| 算法 1 第 5～9 行 | 同文件 `def evolve(pop, cfg)` | 选择/交叉/变异顺序、概率值 |
| 算法 1 第 8 行 | 同文件 `def repair(x, lo, hi)` | 修复公式（反射 vs 截断） |
| 算法 1 终止条件 | 同文件 `if best_hist.stall(40, tol=1e-4)` | 早停阈值与窗口长度 |
| 算法 5 第 3 行 | `code/main/mc_uncertainty.py` → `SEED = 20260901` | 随机种子、样本量 |

**三条检查动作**（交稿前必做，30 分钟）：

1. **重跑一遍**：在干净环境里运行附录代码，记录输出的关键数字，与论文表格逐个对；
2. **数一遍**：伪代码里的每个分支（`\If`/`\Else`）在代码里都有对应的 `if/else`，
   反之亦然（代码里有而伪代码没有的分支，要么补进伪代码，要么在正文说明它是工程细节）；
3. **搜一遍**：把伪代码里的常数（$G=400$、$N=60$、$\alpha=0.95$、种子）在代码里搜一遍，
   确认没有两套值。

---

## 6. 什么时候不要用伪代码

伪代码不是加分项，是"把算法讲到可复现"的工具。下面四种情况**不要**贴：

| 情况 | 为什么不该贴 | 改用什么 |
|---|---|---|
| 有闭式解 / 一步得出结果 | 伪代码只有 2～3 行，占半页却零信息量 | 直接写公式与代入过程 |
| 用现成求解器（Gurobi / LINGO / `scipy.optimize`） | 真正的算法在别人库里，你的伪代码是"调用说明" | 文字交代求解器、版本、参数设置，代码进附录 |
| 流程无分支、无迭代 | 三段文字说清楚的事 | 文字 + 一张流程图 |
| 只为"看起来高级"而贴 | 评委会问"这段伪代码与你的结果有什么关系"，答不上来就是负分 | 删掉，把版面留给结果表与灵敏度分析 |

**该贴的信号**：算法有**迭代结构**、有**约束处理细节**、有**终止判据**，
且这三件事直接决定结果的精度或可行性——此时伪代码是证明"我算得对"的必要证据。

---

## 7. 交付前检查清单

- [ ] 导言区已加 `algorithm` + `algpseudocode`（或 `algorithm2e`，**没**同时加两套）
- [ ] `\floatname{algorithm}{算法}`，输入/输出已中文化
- [ ] 每份伪代码都有编号与标题，正文用 `\ref` 引用过
- [ ] 输入项与正文符号表一致；输出项含单位
- [ ] 约束处理方式写明（罚函数/修复算子/投影），且给了可执行的公式
- [ ] 最后一行给了复杂度 + 实测代价
- [ ] 参数设置（$G,N,\alpha$、步长、阈值）与正文、附录代码**三处一致**
- [ ] 行号引用（"算法 1 第 8 行"）已逐个核对，且引用了该行内容
- [ ] 伪代码与附录代码的流程逐分支一致，且重跑结果与论文数字一致
- [ ] 伪代码内无校名、姓名、学号、赛区信息（含注释与路径）
- [ ] 编译后在 PDF 里**实际看过**：行号不溢出版心、中文正常、没被拆到两页
