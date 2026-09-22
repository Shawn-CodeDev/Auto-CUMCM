# 质量门与自检（quality-gates）

完工前逐项过。**每一条都对应本仓库某个可执行的检查，不是愿望清单。**

---

## 一、四道门（按顺序，前面的不过不进后面）

### 门 1：产物完整（S0–S6）

```powershell
python ../../../scripts/validate_pipeline.py --project <工作目录>
```

| 检查 | 通过条件 |
|---|---|
| intake 产物 | `problem_spec.md`、`data_report.md`、`intake_summary.json` 齐备 |
| 契约 | `paper_contract.md` 有任务清单、模型路线、假设后备 |
| 数据 | `data_report.md` 含清洗规则与理由；诊断图存在 |
| 代码 | `code/` 下脚本齐备，入口可运行 |
| 结果 | `results/` 下有全部 `resultN.xlsx`；`experiment_registry.md` 有登记 |

### 门 2：证据链连通（S7–S8）

```powershell
python ../../../scripts/check_traceability.py --project <工作目录>
```

| 检查 | 通过条件 |
|---|---|
| 结论有编号 | `claim_ledger.md` 含 C01…Cn |
| 结论有证据 | 每条结论的"证据"列指向 E 编号或图表，不是"见正文" |
| 无孤儿实验 | 被跑过但从未被任何结论引用的实验需确认（可接受，但要解释） |
| 无悬空引用 | 不引用不存在的 E 编号 |

### 门 3：论文合规且可编译（S9）

```powershell
python scripts/compile_paper.py --tex paper/paper.tex --runs 3
```

| 检查 | 通过条件 |
|---|---|
| 编译 | 退出码 0，无 `!` 开头错误 |
| 交叉引用 | 无 `undefined reference`（跑 3 遍仍报则说明 label 写错） |
| 中文 | 打开 PDF 目视确认（XeLaTeX + ctex） |
| 公式 | 目视确认无溢出页边 |

### 门 4：论文自检（S10）

```powershell
python scripts/lint_paper.py --work <工作目录>
```

| 类别 | 通过条件 |
|---|---|
| A 结构 | 10 个必需章节齐全；无目录；AI 声明在参考文献之前；有附录 |
| B 合规 | 源码与 PDF 正文/元数据均无校名/姓名/学号/赛区 |
| C 数字追溯 | 账本存在且含 C 编号；账本数值在论文中命中率 > 30% |
| D 图表 | 所有 `\includegraphics` 文件存在；图数 ≤ `\caption` 数 |
| E 篇幅 | PDF ≤ 20 MB；第一页是摘要页；总页数合理 |

---

## 二、诚实性检查（脚本查不了，必须人工过）

这一节是本流水线区别于"自动生成器"的关键。**以下每一条都问自己一遍**：

| 问题 | 不合格的样子 | 合格的样子 |
|---|---|---|
| 论文里有没有**编出来的数**？ | 为了图表好看补一个点 | 每个数都能追到 E 编号 |
| 验证结果**不理想时怎么处理的**？ | 删掉这段，或换成好看的指标 | 如实报告，并分析成因（本文做法） |
| 假设是否**真的被用到**？ | 列了 8 条假设，后文只用了 2 条 | 每条假设标注"后文何处使用" |
| 有没有**过度宣称**？ | "模型能准确预测半径" | "半径预测 MAPE 38.7%，说明收缩关系仍需改进" |
| 参数来源是否**标注清楚**？ | "取 $k=0.36$" | "由题面附录 2 取 $k=0.36$ W/(m·K)" |
| **被放弃的结论**有没有记录？ | 无 | 账本里有"被放弃的结论"小节 |
| 复现步骤是否**真的能跑通**？ | 只列文件不列命令 | 附完整命令序列，且实测跑过 |

> **本文案例的示范**：半径外部验证 MAPE 38.66%、RMSE 0.490 cm，
> 这是一个"不好看"的结果。我们把它写进了摘要第 ④ 块与 §6.2 整节，
> 并指出成因是"整体均匀收缩假设忽略了收缩滞后"。
> 这样处理之后，这个偏差从**弱点**变成了**展示建模素养的证据**。

---

## 三、常见失败速查

| 症状 | 根因 | 处置 |
|---|---|---|
| 论文数字与结果文件对不上 | 手抄数字 | 从 `results/` 复制，或改成脚本生成表格 |
| 编译报缺 `.sty` | TeX Live 未装全 | `tlmgr install <包名>`；本仓库清单见 `../../../scripts/install_texlive.py` |
| 图中中文变方块 | 未用 XeLaTeX 或字体缺失 | 用 `cumcm-figure` 的 `apply_cumcm_style()` |
| 矢量 PDF 体积爆炸 | 大数据量 `pcolormesh` 未光栅化 | 降采样 + `rasterized=True`（本文从 4171 KB 降到 46 KB） |
| 单栏图里的字比正文还大 | 写 `width=\linewidth` 导致放大 2 倍 | 单栏图写固定 cm 宽度 |
| 半径/质量类曲线不单调 | 量测抖动未处理 | 用累积最小/最大修正，并在报告里说明 |
| 结果集太大写不进 xlsx | 每 1 s × 每 0.1 cm 共 26 万行 | 明确说明这是题面要求；用 `openpyxl` 直写，必要时分表 |

---

## 四、交付清单

```
<工作目录>/
├── intake/                    勘察产物（题面解析 + 数据审计）
├── inputs/                   题面、附件、抽取出的参数 JSON
├── paper_contract.md          契约
├── data_report.md             数据审计
├── model_decision.md          模型选型
├── model_spec.md              数学形式化
├── experiment_registry.md     实验登记
├── validation_report.md       验证报告
├── claim_ledger.md            结论账本
├── lint_report.md             自检报告
├── code/                      全部可运行源代码
├── data/clean/                清洗后数据
├── results/                   result1–4.xlsx 与中间结果
├── figures/                   全部图（PDF 矢量 + PNG 预览）
└── paper/
    ├── paper.tex
    └── paper.pdf              ← 最终交付物
```
