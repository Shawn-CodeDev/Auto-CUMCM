"""编译国赛论文（自动定位 xelatex，跑够遍数，抽取错误摘要）。

为什么要单独写一个：LaTeX 编译的坑集中在三处——
  1. 找不到引擎（本仓库把 TeX Live 装在 tools/texlive，不在 PATH 里）
  2. 交叉引用/目录需要跑两遍以上，只跑一遍会留下 "??"
  3. 报错信息淹没在几千行日志里，人看不出到底哪一行错了

本脚本解决这三点：自动找引擎、按需多遍、把 ! 开头的错误与 l.N 行号摘出来。

用法：
    python compile_paper.py --tex paper/paper.tex
    python compile_paper.py --tex paper/paper.tex --engine xelatex --runs 3
    python compile_paper.py --selfcheck        # 只探测引擎可用性
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))


def _candidates() -> list[str]:
    """按优先级列出可能的 XeLaTeX 引擎路径。"""
    c = []
    # 本仓库自带的 TeX Live
    c.append(os.path.join(ROOT, "tools", "texlive", "bin", "windows", "xelatex.exe"))
    # PATH 上的
    for name in ("xelatex", "xelatex.exe"):
        w = shutil.which(name)
        if w:
            c.append(w)
    # 常见安装位置
    c += [
        r"C:\texlive\2026\bin\windows\xelatex.exe",
        r"C:\texlive\2025\bin\windows\xelatex.exe",
        r"C:\texlive\2024\bin\windows\xelatex.exe",
        r"C:\Program Files\MiKTeX\miktex\bin\x64\xelatex.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\MiKTeX\miktex\bin\x64\xelatex.exe"),
    ]
    seen, out = set(), []
    for p in c:
        if p and p not in seen and os.path.exists(p):
            seen.add(p)
            out.append(p)
    return out


def find_engine(explicit: str | None = None) -> str | None:
    if explicit:
        if os.path.exists(explicit):
            return explicit
        w = shutil.which(explicit)
        return w
    cands = _candidates()
    return cands[0] if cands else None


ERROR_RE = re.compile(r"^!+ *(.*)$", re.M)
LINE_RE = re.compile(r"^l\.(\d+)\s*(.*)$", re.M)
# 这些是"看着像错误其实无害"的信息
BENIGN = ("Font shape", "MERG NOT subset", "Overfull \\hbox", "Underfull \\vbox",
          "Package caption Warning", "hyperref Warning")


def summarize_log(log_text: str) -> tuple[list[str], list[str]]:
    """返回 (真正的错误, 提醒)。"""
    errors, warns = [], []
    for m in ERROR_RE.finditer(log_text):
        msg = m.group(1).strip()
        if not msg or any(b in msg for b in BENIGN):
            continue
        # 找紧跟的行号上下文
        tail = log_text[m.end():m.end() + 400]
        lm = LINE_RE.search(tail)
        if lm:
            errors.append(f"{msg}  → 第 {lm.group(1)} 行：{lm.group(2).strip()[:80]}")
        else:
            errors.append(msg)
    for m in re.finditer(r"LaTeX Warning: (.*)", log_text):
        w = m.group(1).strip()
        if "undefined" in w.lower() or "rerun" in w.lower():
            warns.append(w[:110])
    # 去重保序
    def uniq(xs):
        s, o = set(), []
        for x in xs:
            if x not in s:
                s.add(x)
                o.append(x)
        return o
    return uniq(errors)[:25], uniq(warns)[:12]


def compile_tex(tex: str, engine: str, runs: int = 2, timeout: int = 900) -> dict:
    tex = os.path.abspath(tex)
    wd = os.path.dirname(tex)
    base = os.path.splitext(os.path.basename(tex))[0]
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    # XeLaTeX 遇到中文路径/文件名时更稳
    env.setdefault("TEXMFVAR", os.path.join(wd, ".texmf-var"))

    logs = []
    rc = 0
    t0 = time.time()
    for i in range(runs):
        p = subprocess.run(
            [engine, "-interaction=nonstopmode", "-halt-on-error",
             f"-output-directory={wd}", os.path.basename(tex)],
            cwd=wd, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout)
        logs.append(p.stdout or "")
        rc = p.returncode
        logfile = os.path.join(wd, base + ".log")
        if os.path.exists(logfile):
            logs.append(open(logfile, encoding="utf-8", errors="replace").read())
        # 第一遍失败就没必要再跑
        if rc != 0 and i == 0:
            break

    full = "\n".join(logs)
    errors, warns = summarize_log(full)
    pdf = os.path.join(wd, base + ".pdf")
    ok = os.path.exists(pdf) and os.path.getsize(pdf) > 2000 and not errors
    return {
        "ok": ok,
        "returncode": rc,
        "pdf": pdf if os.path.exists(pdf) else None,
        "pdf_bytes": os.path.getsize(pdf) if os.path.exists(pdf) else 0,
        "errors": errors,
        "warnings": warns,
        "elapsed_s": round(time.time() - t0, 1),
        "log_tail": full[-2500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="编译国赛论文")
    ap.add_argument("--tex", help="主 .tex 文件")
    ap.add_argument("--engine", default=None, help="显式指定 xelatex 路径")
    ap.add_argument("--runs", type=int, default=2, help="编译遍数（默认 2，够交叉引用）")
    ap.add_argument("--selfcheck", action="store_true", help="只探测引擎")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    engine = find_engine(args.engine)
    if not engine:
        print("✘ 未找到 XeLaTeX 引擎。")
        print("  安装：python scripts/install_texlive.py   （清华 TUNA 镜像，scheme-small）")
        print("  或指定：--engine <路径\\xelatex.exe>")
        return 2
    print(f"引擎：{engine}")
    if args.selfcheck:
        v = subprocess.run([engine, "--version"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
        print("  " + (v.stdout or "").splitlines()[0])
        return 0

    if not args.tex:
        print("需要 --tex 指定主文件")
        return 2
    if not os.path.exists(args.tex):
        print(f"✘ 找不到 {args.tex}")
        return 2

    res = compile_tex(args.tex, engine, runs=args.runs)
    print(f"耗时 {res['elapsed_s']}s，退出码 {res['returncode']}")
    if res["pdf"]:
        print(f"PDF：{res['pdf']}（{res['pdf_bytes']/1024:.0f} KB）")
    if res["errors"]:
        print(f"\n✘ 发现 {len(res['errors'])} 个错误：")
        for e in res["errors"]:
            print("   - " + e)
    if res["warnings"]:
        print(f"\n提醒 {len(res['warnings'])} 条：")
        for w in res["warnings"][:6]:
            print("   ! " + w)
    if not res["errors"] and res["pdf"]:
        print("\n✔ 编译成功")
        return 0
    print("\n---- 日志末尾 ----")
    print(res["log_tail"][-1200:])
    return 1


if __name__ == "__main__":
    sys.exit(main())
