"""国赛表格/示意图 LaTeX 静态自检器（不需要装 TeX 就能跑）。

为什么需要它：本仓库的目标机器上没有 TeX 发行版（见 README「已知限制」），
而"表能不能编译"这件事必须在上交前有个答案。本脚本查的是**能离线查出来的那几类错**：
三线表违规（竖线 / \\hline）、列数与每行 & 数不一致、环境与花括号不配对、
表题位置、占位符残留（nan / None / TODO）。它**不能**替代真实编译：
最终仍必须在有 XeLaTeX 的机器上编译一遍并在 PDF 里肉眼确认。

用法：
    python tex_check.py paper/tables/tab_sensitivity.tex       # 查单个/多个 .tex
    python tex_check.py --markdown references/three-line-table.md
                                                               # 查 Markdown 里的 ```latex 代码块
    python tex_check.py --markdown-dir references              # 查目录下所有 .md
    python tex_check.py -q ...                                 # 只输出结论

退出码：0 = 全部通过；1 = 存在问题（可直接用于 CI / 门禁脚本）。
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from table_gen import validate_tex  # noqa: E402  （同目录，脚本自足）

# 片段（不含浮动体）在单独校验时，环境不配对属于正常现象，只降级为提示
FRAGMENT_HINTS = ("未闭合的环境", "多出一个 \\end")
FLOAT_ENVS = (r"\begin{table}", r"\begin{figure}", r"\begin{longtable}",
              r"\begin{sidewaystable}", r"\begin{document}")


def is_fragment(tex: str) -> bool:
    return not any(env in tex for env in FLOAT_ENVS)


def check_text(tex: str, *, fragment: bool | None = None) -> tuple[list[str], list[str]]:
    """返回 (errors, hints)。fragment=None 时自动判断。"""
    if fragment is None:
        fragment = is_fragment(tex)
    issues = validate_tex(tex)
    errors, hints = [], []
    for it in issues:
        (hints if (fragment and any(k in it for k in FRAGMENT_HINTS)) else errors).append(it)
    return errors, hints


def check_file(path: str) -> tuple[list[str], list[str]]:
    with open(path, "r", encoding="utf-8") as fh:
        return check_text(fh.read())


def extract_latex_blocks(md_text: str) -> list[tuple[int, str]]:
    """抽出 Markdown 里的 ```latex / ```tex 代码块，返回 [(起始行号, 代码)]。"""
    blocks: list[tuple[int, str]] = []
    inside = False
    lang = ""
    start = 0
    buf: list[str] = []
    for lineno, line in enumerate(md_text.splitlines(), start=1):
        fence = re.match(r"^\s*```+\s*([A-Za-z0-9_+-]*)", line)
        if fence and not inside:
            inside, lang, start, buf = True, fence.group(1).lower(), lineno, []
            continue
        if inside and re.match(r"^\s*```+\s*$", line):
            if lang in ("latex", "tex"):
                blocks.append((start, "\n".join(buf)))
            inside = False
            continue
        if inside:
            buf.append(line)
    return blocks


def check_markdown(path: str, *, verbose: bool = True) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        blocks = extract_latex_blocks(fh.read())
    n_err = n_hint = 0
    details: list[str] = []
    for start, code in blocks:
        errors, hints = check_text(code)
        n_err += len(errors)
        n_hint += len(hints)
        tag = "OK" if not errors else f"{len(errors)} 个问题"
        if verbose:
            first = next((ln.strip() for ln in code.splitlines() if ln.strip()), "")
            details.append(f"  L{start:<5} {tag:<10} {first[:64]}")
        for e in errors:
            details.append(f"           ! {e}")
        for h in hints:
            details.append(f"           ~ {h}（片段，已忽略）")
    return {"path": path, "blocks": len(blocks), "errors": n_err, "hints": n_hint,
            "details": details}


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

    ap = argparse.ArgumentParser(description="表格/示意图 LaTeX 静态自检（无需 TeX 发行版）")
    ap.add_argument("files", nargs="*", help="要校验的 .tex 文件")
    ap.add_argument("--markdown", nargs="+", default=[], help="校验 Markdown 里的 ```latex 代码块")
    ap.add_argument("--markdown-dir", default=None, help="校验目录下全部 .md")
    ap.add_argument("-q", "--quiet", action="store_true", help="只输出结论")
    args = ap.parse_args(argv)

    md_files = list(args.markdown)
    if args.markdown_dir:
        md_files += sorted(glob.glob(os.path.join(args.markdown_dir, "*.md")))
    targets = [f for f in args.files if os.path.isfile(f)]

    if not targets and not md_files:
        ap.print_help()
        return 0

    total_err = total_hint = 0
    print("=== cumcm-table-figure / tex_check 静态自检 ===")
    for path in targets:
        errors, hints = check_file(path)
        total_err += len(errors)
        total_hint += len(hints)
        status = "通过" if not errors else f"{len(errors)} 个问题"
        print(f"[tex ] {path}: {status}"
              + (f"（另 {len(hints)} 条片段提示）" if hints else ""))
        for e in errors:
            print(f"       ! {e}")
        for h in hints:
            print(f"       ~ {h}（片段，已忽略）")

    for path in md_files:
        res = check_markdown(path, verbose=not args.quiet)
        total_err += res["errors"]
        total_hint += res["hints"]
        print(f"[md  ] {path}: {res['blocks']} 个 latex 代码块，"
              f"{'全部通过' if not res['errors'] else str(res['errors']) + ' 个问题'}"
              + (f"（另 {res['hints']} 条片段提示）" if res["hints"] else ""))
        if not args.quiet:
            for line in res["details"]:
                print(line)

    print(f"\n结论：{'全部通过' if total_err == 0 else str(total_err) + ' 个问题待修'}"
          f"；片段提示 {total_hint} 条（正常现象，不计入问题）")
    print("注意：静态检查只能查结构性错误；最终必须在有 XeLaTeX 的机器上编译并肉眼确认 PDF。")
    return 0 if total_err == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
