# Agent Skills（作业能力层）

> 这里是**可被 AI 编码助手直接调用**的技能包。每个技能是一个自包含的目录，
> 含 `SKILL.md`（触发条件 + 工作流）与配套的 `references/`、`scripts/`。
>
> 当你在支持 Agent Skills 的环境里提出相关请求时，助手会**自动加载**匹配的技能；
> 你也可以直接说"用 cumcm-figure 帮我画这张图"来显式调用。

---

## 一、技能清单

| 技能 | 解决什么 | 服务阶段 | 入口 |
|---|---|---|---|
| **`cumcm-paper`** | **端到端流水线**：只给"题面 + 数据"，产出完整论文包（模型、代码、结果、图表、LaTeX 源码与编译好的 PDF） | P0–P16 全流程 | `cumcm-paper/SKILL.md` |
| **`cumcm-figure`** | 契约式论文配图：先写"这张图要证明什么"，再定面板，再写代码。含中文字体/负号/导出统一风格层与自动终检 | P5 / P11 / P12 / P14 | `cumcm-figure/SKILL.md` |
| **`cumcm-table-figure`** | 三线表、机制示意图、流程图、算法伪代码；表格列的必要性检验与 LaTeX 落地 | P8 / P11 / P14 | `cumcm-table-figure/SKILL.md` |
| **`cumcm-cold-review`** | P15 冷审稿面板：构造隔离、六镜头分工、严重级判定、裁定与优先级修复 | P15 | `cumcm-cold-review/SKILL.md` |
| **`cumcm-release`** | P16 提交打包：allowlist 暂存、全字节身份扫描（含容器格式内部）、植入字符串验证扫描器 | P16 | `cumcm-release/SKILL.md` |

四个专项技能是 `cumcm-paper` 的**下游能力**：流水线跑到出图、排版、审稿、打包时，
按契约调用它们，而不是自己重造。

---

## 一·补　端到端案例（可直接看结果）

`cumcm-paper` 用 **2026 年 A 题「药材的烘干问题」** 做了一次真实的端到端测试：

| 输入 | 输出 |
|---|---|
| 官方赛题 PDF + 附件 1（烘房环境）+ 附件 2（半径实测） | 14 页论文 PDF、6 张成品图、4 个交付表格、全部源代码 |

成果资产在 **`../assets/case_study_A2026/`**（含论文 PDF 与 6 张案例图，
可直接用于产品页）。测试的工作目录在 `cumcm-paper/_e2e/A2026/`。

案例中最能说明流水线价值的一点：**它自己发现问题并纠正了模型**——
初版常半径模型算出 27.5 h 完成干燥，而附件 2 的实测半径一直收缩到 29.5 h；
流水线记录了这个矛盾，先后尝试移动边界模型与有效扩散修正，
最终用实测观测量标定出 β = 0.0674，并把仍然存在的偏差
（半径 RMSE 0.490 cm、MAPE 38.66%）**如实写进论文的局限一节**。

---

## 二、为什么要有这一层：与 `tutorials/` 的区别

```
tutorials/process/   讲原理与方法        「这类问题方法上应该怎么办」
sop/                 讲流程与门禁        「这次比赛下一步做什么，做完没有」
skills/              讲一次具体作业怎么做 「把这张图画出来，并且画对」
```

举一个具体差别：

- `tutorials/process/paper_writing.md` 会告诉你"每张图要有编号、标题、单位，正文要有解读"；
- `skills/cumcm-figure` 会**要求你先写出一句话结论、绑定 C 编号、给出面板映射**，
  然后才允许写绘图代码，最后用 `figure_check.py` 检查字体是否嵌入、
  图内是否混入校名、是否画成了空图。

前者是知识，后者是**带强制动作与验证的作业规程**。

---

## 三、设计原则（四个技能共通）

这四条原则是从开源科研 skill 的实践中吸收并改造的，也是这一层价值的来源：

### 1. 先立契约，再动手
出图、排版、审稿、打包都先写一份**契约**：这张图要证明什么、这份报告回答什么、
这个包要放什么。跳过契约直接产出，是本层最严重的误用。

### 2. 验证产物，而不是验证工作区
`cumcm-figure` 检查的是**导出的 PDF**，不是绘图脚本；
`cumcm-release` 扫描的是**staged 目录**，不是工作目录。
理由：工作目录里含有那个"缺失的文件"，从里面永远看不出问题。

### 3. 用 allowlist，不用 blocklist
`cumcm-release` 要求先列出"要放进去的"，而不是"要排除的"。
排除清单是你对"自己没想到的东西"的断言，而身份信息恰恰藏在没想到的地方
（编辑器备份、`__pycache__`、notebook 输出单元格、Office 文档属性、压缩包内的目录名）。

