"""打包产品页用的案例图：从端到端实测产物中挑出最有展示价值的几张。

选择标准（面向产品页）：
  * 一眼能看出"这是真数据 + 真模型"，而不是示意性涂鸦
  * 有中文、有单位、有可读的结论标注
  * 覆盖不同图型：径向分布 / 时空场 / 判据曲线 / 验证对比
"""
from __future__ import annotations

import os
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ROOT = r"E:\Math-SOP"
E2E = os.path.join(ROOT, "skills", "cumcm-paper", "_e2e", "A2026")
SRC = os.path.join(E2E, "figures")
DST = os.path.join(ROOT, "assets", "case_study_A2026")
os.makedirs(DST, exist_ok=True)

PICKS = [
    ("E09_p1_profiles.png", "fig1_温度与水分径向分布.png",
     "问题一：预热阶段温度与含水率的径向分布（6 个时刻）"),
    ("E10_p2_fields.png", "fig2_时空演化热力图.png",
     "问题二：72 小时干燥过程的含水率与温度时空演化"),
    ("E11_drying_time.png", "fig3_烘干时长判据.png",
     "问题三：含水率衰减曲线与烘干时长判据（35.3 h）"),
    ("E12_validation.png", "fig4_实测vs预测验证.png",
     "模型检验：半径收缩的实测与预测对比（含误差指标）"),
    ("E01_env.png", "fig5_烘房环境数据.png",
     "数据审计：附件 1 烘房温度与水分浓度"),
    ("E02_radius.png", "fig6_半径实测数据.png",
     "数据审计：附件 2 药材半径随时间收缩"),
]

copied = []
for src, dst, desc in PICKS:
    sp = os.path.join(SRC, src)
    if not os.path.exists(sp):
        print(f"  跳过（不存在）：{src}")
        continue
    dp = os.path.join(DST, dst)
    shutil.copy2(sp, dp)
    copied.append((dst, os.path.getsize(dp), desc))
    print(f"  ✔ {dst}  ({os.path.getsize(dp)/1024:.0f} KB)")

# 同时把编译好的论文复制过去，便于展示
paper = os.path.join(E2E, "paper", "paper.pdf")
if os.path.exists(paper):
    dp = os.path.join(DST, "案例论文_2026A题_药材烘干.pdf")
    shutil.copy2(paper, dp)
    copied.append((os.path.basename(dp), os.path.getsize(dp), "端到端产出的完整论文 PDF"))
    print(f"  ✔ {os.path.basename(dp)}  ({os.path.getsize(dp)/1024:.0f} KB)")

idx = ["# 端到端案例：2026 A 题 药材的烘干问题", "",
       "> 输入：一份赛题 PDF + 两份附件数据。输出：模型、代码、结果、图表、论文 PDF。",
       "> 全部数字来自真实运行，未经人工修饰。", "",
       "| 文件 | 体积 | 说明 |", "|---|---|---|"]
for name, size, desc in copied:
    idx.append(f"| `{name}` | {size/1024:.0f} KB | {desc} |")
idx += ["", "## 复现命令", "", "```powershell",
        "cd skills/cumcm-paper/_e2e/A2026",
        "python code/load_data.py        # 数据审计",
        "python code/mesh_check.py       # 网格无关性",
        "python code/calibrate_beta.py   # 参数标定",
        "python code/solve_final.py      # 全部结果与图",
        "python ../../../scripts/compile_paper.py --tex paper/paper.tex --runs 3",
        "```", ""]
open(os.path.join(DST, "README.md"), "w", encoding="utf-8").write("\n".join(idx))
print(f"\n共导出 {len(copied)} 个文件到 {DST}")
