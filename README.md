# Auto-CUMCM

> 面向中国大学生数学建模竞赛（CUMCM）的 Agent Skills 工具箱。<br>
> 从题面、数据到论文、图表、冷审稿与提交打包，建立一条可验证的建模交付链。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/Agent%20Skills-5-6f42c1.svg)](#技能矩阵)
[![GitHub stars](https://img.shields.io/github/stars/Shawn-CodeDev/Auto-CUMCM?style=social)](https://github.com/Shawn-CodeDev/Auto-CUMCM/stargazers)

如果这个项目帮助你更快地完成建模论文，欢迎点一个 Star，或分享你的改进方案。

## 这是什么

Auto-CUMCM 不是一套泛泛的写作提示词，而是一组可以被 Agent 直接调用的、带有明确触发条件、工作流、参考资料和验证脚本的专业技能。

它把比赛中最容易失控的环节拆成可复用能力：

```text
题面 + 数据
    │
    ▼
勘察与建模 ──► 实验与证据 ──► 图表与论文 ──► 冷审稿 ──► 匿名化提交包
```

每个技能都位于独立目录，以 `SKILL.md` 作为入口；支持 Agent Skills 的编码助手可以按任务自动匹配，也可以在对话中显式指定技能名称。

## 为什么值得用

- **先定义证据，再生成内容**：图、表、模型和结论都有清晰的交付契约。
- **检查最终产物**：检查导出的 PDF、暂存目录和压缩包，而不是只检查脚本是否运行。
- **允许清单优先**：提交包从 allowlist 构建，降低遗漏身份信息和无关文件的风险。
- **从发现问题到记录问题**：模型偏差、验证结果和局限性进入结论账本，而不是被漂亮的图表掩盖。
- **可复用、可审阅、可扩展**：技能、参考资料和脚本分层组织，适合个人参赛和团队协作。

## 技能矩阵

| 技能 | 适用场景 | 主要产出 |
| --- | --- | --- |
| [`cumcm-paper`](cumcm-paper/SKILL.md) | 从赛题和附件开始搭建完整解题流程 | 勘察报告、模型、实验、图表、LaTeX/PDF、过程记录 |
| [`cumcm-figure`](cumcm-figure/SKILL.md) | 折线图、多面板图、热力图、灵敏度图、验证图 | 论文级 PDF/PNG、图注、图形质量检查结果 |
| [`cumcm-table-figure`](cumcm-table-figure/SKILL.md) | 三线表、符号表、流程图、机制图、算法伪代码 | LaTeX 表格与示意图源码、排版检查结果 |
| [`cumcm-cold-review`](cumcm-cold-review/SKILL.md) | 提交前模拟评委、红队审阅、复现检查 | 问题清单、严重级别、修复优先级、审稿裁定 |
| [`cumcm-release`](cumcm-release/SKILL.md) | 匿名化、支撑材料整理、最终提交 | allowlist 提交目录、扫描报告、可交付压缩包 |

`cumcm-paper` 负责串起主流程，其余四个技能在出图、排版、审稿和交付节点提供专项能力。

## 快速开始

### 方式一：安装到支持 Skills 的 Agent

```bash
npx skills add Shawn-CodeDev/Auto-CUMCM -g -y
```

安装后，可以直接提出类似请求：

```text
用 cumcm-paper 分析这道赛题和附件，先生成 intake 勘察报告。
用 cumcm-figure 检查这张结果图是否满足论文交付要求。
用 cumcm-cold-review 对现有论文做一次提交前红队审阅。
```

### 方式二：克隆后阅读或二次开发

```bash
git clone https://github.com/Shawn-CodeDev/Auto-CUMCM.git
cd Auto-CUMCM
find . -name SKILL.md -print
```

建议先阅读 [`cumcm-paper/SKILL.md`](cumcm-paper/SKILL.md) 了解总流程，再按任务进入专项技能。

## 一次完整工作流

1. **Intake**：读取题面和附件，确认变量、约束、数据质量与交付目标。
2. **建模与实验**：选择模型，记录假设，运行可复现的实验并保留中间证据。
3. **论文资产**：根据结论生产图、表、公式、图注和 LaTeX 章节。
4. **验证与冷审**：检查数值、引用、图表、复现路径和论文中可能被评委攻击的环节。
5. **交付打包**：按 allowlist 生成提交包，扫描身份信息和无关文件，再进行最终复核。

## 项目结构

```text
Auto-CUMCM/
├── cumcm-paper/          # 端到端论文流水线
├── cumcm-figure/         # 数据图与论文级导出
├── cumcm-table-figure/   # 表格、示意图与伪代码
├── cumcm-cold-review/    # 冷审稿与红队检查
├── cumcm-release/        # 提交打包与合规扫描
├── LICENSE
└── README.md
```

每个技能目录可以包含：

- `SKILL.md`：名称、触发条件、边界和执行流程；
- `references/`：方法、模板和质量门禁；
- `scripts/`：生成、检查和自检工具；
- `_demo/` 或 `_e2e/`：用于理解工作流的演示资产。

## 设计原则

### 契约优先

先回答“这张图/这张表/这份报告要证明什么”，再决定结构和实现方式。没有结论的图表不应因为“看起来完整”而进入论文。

### 产物优先

最终检查针对导出的 PDF、暂存目录和压缩包。工作区里存在正确脚本，不代表评委拿到的文件正确。

### Allowlist 优先

提交包明确列出允许进入的文件，而不是事后维护一份可能漏项的排除列表。

### 诚实记录不确定性

偏差、失败实验和模型局限进入结果记录与论文，而不是只保留最漂亮的结果。

## 常用脚本

| 脚本 | 用途 |
| --- | --- |
| `cumcm-figure/scripts/figure_check.py` | 检查字体、空图、命名、身份信息与导出质量 |
| `cumcm-figure/scripts/demo_and_verify.py` | 生成演示图并验证检查器能够拦截问题 |
| `cumcm-table-figure/scripts/table_gen.py` | 生成 booktabs 三线表源码 |
| `cumcm-release/scripts/stage_and_scan.py` | 构建 allowlist 暂存目录并扫描泄露信息 |
| `cumcm-paper/scripts/intake.py` | 对赛题和附件进行初始勘察 |

脚本的具体参数、输入格式和边界条件以对应目录中的 `SKILL.md` 为准。

## 贡献

欢迎提交新的比赛场景、质量检查规则、参考资料和可复现示例。请先阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md)，并确保：

- 新技能有清晰的触发条件、适用边界和最小可运行示例；
- 脚本失败时给出可操作的错误信息；
- 示例数据不包含真实个人信息、学校信息或未授权的竞赛材料；
- 提交前运行 `git diff --check`，并删除本地生成的缓存与临时文件。

## 许可

本项目以 [MIT License](LICENSE) 发布。第三方参考资料和外部资产仍受其原始许可证约束。

---

如果你在真实赛题上使用了 Auto-CUMCM，欢迎在 Issue 中分享：题型、使用的技能、遇到的失败点，以及最希望补上的能力。