### 4. 植入已知字符串，证明检查器在工作
"零发现"与"检查器根本没运行"输出完全一样。
所以 `cumcm-release` 会把已知的校名/学号/路径**植入真实格式**（docx 的 XML、
xlsx 单元格、ipynb 输出），确认扫描器抓得到，再清理。
`cumcm-figure` 的 `demo_and_verify.py` 同理：故意生成一张含校名的图，确认终检器拦得住。

---

## 四、脚本速查

| 脚本 | 作用 | 自检命令 |
|---|---|---|
| `cumcm-figure/scripts/cumcm_style.py` | 统一风格层：中文字体、负号、配色、尺寸、导出 | `python cumcm_style.py` |
| `cumcm-figure/scripts/figure_check.py` | 配图终检：字体嵌入、体积、身份信息、近空图、命名 | `python figure_check.py --dir results/figures` |
| `cumcm-figure/scripts/demo_and_verify.py` | 端到端验证：出 4 张图 + 注入问题确认终检器有效 | `python demo_and_verify.py` |
| `cumcm-table-figure/scripts/table_gen.py` | 从 CSV/Excel 生成 booktabs 三线表源码 | `python table_gen.py` |
| `cumcm-release/scripts/stage_and_scan.py` | allowlist 暂存 + 身份信息扫描 + 扫描器自检 | `python stage_and_scan.py --selftest` |

---

## 五、已验证的能力（不是声称，是跑出来的）

| 验证项 | 结论 |
|---|---|
| 中文字体与负号 | 本机识别到 `Microsoft YaHei` / `SimHei`，出图目视确认中文正常、负号为短横线 |
| 导出成对产出 | 每张图同时产出矢量 PDF 与 600 dpi PNG；4 张演示图全部通过终检（硬性问题 0） |
| 身份信息拦截 | 故意在图内文字与文件名注入"参赛大学 / 学号 2026001"，终检器 3 条全中 |
| 空图拦截 | 只有坐标轴没有数据的图，导出期告警触发（数据元素计数 = 0） |
| 三线表生成 | `table_gen.py` 生成合法 booktabs 源码（right / siunitx 两种模式）；用负例（`\hline`、列数不一致）验证校验器真会拦 |
| 提交包扫描 | 6 类植入泄露（校名/学号/POSIX 路径/Windows 路径/邮箱/赛区）全部抓到，2 个干净对照 0 误报，规则原文白名单正确放行 |
| 技能规范 | `scripts/check_skills.py`：4 个技能的 frontmatter、触发描述、资源引用全部合规 |

> 说明：`cumcm-figure/scripts/_calibrate_empty.py` 是阈值标定脚本，
> 记录了"矢量 PDF 里空图与 200 个数据点体积几乎相同（2041 B vs 4065 B）"这一实测结论，
> 解释了为什么空图检测必须放在绘图对象层面而不是靠文件大小。

---

## 六、与 SOP 门禁的接口

技能产出要能通过 `scripts/validate_pipeline.py` 的对应阶段门禁：

| 技能 | 对应门禁 | 关键检查 |
|---|---|---|
| `cumcm-figure` | P12 / P14 | 验证图数量、论文 PDF 体积、PDF 内身份信息 |
| `cumcm-table-figure` | P8 / P14 | 论文章节齐全、公式数量、表格行数 |
| `cumcm-cold-review` | P15 | `no_fatal_open`：不得存在"致命 + 未修复"的行 |
| `cumcm-release` | P16 | 论文/支撑材料体积、AI 详情文件、清单全勾、包内无身份信息 |

工作顺序建议：**先用技能产出，再跑门禁校验**，两者互补——
技能负责"做对"，门禁负责"不漏"。

---

## 七、调研来源与授权说明

本层的设计参考了以下开源科研 skill 的方法论，并针对国赛场景重写：

| 来源 | 吸收了什么 |
|---|---|
| [jing1312/nature-figure-skill](https://github.com/jing1312/nature-figure-skill) | 图契约、QA 契约、设计理论、图型选择、编辑文本与字体嵌入 |
| [gxCaesar/open-research-skills](https://github.com/gxCaesar/open-research-skills) | 冷审稿面板的隔离构造与镜头分工、artifact release 的 allowlist 与扫描器自检、可视化模式划分 |
| [tuoxie2046/claude-code-research-skills](https://github.com/tuoxie2046/claude-code-research-skills) | 科研图表工作流的组织方式（仓库因路径过长未能完整抓取，仅作方向参考） |

原始抓取内容保留在 `../research/skills_raw/`，仅作参考，**不是交付物**。
以上技能均为其作者的知识产权，本仓库只吸收了方法论并用中文针对国赛重写实现，
未复制其代码或英文原文。
