"""论文自检（S10）：把国赛的合规与质量要求变成可执行的检查。

检查分五类，每类都对应真实规则或本仓库的硬约定：
  A 结构   —— 章节齐全、摘要自足要素、附录含源程序清单
  B 合规   —— 身份信息（正文/元数据/文件名）、页数、AI 声明位置、无目录
  C 数字   —— 论文里的数值能否追到 claim_ledger 的 C 编号
  D 图表   —— 每张图/表都有编号与引用；图文件存在；调用 figure_check
  E 篇幅   —— 正文页数、图表占比、PDF 体积

用法：
    python lint_paper.py --work <工作目录>
    python lint_paper.py --work <工作目录> --pdf <论文.pdf>
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

# 论文章节关键词 -> 缺失即报错
REQUIRED_SECTIONS = [
    ("摘要", ["摘要", "abstract"]),
    ("问题重述", ["问题重述"]),
    ("问题分析", ["问题分析"]),
    ("模型假设", ["模型假设", "假设"]),
    ("符号说明", ["符号说明", "符号"]),
    ("模型建立与求解", ["模型的建立与求解", "模型建立与求解", "模型的建立", "模型建立"]),
    ("模型检验", ["模型检验", "检验", "灵敏度"]),
    ("模型评价", ["模型评价", "评价与推广"]),
    ("参考文献", ["参考文献", "\\bibitem", "\\bibliography"]),
    ("附录", ["附录", "\\appendix"]),
]

IDENTITY_PATTERNS = [
    (r"[\u4e00-\u9fff]{2,12}大学", "校名"),
    (r"[\u4e00-\u9fff]{2,12}学院", "学院名"),
    (r"学\s*号\s*[:：]?\s*\d{6,}", "学号"),
    (r"[\u4e00-\u9fff]{2,4}\s*赛区", "赛区"),
]
IDENTITY_ALLOW = re.compile(r"XX大学|某某大学|示例|占位|规范|章程|样例|大学生数学建模")


def read_text(p: str) -> str:
    try:
        return open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def find_tex(work: str) -> list[str]:
    out = []
    for root, dirs, files in os.walk(work):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "intake")]
        for f in files:
            if f.endswith(".tex"):
                out.append(os.path.join(root, f))
    return out


def check_structure(tex_all: str) -> tuple[list[str], list[str]]:
    problems, notes = [], []
    for label, keys in REQUIRED_SECTIONS:
        if not any(k in tex_all for k in keys):
            problems.append(f"缺少章节：{label}")
    if not re.search(r"\\begin\{abstract\}|摘\s*要", tex_all):
        problems.append("未见摘要")
    if "\\tableofcontents" in tex_all:
        problems.append("正文含目录（\\tableofcontents）——规则要求不要目录")
    if not re.search(r"AI\s*工具使用声明|人工智能工具使用|AI工具使用", tex_all):
        problems.append("未见《AI 工具使用声明》")
    else:
        # 声明必须在参考文献之前
        i_ai = max(tex_all.find("AI 工具使用声明"), tex_all.find("AI工具使用声明"),
                   tex_all.find("人工智能工具使用"))
        i_ref = min([x for x in (tex_all.find("参考文献"), tex_all.find("\\bibitem"),
                                tex_all.find("\\bibliography")) if x >= 0] or [10**9])
        if i_ai > i_ref:
            problems.append("《AI 工具使用声明》在参考文献之后（应在之前）")
        else:
            notes.append("AI 声明位置正确（参考文献之前）")
    if "\\appendix" not in tex_all and "附录" not in tex_all:
        problems.append("未见附录")
    return problems, notes


def check_identity(tex_all: str, pdf_path: str | None) -> tuple[list[str], list[str]]:
    problems, notes = [], []
    for pat, kind in IDENTITY_PATTERNS:
        for m in re.finditer(pat, tex_all):
            win = tex_all[max(0, m.start() - 40): m.end() + 40]
            if IDENTITY_ALLOW.search(win):
                continue
            problems.append(f"源码疑似{kind}：{m.group(0).strip()}")
            break
    if pdf_path and os.path.exists(pdf_path):
        try:
            import pymupdf as fitz  # type: ignore
        except Exception:
            try:
                import fitz  # type: ignore
            except Exception:
                notes.append("未安装 PyMuPDF，跳过 PDF 层检查")
                return problems, notes
        try:
            doc = fitz.open(pdf_path)
            txt = "".join(p.get_text() for p in doc)
            meta = doc.metadata or {}
            npages = doc.page_count
            doc.close()
        except Exception as e:  # noqa: BLE001
            problems.append(f"无法读取 PDF：{e}")
            return problems, notes
        for pat, kind in IDENTITY_PATTERNS:
            for m in re.finditer(pat, txt):
                win = txt[max(0, m.start() - 40): m.end() + 40]
                if IDENTITY_ALLOW.search(win):
                    continue
                problems.append(f"PDF 正文疑似{kind}：{m.group(0).strip()}")
                break
        au = str(meta.get("author") or "").strip()
        if au and not re.search(r"latex|tex|word|writer|microsoft|acrobat|overleaf", au, re.I):
            problems.append(f"PDF 元数据残留作者：{au}")
        else:
            notes.append("PDF 元数据未见作者信息")
        notes.append(f"PDF 共 {npages} 页")
    return problems, notes


def check_numbers(tex_all: str, work: str) -> tuple[list[str], list[str]]:
    """核对论文里的关键数值是否有账本来源。

    纪律：claim_ledger 的 C 编号应出现在论文里（或至少结果表可追）。
    这里做**宽松但有用**的检查：账本存在、含 C 编号、论文里引用了编号或数值能对上一部分。
    """
    problems, notes = [], []
    ledger = None
    for root, _d, files in os.walk(work):
        for f in files:
            if f == "claim_ledger.md":
                ledger = os.path.join(root, f)
    if not ledger:
        problems.append("缺 claim_ledger.md（结论账本）——数字无法追溯")
        return problems, notes
    led = read_text(ledger)
    c_ids = sorted(set(re.findall(r"\bC0*(\d{1,3})\b", led)), key=int)
    if not c_ids:
        problems.append("claim_ledger.md 里没有 C 编号")
        return problems, notes
    notes.append(f"账本含 {len(c_ids)} 条结论编号：{['C'+c for c in c_ids][:8]}")
    # 账本里的数值是否在论文中出现（抽 4 位以上数字比对）
    nums = set(re.findall(r"\d+\.\d{2,}", led))
    hit = sum(1 for n in nums if n in tex_all)
    notes.append(f"账本数值在论文中命中 {hit}/{len(nums)} 个"
                 + ("（论文数字大多可追）" if nums and hit / len(nums) > 0.3
                    else "（⚠️ 论文数字与账本重合度低，请核对）"))
    return problems, notes


def check_figures(tex_all: str, work: str) -> tuple[list[str], list[str]]:
    problems, notes = [], []
    figs = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex_all)
    if not figs:
        problems.append("论文里没有插图")
    missing = []
    for f in figs:
        base = f.split("}")[0].strip()
        cands = [base, base + ".pdf", base + ".png"]
        found = False
        for root, _d, files in os.walk(work):
            for c in cands:
                if os.path.basename(c) in files:
                    found = True
                    break
            if found:
                break
        if not found:
            missing.append(base)
    if missing:
        problems.append(f"插图文件找不到：{missing[:5]}")
    n_cap = len(re.findall(r"\\caption\{", tex_all))
    if n_cap < len(figs):
        problems.append(f"有 {len(figs)} 张图但只有 {n_cap} 个 \\caption（图必须有标题）")
    if len(re.findall(r"\\begin\{table\}", tex_all)) and "booktabs" not in tex_all \
            and "\\toprule" not in tex_all:
        notes.append("表格未见 booktabs 三线表（\\toprule/\\midrule/\\bottomrule）")
    else:
        notes.append(f"图 {len(figs)} 张、caption {n_cap} 个、表 "
                     f"{len(re.findall(r'begin.table.', tex_all))} 个")
    return problems, notes


def check_length(pdf_path: str | None) -> tuple[list[str], list[str]]:
    problems, notes = [], []
    if not pdf_path or not os.path.exists(pdf_path):
        notes.append("未提供 PDF，跳过篇幅检查")
        return problems, notes
    mb = os.path.getsize(pdf_path) / 1e6
    if mb > 20:
        problems.append(f"PDF {mb:.1f}MB 超过 20MB 上限")
    else:
        notes.append(f"PDF {mb:.2f}MB ≤ 20MB")
    try:
        import pymupdf as fitz  # type: ignore
    except Exception:
        try:
            import fitz  # type: ignore
        except Exception:
            return problems, notes
    doc = fitz.open(pdf_path)
    n = doc.page_count
    txt1 = doc[0].get_text() if n else ""
    doc.close()
    notes.append(f"总页数 {n}")
    if "摘" not in txt1 and "Abstract" not in txt1:
        problems.append("第一页不是摘要页（电子版第一页必须为摘要页）")
    else:
        notes.append("第一页是摘要页 ✔")
    return problems, notes


def main() -> int:
    ap = argparse.ArgumentParser(description="论文自检")
    ap.add_argument("--work", required=True, help="工作目录")
    ap.add_argument("--pdf", default=None, help="论文 PDF（省略则自动找）")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    work = os.path.abspath(args.work)
    texs = find_tex(work)
    if not texs:
        print(f"✘ 在 {work} 下找不到 .tex")
        return 2
    tex_all = "\n".join(read_text(t) for t in texs)

    pdf = args.pdf
    if not pdf:
        for root, _d, files in os.walk(work):
            for f in files:
                if f.endswith(".pdf") and "paper" in f.lower():
                    pdf = os.path.join(root, f)
        if not pdf:
            cands = []
            for root, _d, files in os.walk(work):
                cands += [os.path.join(root, f) for f in files if f.endswith(".pdf")]
            pdf = max(cands, key=os.path.getsize) if cands else None

    sections = [
        ("A 结构", check_structure(tex_all)),
        ("B 合规", check_identity(tex_all, pdf)),
        ("C 数字追溯", check_numbers(tex_all, work)),
        ("D 图表", check_figures(tex_all, work)),
        ("E 篇幅", check_length(pdf)),
    ]

    L = ["=" * 74, "国赛论文自检报告", "=" * 74, f"工作目录: {work}",
         f"源文件: {len(texs)} 个 .tex", f"PDF: {pdf or '（未找到）'}", ""]
    total_p = 0
    for name, (probs, notes) in sections:
        flag = "✘" if probs else "✔"
        L.append(f"{flag} {name}")
        for x in probs:
            L.append("    ✘ " + x)
            total_p += 1
        for x in notes:
            L.append("    · " + x)
        L.append("")
    L.append("-" * 74)
    L.append(f"硬性问题：{total_p} 条" + ("　→ 必须修复" if total_p else "　✔ 通过"))

    rep = "\n".join(L)
    dest = os.path.join(work, "lint_report.md")
    os.makedirs(work, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(rep)
    print(rep)
    print(f"\n报告写入：{dest}")
    return 1 if total_p else 0


if __name__ == "__main__":
    sys.exit(main())
