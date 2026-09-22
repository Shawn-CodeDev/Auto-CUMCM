"""从 2026 A 题题面中抽取附录 2/3/4 的物理参数与经验公式，落成可被代码引用的 JSON。

为什么单独做这一步：这些公式是**题目给定的**，不是我们拟合出来的，
所以必须原样进入论文的模型部分（P8 参数来源标注为"题目给定"），
并且代码要直接引用同一份 JSON，避免"论文写的公式"和"代码里的公式"不一致。

踩过的坑（写在这里免得下次再犯）：
  * 题面里"附录2  问题1 的相关参数"的**标题**没有空格，而正文引用写作"附录2）"；
    用 `find("附录 2")` 会命中正文引用，导致切错区块。
  * 附录 3 与附录 4 结构完全相同（三行公式 + D），必须**先切片再解析**，
    否则第二段的正则会匹配到第一段的值（实测附录 4 被解析成附录 3 的数字）。
  * 括号全角半角混用，正则前统一归一化。
"""
from __future__ import annotations

import json
import os
import re

SRC = r"E:\Math-SOP\logs\A2026_problem_text.txt"
OUT = r"E:\Math-SOP\skills\cumcm-paper\_e2e\A2026\inputs\problem_params.json"

text = open(SRC, encoding="utf-8").read()
text = text.replace("（", "(").replace("）", ")")


def heading_pos(tag: str) -> int:
    """定位附录**标题**（形如 '附录3  问题2 的相关经验公式'）。

    题面里标题与正文引用的关键差别是**空格数**：
       正文引用：`（相关参数见附录2）`      —— 数字后紧跟全角右括号，无空格
       附录标题：`附录2  问题1 的相关参数`  —— 数字后是两个空格
    所以用 `\\s{2,}` 锚定，能干净地跳过所有正文引用。
    """
    m = re.search(re.escape(tag) + r"\s{2,}\S", text)
    return m.start() if m else -1


i2 = heading_pos("附录2")
i3 = heading_pos("附录3")
i4 = heading_pos("附录4")
print(f"  标题位置：附录2={i2} 附录3={i3} 附录4={i4}")

blk2 = text[i2:i3] if 0 <= i2 < i3 else ""
blk3 = text[i3:i4] if 0 <= i3 < i4 else ""
blk4 = text[i4:] if i4 >= 0 else ""


def parse_formulas(b: str) -> dict:
    """解析"ρ= / cp= / k= / D=" 四行经验公式块。"""
    out = {}
    m = re.search(r"𝜌=\s*([\d.]+)\s*\+\s*([\d.]+)\s*𝐶", b)
    if m:
        out["rho"] = [float(m.group(1)), float(m.group(2))]
    m = re.search(r"𝑐𝑝=\s*([\d.]+)\s*\+\s*([\d.]+)\s*∙\s*\n?\s*𝐶\s*\n?\s*𝐶\s*\+\s*1", b)
    if m:
        out["cp"] = [float(m.group(1)), float(m.group(2))]
    m = re.search(r"𝑘=\s*([\d.]+)\s*\+\s*([\d.]+)\s*∙\s*\n?\s*𝐶\s*\n?\s*𝐶\s*\+\s*1", b)
    if m:
        out["k"] = [float(m.group(1)), float(m.group(2))]
    m = re.search(
        r"𝐷=\s*([\d.]+)\s*×\s*10\s*−\s*(\d+)\s*e\s*−\s*([\d.]+)\s*\n?\s*𝐶"
        r"\s*e\s*−\s*([\d.]+)\s*\n?\s*𝑇", b)
    if m:
        out["D"] = {"D0": float(m.group(1)) * (10 ** -int(m.group(2))),
                    "a": float(m.group(3)), "Ea_over_R": float(m.group(4))}
    return out


# 附录 2：问题 1 的常数
# 注意：PDF 抽出的文本会**在词中间断行**（实测"对流换热\n系数为25"），
# 所以参数名内部必须允许换行——把模式里的空白放宽为 "\s*"，并把参数名里的
# 汉字之间也允许空白，否则会漏掉 h。
def find_num(block: str, label: str, unit_pat: str) -> float | None:
    """在 label（允许词间断行）之后找数值 + 单位。"""
    lab = r"\s*".join(re.escape(c) for c in label)
    m = re.search(lab + r"\s*(?:为|是|约)?\s*([\d.]+)\s*" + unit_pat, block)
    return float(m.group(1)) if m else None


const = {}
const["rho"] = find_num(blk2, "密度", r"kg/m3")
const["cp"] = find_num(blk2, "比热容", r"J/\(kg·K\)")
const["k"] = find_num(blk2, "热传导系数", r"W/\(m·K\)")
const["h"] = find_num(blk2, "对流换热系数", r"W/\(m2·K\)")
const["hm"] = find_num(blk2, "对流传质系数", r"×\s*10\s*−\s*7")
const = {k: v for k, v in const.items() if v is not None}
for k in ("rho", "cp", "k", "h", "hm"):
    if k not in const:
        print(f"  !! 附录2 未匹配到 {k}")

m = re.search(r"𝐷=\s*([\d.]+)\s*×\s*10\s*−\s*9\s*e\s*−\s*([\d.]+)", blk2)
d1 = {"D0": float(m.group(1)) * 1e-9, "a": float(m.group(2))} if m else None

# 几何与初始条件（题面正文）
geo = {}
m = re.search(r"长为\s*([\d.]+)\s*cm，半径为\s*([\d.]+)\s*cm", text)
if m:
    geo["length_cm"], geo["radius_cm"] = float(m.group(1)), float(m.group(2))
m = re.search(r"温度为\s*([\d.]+)\s*°C", text)
if m:
    geo["T0_C"] = float(m.group(1))
m = re.search(r"水分浓度\(即干基含水率\)为\s*([\d.]+)\s*kg/kg", text)
if m:
    geo["C0"] = float(m.group(1))
m = re.search(r"水分浓度应低于\s*([\d.]+)\s*kg/kg", text)
if m:
    geo["C_target"] = float(m.group(1))

app3 = parse_formulas(blk3)
app4 = parse_formulas(blk4)

data = {
    "_source": "2026 高教社杯全国大学生数学建模竞赛 A 题（药材的烘干问题）题面附录 2/3/4",
    "_note": "全部参数与经验公式均为**题目给定**，不是拟合值。代码与论文必须引用同一份。",
    "geometry": geo,
    "problem1_constants": const,
    "problem1_diffusivity": d1,
    "appendix3_problem23": app3,
    "appendix4_problem4": app4,
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False, indent=2)

print(json.dumps(data, ensure_ascii=False, indent=2))
